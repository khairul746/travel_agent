import asyncio, os, sys, signal
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from Agent.llm import agent, collector
from threading import Thread
from flask import Blueprint, request, jsonify
from uuid import uuid4
from werkzeug.exceptions import BadRequest
from Tools.search_flights import search_flights_tool_fn, get_flight_urls_tool_fn, close_session_tool_fn
from Utils.session_manager import close_all_sessions_sync

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

CORS(app)

api = Blueprint("api", __name__, url_prefix="/api")

_LOOP = asyncio.new_event_loop()
def _loop_forever():
    """
    Run the global asyncio event loop forever in a dedicated background thread.

    This process-wide loop is used to execute async coroutines (e.g., Playwright tools)
    from sync Flask endpoints via `run_coro()`. The loop is set on this thread and kept
    alive for the lifetime of the process.
    """
    asyncio.set_event_loop(_LOOP)
    _LOOP.run_forever()

Thread(target=_loop_forever, daemon=True).start()

def run_coro(coro, timeout=120):
    """
    Run an asyncio coroutine on the background event loop and wait for the result.

    Args:
        coro: The coroutine object to execute.
        timeout (int|float): Max seconds to wait for the result before raising TimeoutError.

    Returns:
        Any: The coroutine's return value.

    Raises:
        concurrent.futures.TimeoutError: If result is not available within `timeout`.
        Exception: Any exception raised inside the coroutine is propagated.
    """
    fut = asyncio.run_coroutine_threadsafe(coro, _LOOP)
    return fut.result(timeout=timeout)

def _install_signal_shutdown():
    """
    Register signal handlers to close Playwright sessions and stop the
    background asyncio loop before the process exits. Avoid double-registering
    with Flask's debug reloader by only installing in the child process.
    """
    # Only install in the actual serving process when debug reloader is on
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if app.debug and not is_reloader_child:
        return

    def _handler(signum, frame):
        try:
            # 1) close all Playwright sessions so the Node driver won't EPIPE
            close_all_sessions_sync()
        finally:
            # 2) stop the background asyncio loop thread
            try:
                _LOOP.call_soon_threadsafe(_LOOP.stop)
            except Exception:
                pass
            # 3) exit the process
            sys.exit(0)

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):  # SIGBREAK for Windows (Ctrl+Break)
        sig = getattr(signal, name, None)
        if not sig:
            continue
        try:
            signal.signal(sig, _handler)
        except Exception:
            # Some environments disallow setting signal handlers; ignore
            pass

# >>> call it once right after the loop thread is started <<<
_install_signal_shutdown()

@app.route("/")
def main():
    """Render the main UI page (index.html)."""
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """
    Handle chat messages from the UI
    
    Returns:
      flask.Response: JSON response with reply/artifacts/thread_id, or a JSON error (500) on failure.
    """
    body = request.get_json(force=True) or {}
    user_input = body.get("message", "")
    
    base_thread_id = body.get("thread_id") or request.remote_addr or "default"
    used_thread_id = base_thread_id
    
    start_idx = len(collector.events)
    
    def _invoke(thread_id: str):    
        config = {"thread_id": thread_id, "recursion_limit": 15, "callbacks": [collector]}
        return run_coro(agent.ainvoke({"messages": user_input}, config=config))
    
    try:
        # Attempt 1
        resp = _invoke(used_thread_id)
    except Exception as e1:
        # Delete only created event during attempt 1
        if len(collector.events) > start_idx:
            del collector.events[start_idx:]
        used_thread_id = f"{base_thread_id}-{uuid4().hex[:8]}"
        start_idx = len(collector.events)

        try:
            resp = _invoke(used_thread_id)
        except Exception as e2:
            # Delete attempt 2 event (if there are)
            if len(collector.events) > start_idx:
                del collector.events[start_idx:]
            return jsonify({
                "error": "Agent invocation failed after some retries",
                "thread_id": used_thread_id,
                "type": type(e2).__name__,
                "details": str(e2)
            }), 500

    def _latest_artifacts_from_new_events():
        for ev in reversed(collector.events[start_idx:]):
            out = ev.get("output")
            if out is None:
                continue
            if isinstance(out, dict):
                return out.get("content", out)
            return out
        return None

    artifacts = _latest_artifacts_from_new_events()

    return jsonify({
        "reply": resp["messages"][-1].content,
        "artifacts": artifacts,
        "thread_id": used_thread_id
    })

@api.post("/search-flights")
def search_flights_ep():
    """
    Proxy endpoint to search flights via the tool layer.

    Expects JSON body:
      - origin (str): IATA/city/origin label (required)
      - destination (str): IATA/city/destination label (required)
      - departure_date (str): human-friendly date string (required)
      - other optional fields (e.g., adults, children, class, headless...)

    Returns:
      flask.Response: JSON with the tool's result, or {"error": "..."} with HTTP 400 on failure.
    """
    payload = request.get_json(silent=True) or {}
    for k in ("origin", "destination", "departure_date"):
        if not payload.get(k):
            raise BadRequest(f"Missing required field: {k}")
    try:
        result = run_coro(search_flights_tool_fn(**payload))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api.post("/get-flight-urls")
def get_flight_urls_ep():
    """
    Collect booking URLs/providers for a selected flight.

    Expects JSON body:
      - session_id (str): Playwright session id (required)
      - flight_no (int): 1-based index of the chosen flight card (optional, defaults in tool)
      - max_providers (int): limit number of providers to collect (optional)
      - popup_wait_timeout (int): ms to wait after a provider click (optional)

    Returns:
      flask.Response: JSON list of providers (each with provider/price/logo_url/booking_url),
                      or {"error": "..."} with HTTP 400 if the tool fails/validation fails.
    """
    payload = request.get_json(silent=True) or {}
    if not payload.get("session_id"):
        raise BadRequest("Missing required field: session_id")
    try:
        result = run_coro(get_flight_urls_tool_fn(**payload))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api.post("/close-session")
def close_session_ep():
    """Close a Playwright session (browser/context/page) and free resources.

    Expects JSON body:
      - session_id (str): The session id to close (required).

    Returns:
      flask.Response: {"message": "..."} on success, or {"error": "..."} with HTTP 400 on failure.
    """
    payload = request.get_json(silent=True) or {}
    if not payload.get("session_id"):
        raise BadRequest("Missing required field: session_id")
    try:
        msg = run_coro(close_session_tool_fn(**payload))
        return jsonify({"message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=False, port=5000)
