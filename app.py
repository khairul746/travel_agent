from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import asyncio
from Agent.llm import agent, collector
import asyncio
from threading import Thread
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from Tools.search_flights import search_flights_tool_fn, get_flight_urls_tool_fn, close_session_tool_fn

app = Flask(__name__)
CORS(app)

api = Blueprint("api", __name__, url_prefix="/api")

_LOOP = asyncio.new_event_loop()
def _loop_forever():
    asyncio.set_event_loop(_LOOP)
    _LOOP.run_forever()

Thread(target=_loop_forever, daemon=True).start()

def run_coro(coro, timeout=120):
    fut = asyncio.run_coroutine_threadsafe(coro, _LOOP)
    return fut.result(timeout=timeout)

@app.route("/")
def main():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True) or {}
    user_input = body.get("message", "")
    thread_id = body.get("thread_id", request.remote_addr or "default")
    config = {"thread_id": thread_id, "recursion_limit": 15, "callbacks": [collector]}
    resp = run_coro(agent.ainvoke({"messages": user_input}, config=config))
    return jsonify({
        "reply": resp["messages"][-1].content,
        "artifacts": collector.events[-1]["output"].content if collector.events else "No artifacts",
    })

@api.post("/search-flights")
def search_flights_ep():
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
    app.run(debug=True)

