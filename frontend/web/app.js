/* ═══════════════════════════════════════════════
   Veri-RAG · app.js
   Set API_BASE to your FastAPI server URL.
   Same-origin (empty string) works when served
   through FastAPI's StaticFiles mount.
═══════════════════════════════════════════════ */

const API_BASE       = "";
const QUERY_ENDPOINT = "/query";  // POST { query } → { answer }

/* ═══════════════════════════════════════════════
   STATE
═══════════════════════════════════════════════ */
let state = {
  chats:        [],   // [{ id, title, messages: [{id,q,a,ts}] }]
  activeChatId: null,
  loading:      false,
};

/* ═══════════════════════════════════════════════
   BOOT
═══════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
  loadStateFromStorage();
  renderChatList();
  applyMode();         // welcome vs chat layout
  checkApiHealth();
});

/* ═══════════════════════════════════════════════
   STORAGE
═══════════════════════════════════════════════ */
function saveStateToStorage() {
  try {
    localStorage.setItem("verirag_chats",  JSON.stringify(state.chats));
    localStorage.setItem("verirag_active", state.activeChatId ?? "");
  } catch (_) {}
}

function loadStateFromStorage() {
  try {
    const chats  = localStorage.getItem("verirag_chats");
    const active = localStorage.getItem("verirag_active");
    if (chats)  state.chats = JSON.parse(chats);
    if (active && state.chats.find(c => c.id === active)) {
      state.activeChatId = active;
    }
  } catch (_) {}
}

/* ═══════════════════════════════════════════════
   LAYOUT MODE
   - "welcome" : orb + centered input visible, bottom bar hidden
   - "chat"    : messages visible, bottom bar shown
═══════════════════════════════════════════════ */
function applyMode() {
  const chat         = activeChat();
  const hasMessages  = chat && chat.messages.length > 0;
  const welcome      = document.getElementById("welcomeSection");
  const messages     = document.getElementById("messages");
  const bottomBar    = document.getElementById("inputBarBottom");

  if (hasMessages) {
    welcome.style.display   = "none";
    messages.style.display  = "flex";
    bottomBar.style.display = "flex";
  } else {
    welcome.style.display   = "flex";
    messages.style.display  = "none";
    bottomBar.style.display = "none";
  }

  renderMessages();
}

/* ═══════════════════════════════════════════════
   createNewChat()
═══════════════════════════════════════════════ */
function createNewChat() {
  const id   = "chat_" + Date.now();
  const chat = { id, title: "New Chat", messages: [], createdAt: Date.now() };

  state.chats.unshift(chat);
  state.activeChatId = id;

  saveStateToStorage();
  renderChatList();
  applyMode();

  focusInput();
}

/* ═══════════════════════════════════════════════
   switchChat(id) / deleteChat(id, event)
═══════════════════════════════════════════════ */
function switchChat(id) {
  state.activeChatId = id;
  saveStateToStorage();
  renderChatList();
  applyMode();
  focusInput();
}

function deleteChat(id, event) {
  event.stopPropagation();
  state.chats = state.chats.filter(c => c.id !== id);

  if (state.activeChatId === id) {
    state.activeChatId = state.chats.length ? state.chats[0].id : null;
  }

  saveStateToStorage();
  renderChatList();
  applyMode();
}

/* ═══════════════════════════════════════════════
   sendQuery()
═══════════════════════════════════════════════ */
async function sendQuery() {
  // Read whichever input is visible
  const input = visibleInput();
  const query = input.value.trim();
  if (!query || state.loading) return;

  // Auto-create chat if none active
  if (!state.activeChatId) {
    const id   = "chat_" + Date.now();
    const chat = { id, title: "New Chat", messages: [], createdAt: Date.now() };
    state.chats.unshift(chat);
    state.activeChatId = id;
    renderChatList();
  }

  const chat = activeChat();
  if (!chat) return;

  // Set title from first query
  if (chat.title === "New Chat") {
    chat.title = query.length > 44 ? query.slice(0, 44) + "…" : query;
    renderChatList();
  }

  // Clear input
  input.value = "";
  clearBothInputs();

  // Add message (a = null = loading)
  const msgId = "msg_" + Date.now();
  chat.messages.push({ id: msgId, q: query, a: null, ts: Date.now() });

  saveStateToStorage();
  applyMode();      // switches to chat layout
  scrollToBottom();
  showLoading(msgId);

  state.loading = true;
  setSendDisabled(true);

  try {
    const res    = await fetchQuery(query);
    const answer = res.answer ?? res.result ?? JSON.stringify(res);
    const msg    = chat.messages.find(m => m.id === msgId);
    if (msg) msg.a = answer;
    saveStateToStorage();
    renderMessages();
    scrollToBottom();
  } catch (err) {
    const msg = chat.messages.find(m => m.id === msgId);
    if (msg) msg.a = `⚠️ Error: ${err.message}`;
    renderMessages();
    scrollToBottom();
  } finally {
    state.loading = false;
    setSendDisabled(false);
    focusInput();
  }
}

/* ═══════════════════════════════════════════════
   fetchQuery(query) — calls POST /query
═══════════════════════════════════════════════ */
async function fetchQuery(query) {
  const res = await fetch(`${API_BASE}${QUERY_ENDPOINT}`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ query }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`HTTP ${res.status}: ${text}`);
  }

  return res.json();
}

/* ═══════════════════════════════════════════════
   showLoading(msgId) — animated dots
═══════════════════════════════════════════════ */
function showLoading(msgId) {
  const el = document.getElementById(`ai_${msgId}`);
  if (!el) return;
  el.innerHTML = `
    <div class="loading-dots">
      <div class="dots"><span></span><span></span><span></span></div>
      <span>Thinking…</span>
    </div>`;
}

/* ═══════════════════════════════════════════════
   renderMessages()
═══════════════════════════════════════════════ */
function renderMessages() {
  const container = document.getElementById("messages");
  const chat      = activeChat();

  if (!chat || chat.messages.length === 0) {
    container.innerHTML = "";
    return;
  }

  container.innerHTML = chat.messages.map((msg, i) => `
    <div class="message-block">
      ${i > 0 ? '<div class="message-divider"></div>' : ""}

      <!-- User bubble -->
      <div class="turn-user">
        <div class="bubble-user">${escapeHtml(msg.q)}</div>
      </div>

      <!-- AI turn -->
      <div class="turn-ai">
        <div class="ai-avatar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="6"  r="3" fill="currentColor"/>
            <circle cx="5"  cy="18" r="3" fill="currentColor" opacity=".7"/>
            <circle cx="19" cy="18" r="3" fill="currentColor" opacity=".7"/>
            <line x1="12" y1="9" x2="5"  y2="15" stroke="currentColor" stroke-width="1.5"/>
            <line x1="12" y1="9" x2="19" y2="15" stroke="currentColor" stroke-width="1.5"/>
            <line x1="8"  y1="18" x2="16" y2="18" stroke="currentColor" stroke-width="1.5"/>
          </svg>
        </div>
        <div class="ai-body">
          <div class="ai-name">Veri-RAG</div>
          <div class="ai-text" id="ai_${msg.id}">
            ${msg.a === null ? "" : ""}
          </div>
          ${msg.a !== null ? `
          <div class="ai-meta">
            <span>${formatTime(msg.ts)}</span>
            <span>·</span>
            <span>Graph RAG</span>
          </div>` : ""}
        </div>
      </div>
    </div>
  `).join("");

  // Render text after DOM is set
  chat.messages.forEach(msg => {
    if (msg.a !== null) {
      const el = document.getElementById(`ai_${msg.id}`);
      if (el) renderAnswer(el, msg.a);
    } else {
      showLoading(msg.id);
    }
  });
}

/* ═══════════════════════════════════════════════
   renderAnswer(el, text)
═══════════════════════════════════════════════ */
function renderAnswer(el, text) {
  el.innerHTML = escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`\n]+)`/g,   "<code>$1</code>")
    .replace(/\n/g,            "<br/>");
}

/* ═══════════════════════════════════════════════
   renderChatList()
═══════════════════════════════════════════════ */
function renderChatList() {
  const now        = Date.now();
  const DAY        = 86_400_000;
  const todayStart = startOfDay(now);
  const yestStart  = startOfDay(now - DAY);

  const groups = { today: [], yesterday: [], older: [] };

  state.chats.forEach(chat => {
    if      (chat.createdAt >= todayStart) groups.today.push(chat);
    else if (chat.createdAt >= yestStart)  groups.yesterday.push(chat);
    else                                   groups.older.push(chat);
  });

  const fill = (listId, chats) => {
    document.getElementById(listId).innerHTML = chats.map(chat => `
      <li class="chat-item ${chat.id === state.activeChatId ? "active" : ""}"
          onclick="switchChat('${chat.id}')">
        <span class="chat-item-title">${escapeHtml(chat.title)}</span>
        <button class="chat-item-del" onclick="deleteChat('${chat.id}', event)" title="Delete">×</button>
      </li>
    `).join("");
  };

  fill("chatListToday",     groups.today);
  fill("chatListYesterday", groups.yesterday);
  fill("chatListOlder",     groups.older);

  document.getElementById("historyToday").style.display     = groups.today.length     ? "" : "none";
  document.getElementById("historyYesterday").style.display = groups.yesterday.length ? "" : "none";
  document.getElementById("historyOlder").style.display     = groups.older.length     ? "" : "none";
  document.getElementById("historyEmpty").style.display     = state.chats.length      ? "none" : "";
}

/* ═══════════════════════════════════════════════
   filterChats(query)
═══════════════════════════════════════════════ */
function filterChats(q) {
  const term = q.toLowerCase();
  document.querySelectorAll(".chat-item").forEach(el => {
    const title = el.querySelector(".chat-item-title")?.textContent.toLowerCase() ?? "";
    el.style.display = title.includes(term) ? "" : "none";
  });
}

/* ═══════════════════════════════════════════════
   exportChat()
═══════════════════════════════════════════════ */
function exportChat() {
  const chat = activeChat();
  if (!chat || !chat.messages.length) { alert("No conversation to export."); return; }

  const lines = chat.messages.map(m =>
    `[${new Date(m.ts).toLocaleString()}]\nQ: ${m.q}\nA: ${m.a ?? "(loading...)"}`
  );
  const blob = new Blob(["Veri-RAG Export\n" + chat.title + "\n\n" + lines.join("\n\n---\n\n")], { type: "text/plain" });
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement("a"), { href: url, download: `verirag_${Date.now()}.txt` });
  a.click();
  URL.revokeObjectURL(url);
}

/* ═══════════════════════════════════════════════
   navigate(page)
═══════════════════════════════════════════════ */
function navigate(page) {
  document.querySelectorAll(".nav-item").forEach(el =>
    el.classList.toggle("active", el.dataset.page === page)
  );
}

/* ═══════════════════════════════════════════════
   toggleSidebar()
═══════════════════════════════════════════════ */
function toggleSidebar() {
  const sidebar   = document.getElementById("sidebar");
  const openBtn   = document.getElementById("sidebarOpenBtn");
  const collapsed = sidebar.classList.toggle("collapsed");
  openBtn.style.display = collapsed ? "flex" : "none";
}

/* ═══════════════════════════════════════════════
   checkApiHealth()
═══════════════════════════════════════════════ */
async function checkApiHealth() {
  const dot   = document.getElementById("statusDot");
  const label = document.getElementById("statusLabel");

  dot.className   = "status-dot loading";
  label.textContent = "…";

  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
    dot.className     = res.ok ? "status-dot ok" : "status-dot error";
    label.textContent = res.ok ? "API Online"    : "API Error";
  } catch (_) {
    dot.className     = "status-dot error";
    label.textContent = "Offline";
  }

  setTimeout(checkApiHealth, 30_000);
}

/* ═══════════════════════════════════════════════
   insertExample(text) — from suggestion cards
═══════════════════════════════════════════════ */
function insertExample(text) {
  const input = document.getElementById("queryInputWelcome");
  input.value = text;
  autoResize(input);
  input.focus();
}

/* ═══════════════════════════════════════════════
   INPUT HELPERS
═══════════════════════════════════════════════ */
function handleKeydown(event, mode) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendQuery();
  }
}

// Keep both textareas in sync so send() always reads the right value
function syncInputs(source) {
  const welcome = document.getElementById("queryInputWelcome");
  const bottom  = document.getElementById("queryInputBottom");
  if (source === "welcome") { bottom.value = welcome.value; autoResize(welcome); }
  else                      { welcome.value = bottom.value; autoResize(bottom); }
}

function visibleInput() {
  const bottomBar = document.getElementById("inputBarBottom");
  return bottomBar.style.display === "none"
    ? document.getElementById("queryInputWelcome")
    : document.getElementById("queryInputBottom");
}

function focusInput() {
  const el = visibleInput();
  if (el) { el.focus(); autoResize(el); }
}

function clearBothInputs() {
  ["queryInputWelcome", "queryInputBottom"].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.value = ""; autoResize(el); }
  });
}

function setSendDisabled(disabled) {
  ["btnSendWelcome", "btnSendBottom"].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.disabled = disabled;
  });
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 180) + "px";
}

/* ═══════════════════════════════════════════════
   MISC HELPERS
═══════════════════════════════════════════════ */
function activeChat() {
  return state.chats.find(c => c.id === state.activeChatId) ?? null;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function startOfDay(ts) {
  const d = new Date(ts);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

function scrollToBottom() {
  const el = document.getElementById("workspaceContent");
  if (el) el.scrollTop = el.scrollHeight;
}
