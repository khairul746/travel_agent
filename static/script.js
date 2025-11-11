// script.js v4
console.log("[script.js v4] loaded");

let CURRENT_SESSION_ID = null;

// ------- persistence ------- 
const STATE_KEY = "chat_state_v1";

function loadState() {
  try { return JSON.parse(localStorage.getItem(STATE_KEY)) || {}; }
  catch { return {};}
}

function saveState(state) {
  try { localStorage.setItem(STATE_KEY, JSON.stringify(state)); }
  catch {} 
}

function rehydrateUI() {
  const state = loadState();

  // Rebuild chat bubbles (newest at top to match .prepend behavior)
  const chatBox = byId("chatMessages");
  if (chatBox && Array.isArray(state.chat)) {
    chatBox.innerHTML = "";
    // state.chat is chronological; render in reverse so newest ends up on top via prepend
    state.chat.forEach(item => {
      const b = document.createElement("div");
      b.className = `chat-bubble ${item.role === "user" ? "user-bubble" : "bot-bubble"}`;
      b.innerHTML = DOMPurify.sanitize(marked.parse(item.text)) || "";
      chatBox.prepend(b)
    });
  }

  // Restore artifacts & session
  if (state.artifacts) {
    try {
      CURRENT_SESSION_ID = state.session_id || null;
      renderFlightResults(state.artifacts);

      // Rehydrate providers per flight
      rehydrateProvidersFromState(state);
    }
    catch (e) { console.warn("rehydrate artifacts/providers failed", e); }
  }

  // Rehydrate selected currency on load
  try {
    const codeFromArtifacts = state.artifacts
      ? getCurrencyFromPayload(state.artifacts) : null;
    const code = codeFromArtifacts || state.currency || null;
    if (code) renderSelectedCurrency(code);
  } catch (err) {
    console.warn("rehydrate currency failed", err)
  }
}

function rehydrateProvidersFromState(state) {
  if (!state || !state.providers) return;
  const flightBox = byId("flightResults");
  if (!flightBox) return;

  for (const [no, providers] of Object.entries(state.providers)) {
    const card = flightBox.querySelector(`.flight-card[data-flight-no="${no}"]`);
    if (!card) continue;
    const providersBox = card.querySelector(".providers");
    if (!providersBox) continue;

    renderProviders(providersBox, providers);
    providersBox.hidden = false;
  }
}

// --- chat thread id helpers ---
function genThreadId() {
  return (crypto?.randomUUID && crypto.randomUUID())
    || `t_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,10)}`;
}

function getOrCreateThreadId() {
  const st = loadState();
  if (st.thread_id) return st.thread_id;
  const newId = genThreadId();
  st.thread_id = newId;
  saveState(st);
  return newId;
}

function setThreadId(id) {
  const st = loadState();
  st.thread_id = id;
  saveState(st);
}


// ---------- utils ----------
function byId(id) { return document.getElementById(id); }

function safeParseMaybeJson(v) {
  if (v == null) return null;
  if (typeof v === "string") {
    try { return JSON.parse(v); } catch { return v; }
  }
  return v;
}

// artifacts -> payload (sometimes nested under .content)
function extractPayload(artifacts) {
  const a = safeParseMaybeJson(artifacts) || {};
  return a.content ?? a;
}

// flights -> [{data, flightNo}]
function extractFlights(payload) {
  const flights = payload?.flights;
  if (!flights) return [];

  const entries = Object.entries(flights).map(([k, f], idx) => {
    const m = k.match(/(\d+)/);
    const n = m ? Number(m[1]) : idx + 1; // Extract numeric part for ordering
    return { k, f, n };
  });

  // Sort numerically so 2 comes before 10
  entries.sort((a, b) => a.n - b.n);

  return entries.map(({ k, f, n }, i) => ({
    data: f,
    flightNo: Number.isFinite(n) ? n : (i + 1),
    flightKey: k, // keep original key for stable rehydrate/persist mapping
  }));
}

function getCurrencyFromPayload(artifactsOrPayload) {
  const payload = extractPayload(artifactsOrPayload) || {};
  return ( payload.currency || null )
}

// ---------- renderers ----------
function renderFlightResults(artifacts) {
  const flightBox = byId("flightResults");
  if (!flightBox) return;

  const payload = extractPayload(artifacts);
  CURRENT_SESSION_ID = payload?.session_id ?? null;

  const items = extractFlights(payload);
  if (!items.length) {
    flightBox.innerHTML = "";
    return;
  }

  flightBox.innerHTML = "";
  const wrapper = document.createElement("div");
  wrapper.className = "flight-bubble";

  items.forEach(({ data: f, flightNo, flightKey }) => {
    const card = document.createElement("div");
    card.className = "flight-card";
    // Important: add stable identifiers for rehydration
    card.dataset.flightNo = String(flightNo);
    card.dataset.flightKey = String(flightKey);

    const price = (f.price && (f.price.display || f.price)) || "";
    const airlines = (f.airlines || []).filter(Boolean).join(", ");
    const depAirport = f.departure_airport || f.origin?.name || "";
    const arrAirport = f.arrival_airport || f.destination?.name || "";
    const depTime = f.departure_time || f.departure?.time_label || "";
    const arrTime = f.arrival_time || f.arrival?.time_label || "";
    const duration = f.flight_duration || f.duration_label || "";
    const stops = Number.isFinite(f.stops) ? f.stops : parseInt(f.stops || 0, 10);

    card.innerHTML = `
      <div class="flight-card-detail">
        <div class="col1"><strong>${price}</strong>${airlines}</div>
        <div class="col2">${depAirport} (${depTime}) → ${arrAirport} (${arrTime})</div>
        <div class="col3">${duration} • ${stops} stop${stops === 1 ? "" : "s"}</div>
        <div class="col4"><button class="select-flight-btn">Select Flight</button></div>
      </div>
      <div class="providers" hidden></div>
    `;

    const btn = card.querySelector(".select-flight-btn");
    btn.dataset.flightNo = String(flightNo);
    btn.dataset.flightKey = String(flightKey);
    btn.addEventListener("click", onSelectFlightClick);
    wrapper.appendChild(card);
  });

  flightBox.appendChild(wrapper);
}

function renderProviders(container, providers) {
  container.innerHTML = "";
  const list = document.createElement("div");
  list.className = "providers-list";
  
  (providers || []).forEach(p => {
    const row = document.createElement("div");
    row.className = "provider-item";
    if (p.price) {
      row.innerHTML = `
        <div class="provider-line">
          <img class="provider-logo" src="${p.logo_url}" alt="logo">
          <p class="provider-name">${p.provider || "Provider"}</p>
          <p class="provider-price">${p.price || ""}</p>
          <button onclick="goToLink('${p.booking_url}')" target="_blank">Book</button>
        </div>
      `
    ;}
    list.appendChild(row);
  });
  container.appendChild(list);
  container.hidden = false;
}

function renderSelectedCurrency(currency) {
  const selectBtn = document.querySelector(".select-currency");
  if (!selectBtn) return;
  const dot = selectBtn.querySelector(".selected-dot");
  const code = selectBtn.querySelector(".selected-currency");
  dot?.classList.remove("hidden");
  code?.classList.remove("hidden");
  if (code) code.textContent = currency || "";
}

// ---------- API calls ----------
async function callChat(message) {
  const thread_id = getOrCreateThreadId();
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id }),
  });
  const data = await res.json();
  if (data && data.thread_id && data.thread_id !== thread_id) {
    setThreadId(data.thread_id);
  }
  console.log("[chat]", data);
  return data;
}

async function callGetFlightUrls(payload) {
  const res = await fetch("/api/get-flight-urls", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  console.log("[get-flight-urls]", data);
  return data;
}

async function callSelectCurrency({currency, session_id}) {
  const res = await fetch("api/select-currency",{
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      session_id ? { currency, session_id} : { currency }
    ),
  });
  const data = await res.json();
  console.log("[select-currency]", data);
  return data
}

// ---------- handlers ----------
async function onSelectFlightClick(event) {
  if (SENDING) return;
  SENDING = true;
  setSendBtnLoading(true);

  const btn = event.currentTarget;
  const card = btn.closest(".flight-card");
  const providersBox = card.querySelector(".providers");

  if (!CURRENT_SESSION_ID) {
    providersBox.hidden = false;
    providersBox.textContent = "The session is not yet available. Please send a prompt to have the session_id created.";
    return;
  }
  const flightNo = Number(btn.dataset.flightNo, 10);
  if (!Number.isFinite(flightNo) || flightNo <= 0) {
    console.warn("Invalid flightNo from dataset:", btn.dataset.flightNo);
    return;
  }

  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Getting links…";
  providersBox.hidden = false;
  providersBox.textContent = "Fetching providers…";

  try {
    const links = await callGetFlightUrls({
      session_id: CURRENT_SESSION_ID,
      flight_no: flightNo,
      max_providers: 5,
      popup_wait_timeout: 3000,
    });
    if (Array.isArray(links) && links.length) {
      renderProviders(providersBox, links);
    } else if (links && links.error) {
      providersBox.textContent = `Error: ${links.error}`;
    } else {
      providersBox.textContent = "No links found for this flight.";
    }

    // persist providers box
    const st = loadState();
    st.providers = st.providers || {};
    st.providers[String(flightNo)] = Array.isArray(links) ? links : [];
    saveState(st)


  } catch (e) {
    console.error(e);
    providersBox.textContent = "Failed to fetch links.";
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }

  // Send a follow-up message to the chat logic
  const msg = `
    I selected flight number ${flightNo} but don't call get_flight_urls_tool again 
    because it has already been called by API. Please give detailed information about this
    flight including date, airport, time, airline, price, etc except flight number. Ask a follow up question about
    purpose of the flight (business, holiday, shopping, etc.). After I answer the purpose
    of the flight you can give some suggestions related to the purpose and this flight.
    But, if I have mentioned the purpose of the flight on other selected flight number, 
    don't ask me again, just ask me other questions as you are a travel planner.
  `;
  const chatBox = byId("chatMessages");

  try {
    const data = await callChat(msg);
    const botBubble = document.createElement("div");
    botBubble.className = "chat-bubble bot-bubble";
    botBubble.innerHTML = DOMPurify.sanitize(marked.parse(data.reply)) || "…";
    chatBox.prepend(botBubble);  

    // persist chat
    const st2 = loadState();
    st2.chat = st2.chat || [];
    st2.chat.push({ role: "bot", text: data.reply || "…", ts: Date.now() });
    saveState(st2)

  } catch (e) {
    console.error(e);
    const errorBubble = document.createElement("div");
    errorBubble.className = "chat-bubble bot-bubble";
    errorBubble.innerHTML = `
      <div class="error-bubble">
        <p>⚠️ Could not connect to the server.</p>
        <button class="reset-thread" onclick="resetChatThread()">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
        </button>
      </div>
    `;
    chatBox.prepend(errorBubble);
  } finally {
    setSendBtnLoading(false);
    SENDING = false;
  }
}

async function goToLink(url) {
  window.open(url, '_blank');
}

let SENDING = false;

function setSendBtnLoading(on) {
  const btn = byId("sendChat");
  if (!btn) return;
  btn.disabled = !!on;
  btn.classList.toggle("is-loading", !!on);
}

async function sendMessage() {
  if (SENDING) return;

  const input = byId("userInput");
  const msg = (input.value || "").trim();

  if (!msg) {
    input.focus();
    return;
  };

  SENDING = true;
  setSendBtnLoading(true);
  
  const chatBox = byId("chatMessages");
  
  // render user bubble
  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble user-bubble";
  userBubble.innerHTML = DOMPurify.sanitize(marked.parse(msg));
  chatBox.prepend(userBubble);
  
  // persist user bubble
  const st1 = loadState();
  st1.chat = st1.chat || [];
  st1.chat.push({ role: "user", text: msg, ts: Date.now() });
  saveState(st1)

  input.value = "";

  try {
    const data = await callChat(msg);

    // render bot bubble
    const botBubble = document.createElement("div");
    botBubble.className = "chat-bubble bot-bubble";
    botBubble.innerHTML = DOMPurify.sanitize(marked.parse(data.reply)) || "…";
    chatBox.prepend(botBubble);

    // render results on left overlay
    if (data.artifacts) {
      renderFlightResults(data.artifacts);
      // After re-rendering flight cards, also rehydrate any cached providers
      const stateNow = loadState();
      if (stateNow && stateNow.artifacts === data.artifacts) rehydrateProvidersFromState(stateNow);
    }

    // render selected currency
    if (data.artifacts) {
      currency = data.artifacts.currency;
      renderSelectedCurrency(currency);
      const st1 = loadState();
      st1.currency = currency;
    }

    // persist bot bubble and artifacts
    const st2 = loadState();
    st2.chat = st2.chat || [];
    st2.chat.push( { role: "bot", text: data.reply || "…", ts: Date.now() });

    if (data.artifacts) {
      st2.artifacts = data.artifacts;
      const payload = safeParseMaybeJson(data.artifacts);
      const content = payload && (payload.content ?? payload);
      st2.session_id = content?.session_id ?? null;
    }

    saveState(st2);

  } catch (e) {
    console.error(e);
    const errorBubble = document.createElement("div");
    errorBubble.className = "chat-bubble bot-bubble";
    errorBubble.innerHTML = `
      <div class="error-bubble">
        <p>⚠️ Could not connect to the server.</p>
        <button class="reset-thread" onclick="resetChatThread()">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
        </button>
      </div>
    `;
    chatBox.prepend(errorBubble);
  } finally {
    setSendBtnLoading(false);
    SENDING = false;
  }
}

function handleKeyDown(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
}

// expose
window.sendMessage = sendMessage;
window.handleKeyDown = handleKeyDown;

// reset chat thread
function resetChatThread() {
  const newId = genThreadId();
  setThreadId(newId);
  location.reload();
  console.log("New thread created");
}

// reset persisted state
function resetChat() {
  localStorage.removeItem(STATE_KEY);
  location.reload();
}
window.resetChat = resetChat;

// rehydrate UI on load
document.addEventListener("DOMContentLoaded", rehydrateUI);


// ==== currency handlers ====
// fetch currencies data
fetch('static/currencies.json')
  .then(response => response.json())
  .then(currency => {
    const currencyList = document.getElementById("currencyList");
    for(const c of currency){
      const label = document.createElement("label");
      label.className = "item";
      label.dataset.name = `${c.name}`;
      label.dataset.code = `${c.code}`;
      label.innerHTML = `
        <input type="radio" name="currency" value="${c.code}">
        <span class="radio"><span class="dot"></span></span>
        <span class="labels"><span>${c.name}</span><span class="code">${c.code}</span></span>`;
      currencyList.appendChild(label);
    }
  })
  
// cancel select a currency
const cancelSelect = () => {
  document.querySelectorAll("input[type='radio']").forEach(
    radio => radio.checked = false
  );
}

// select currency on/off switch
const currencyDialog = document.getElementById('currencyDialog');
const currencyWrapper = document.querySelector('.currency-dialog');

window.showCurrencyDialog = (show) => show ? currencyDialog.showModal() : (cancelSelect() , currencyDialog.close());
currencyDialog.addEventListener('click', (e) => {
  !currencyWrapper.contains(e.target) && currencyDialog.close();
});

// --- Search / filter currency-list ---
const searchInput = document.querySelector('.currency-search [data-role="search"]');
const listEl = document.getElementById('currencyList');

// Normalize input text
const normalize = (s) =>
  (s || '')
    .toString()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, ''); // remove diacritics

const filterCurrencies = (q) => {
  const query = normalize(q.trim());
  const items = listEl.querySelectorAll('.item');

  // if blank, show all currencies
  if (!query) {
    items.forEach(el => { el.style.display = ''; });
    return;
  }

  items.forEach(el => {
    const name = normalize(el.dataset.name);
    const code = normalize(el.dataset.code);
    // match code or name
    const match = code.includes(query) || name.includes(query);
    el.style.display = match ? '' : 'none';
  });
};

// Real-time filter upon user typing
searchInput.addEventListener('input', (e) => filterCurrencies(e.target.value));

// Clear filter upon user close the dialog
currencyDialog.addEventListener('close', () => {
  searchInput.value = '';
  filterCurrencies('');
});

async function setCurrency() {
  if (SENDING) return;
  
  const selected = listEl.querySelector("input[type='radio']:checked");
  if (!selected) {
    alert("Please select a currency first!");
    return;
  }

  const item = selected.closest(".item");
  const currency = item?.dataset?.code;
  if (!currency) return;

  // render selected currency
  renderSelectedCurrency(currency);

  SENDING = true;
  setSendBtnLoading(SENDING);

  // call API for changing currency in backend
  try {
    const sid = CURRENT_SESSION_ID || null;
    result = await callChat(
      `Convert the current currency to ${currency} no matter if the flight results have been there or not. If you need a session, 
      this is the session_id: ${sid} (it might be None, because of the beginning of the conversation).`
    );
    
    const chatBox = byId("chatMessages");
    const botBubble = document.createElement("div");
    botBubble.className = "chat-bubble bot-bubble";
    botBubble.innerHTML = DOMPurify.sanitize(marked.parse(result.reply)) || "…";
    chatBox.prepend(botBubble);  

    // persist chat
    const st = loadState();
    st.chat = st.chat || [];
    st.chat.push({ role: "bot", text: result.reply || "…", ts: Date.now() });
    saveState(st)

    // return converted flight results if any
    const maybeFlights = result?.artifacts?.flights;
    if (maybeFlights) {
      const flightPayload = extractPayload(result.artifacts);
      CURRENT_SESSION_ID = flightPayload.session_id;
      // persist rendered flights
      const st2 = loadState();
      st2.artifacts = flightPayload;
      saveState(st);
      // render converted flights
      renderFlightResults(st2.artifacts);
    }
    
    // Persist selected currency
    const st3 = loadState();
    st3.currency = currency;
    saveState(st3);
  } catch (err) {
    alert(err)
    console.error("Select currency failed", err);
  } finally { 
    currencyDialog.close();
    SENDING = false;
    setSendBtnLoading(SENDING);
  }
}