# Travel Agent (Flask + Playwright)  

A small proof-of-concept “chat” app that searches flights and surfaces booking links directly from a conversational UI.  
Back-end is Flask that drives Playwright in a background; front-end is a minimal HTML/JS chat with a flight results overlay.

---

## What this app does

<img src="DemoTravelAgent.gif" style="width: 80vw">

- **Chat to search**: type a prompt like “Find me a flight from Jakarta to Singapore on September 10”.  
- **Inline flight cards**: results render as cards over the left overlay, not inside the chat stream.  
- **Select & get links**: each card has a **Select Flight** button that requests booking/provider links for that option.  
- **Session & thread routing**:  
  - **Playwright sessions** keep a live browser/page per `session_id`.  
  - **Agent threads** keep conversation state per `thread_id`. If the agent call fails, the server **rotates `thread_id` and retries once**.  
- **Graceful shutdown**: when you stop the server, Playwright sessions are closed cleanly to avoid `EPIPE` errors.

---

## Getting started

### Prerequisites
- Python 3.10+  

### Install & run

Prioritize running with Docker (recommended). A local venv/dev workflow is provided as a fallback.

Docker (recommended)

For Windows (cmd.exe) — build and run the container:

```bat
:: 1) Build image
docker build -t travel_agent:latest .

:: 2) Run container (maps port 5000)
docker run --rm -p 8000:8000 --shm-size=1g -e GROQ_API_KEY=YOUR_API_KEY travel-agent:latest

:: then open http://localhost:5000
```

Local development (optional)

If you prefer to run locally in a virtual environment (dev/testing):

```bash
# 1) Create & activate venv (optional but recommended)
uv venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2) Install deps
uv sync

# 3) Install Playwright browsers
python -m playwright install chromium
# On Linux you may need:
# python -m playwright install --with-deps chromium

# 4) Run the app
uv run app.py
# open http://localhost:5000
```

## Front-end usage (high level)

- **Send message**: `sendMessage()` posts `{ message, thread_id }` to `/chat`.  
  - The **loader** shows while sending (CSS toggled via `.is-loading` / `:disabled`).  
  - We **validate message first** so loader doesn’t flash on empty input.
- **Render**:
  - Chat bubbles appear in the right column.  
  - If `artifacts` contain flights, we overlay **flight cards** on the left (“flight-bubble” container).
- **Select flight**: clicking “Select Flight” calls `/api/get-flight-urls` with:
  - `session_id` (from the artifacts of `/chat`),  
  - `flight_no` (1-based index of the chosen card).
  - Button(s) are **disabled** during the request to avoid double-clicks; re-enabled when done.
- **Reset chat**: `resetChat()` **rotates** `thread_id` (generates a new one and persists it in localStorage), without nuking the rest of the UI state. This lets the back-end start a fresh agent thread cleanly.

---

## API reference

### `POST /chat`
Invokes the agent with the user message and a conversation `thread_id`.

**Request**
```json
{
  "message": "Find flights Jakarta → Singapore on September 10",
  "thread_id": "t_ce4e…"
}
```

**Response**
```json
{
  "reply": "Here are some options…",
  "artifacts": {
    "session_id": "2ecb52d1-26ce-42a2-8cff-bbcd58d56829",
    "flights": {
      "Flight 1": { "price": "Rp722,600", "airlines": ["Citilink Indonesia"], "departure_time": "6:20 AM", "...": "..." },
      "Flight 2": { "...": "..." }
    },
    "flight_class_used": "Economy",
    "currency": "IDR"
  },
  "thread_id": "t_ce4e…"
}
```
> The server **retries once** with a new `thread_id` if the first agent invocation fails. It returns the final `thread_id` it used.

---

### `POST /api/search-flights`
Runs flight search (usually called by the agent/tooling; you can call it directly for testing).

**Request (example)**
```json
{
  "origin": "Jakarta",
  "destination": "Singapore",
  "departure_date": "September 10",
  "adults": 1,
  "children": 0,
  "headless": true
}
```

**Response**
```json
{
  "session_id": "2ecb52d1-26ce-42a2-8cff-bbcd58d56829",
  "flights": { "Flight 1": { "...": "..." }, "Flight 2": { "...": "..." } },
  "flight_class_used": "Economy",
  "currency": "IDR"
}
```

---

### `POST /api/get-flight-urls`
Returns booking/provider links for the selected flight.

**Request**
```json
{
  "session_id": "2ecb52d1-26ce-42a2-8cff-bbcd58d56829",
  "flight_no": 3,
  "max_providers": 5,
  "popup_wait_timeout": 10000
}
```

**Response (example)**
```json
[
  {
    "logo_url": "https://…/JT.png",
    "provider": "LionAirline",
    "price": "IDR 721,780",
    "booking_url": "https://secure2.lionair.co.id/…"
  }
]
```
> Returns `{ "error": "…" }` with HTTP 400 if validation fails (e.g., missing `session_id`).

Note: some providers return a `call_number` instead of `booking_url` when the option requires a phone booking.

---

### `POST /api/close-session`
Closes a Playwright session and frees resources.

**Request**
```json
{ "session_id": "2ecb52d1-26ce-42a2-8cff-bbcd58d56829" }
```

**Response**
```json
{ "message": "session closed" }
```

---

## Session management & shutdown

### Sessions
- `create_session(headless=True) -> sid`: starts Playwright, launches browser, context & page; stores in `SESSIONS[sid]`.  
- `get_session(sid) -> PWSession`: retrieves an existing session.  
- `close_session(sid)`: closes browser and stops Playwright for that session.


## Data shapes (what the FE expects)

- `artifacts` from `/chat` can be:
  - a direct object: `{ session_id, flights, … }`, or  
  - wrapped inside `{ content: { … } }`.  
  The FE normalizes this (`extractPayload`) and also supports `flights` as either:
  - an object keyed by `"Flight 1" … "Flight N"`, or  
  - an array of flight objects.

- Flight card fields the FE looks for (it handles both legacy and normalized names):
  - `price` or `price.display`  
  - `airlines` (array of strings)  
  - `departure_airport` / `origin.name`  
  - `arrival_airport` / `destination.name`  
  - `departure_time` / `departure.time_label`  
  - `arrival_time` / `arrival.time_label`  
  - `flight_duration` / `duration_label`  
  - `stops` (number)

---

## Troubleshooting

- **EPIPE: broken pipe** when stopping Flask  
  → Install signal handlers that call `close_all_sessions_sync()` and stop the background loop before exit (see “Clean shutdown” above).

- **Flight cards never render**  
  → Ensure you only call **`/chat` once**, then parse `artifacts` correctly (may be JSON string or `{content:{…}}`). Normalize `flights` (object vs array).

- **Select Flight → “Could not connect to the server.”**  
  → Usually means `session_id` was not sent. Always extract `session_id` from `/chat` artifacts and include it in `/api/get-flight-urls`.

- **Loader shows even when message is empty**  
  → Validate input **before** toggling loader state.

- **JS changes not taking effect**  
  → Your browser may cache `script.js`. Do a **hard refresh** (Ctrl/Cmd+F5) or append a cache-buster query:  
  `<script src="{{ url_for('static', filename='script.js') }}?v=4"></script>`

---

## Future ideas

- Persist sessions/threads beyond process lifetime (Redis/DB).  
- Migrate to ASGI (FastAPI) for end-to-end async + native lifespan events.  
- Stronger data contracts using Pydantic models for request/response.  
- Caching & deduplication on flight results, better pagination.  
- Provider integrations beyond scraped links (official APIs, if available).  
- CI for Playwright tests with mock pages.  

---

## Legal & ethical

This demo uses browser automation. **Respect the target sites’ Terms of Service** and robots policies. Use responsibly and for educational purposes.

---

## Contribution

Contributions are always welcome. If you’ve expanded one of the examples, found a mistake, or think something could be explained more clearly, please open a pull request. Improvements are greatly valued.
