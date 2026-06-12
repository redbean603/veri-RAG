const API_URL = "/query";

let chats = [];
let currentChatId = null;

function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const workspace = document.getElementById("workspace");
  const openBtn = document.getElementById("sidebarOpenBtn");

  if (!sidebar) return;

  sidebar.classList.toggle("collapsed");

  if (workspace) workspace.classList.toggle("sidebar-collapsed");

  if (openBtn) {
    openBtn.style.display = sidebar.classList.contains("collapsed") ? "inline-flex" : "none";
  }
}

function createNewChat() {
  currentChatId = Date.now().toString();
  chats.unshift({
    id: currentChatId,
    title: "New chat",
    createdAt: new Date(),
    messages: []
  });

  const messages = document.getElementById("messages");
  const welcome = document.getElementById("welcomeSection");
  const bottom = document.getElementById("inputBarBottom");

  if (messages) messages.innerHTML = "";
  if (welcome) welcome.style.display = "flex";
  if (bottom) bottom.style.display = "none";

  const w = document.getElementById("queryInputWelcome");
  const b = document.getElementById("queryInputBottom");
  if (w) w.value = "";
  if (b) b.value = "";

  renderChatHistory();
}

function filterChats(value) {
  const q = (value || "").toLowerCase();
  document.querySelectorAll(".chat-item").forEach((item) => {
    item.style.display = item.textContent.toLowerCase().includes(q) ? "block" : "none";
  });
}

function exportChat() {
  const messages = document.getElementById("messages");
  const text = messages ? messages.innerText : "";
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "veri-rag-chat.txt";
  a.click();

  URL.revokeObjectURL(url);
}

function handleKeydown(event, mode) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendQuery();
  }
}

function syncInputs(source) {
  const welcome = document.getElementById("queryInputWelcome");
  const bottom = document.getElementById("queryInputBottom");

  if (!welcome || !bottom) return;

  if (source === "welcome") {
    bottom.value = welcome.value;
    autoResize(welcome);
  } else {
    welcome.value = bottom.value;
    autoResize(bottom);
  }
}

function autoResize(el) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 180) + "px";
}

function setApiStatus(status, text) {
  const dot = document.getElementById("statusDot");
  const label = document.getElementById("statusLabel");

  if (label) label.textContent = text;

  if (dot) {
    dot.className = "status-dot";
    dot.classList.add(status);
  }
}

function getQueryValue() {
  const bottom = document.getElementById("queryInputBottom");
  const welcome = document.getElementById("queryInputWelcome");

  const bottomValue = bottom ? bottom.value.trim() : "";
  const welcomeValue = welcome ? welcome.value.trim() : "";

  return bottomValue || welcomeValue;
}

function clearInputs() {
  const bottom = document.getElementById("queryInputBottom");
  const welcome = document.getElementById("queryInputWelcome");

  if (bottom) {
    bottom.value = "";
    autoResize(bottom);
  }

  if (welcome) {
    welcome.value = "";
    autoResize(welcome);
  }
}

function showChatMode() {
  const welcome = document.getElementById("welcomeSection");
  const bottom = document.getElementById("inputBarBottom");

  if (welcome) welcome.style.display = "none";
  if (bottom) bottom.style.display = "block";
}

function addMessage(role, content) {
  const messages = document.getElementById("messages");
  if (!messages) return;

  const row = document.createElement("div");
  row.className = `message message-${role}`;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  if (role === "assistant") {
    bubble.innerHTML = formatAssistantHtml(content);
  } else {
    bubble.textContent = content;
  }

  row.appendChild(bubble);
  messages.appendChild(row);

  const workspaceContent = document.getElementById("workspaceContent");
  if (workspaceContent) {
    workspaceContent.scrollTop = workspaceContent.scrollHeight;
  }
}

function formatAssistantHtml(data) {
  if (typeof data === "string") {
    return escapeHtml(data).replace(/\n/g, "<br>");
  }

  if (data && typeof data.body === "string") {
    try {
      data = JSON.parse(data.body);
    } catch (e) {
      return escapeHtml(data.body).replace(/\n/g, "<br>");
    }
  }

  const result = data && data["검증결과"] ? data["검증결과"] : data;

  if (result && result["최종답변"]) {
    const steps = result["사고과정"] || [];

    return `
      <div class="result-card">
        <div><strong>검증 결과:</strong> ${escapeHtml(result["기만유형"] || "-")}</div>
        <div><strong>조작 여부:</strong> ${escapeHtml(String(result["조작여부"]))}</div>
        <div><strong>신뢰 점수:</strong> ${escapeHtml(String(result["신뢰점수"] || "-"))}</div>
        <br>
        <div><strong>사고 과정</strong></div>
        <ul>
          ${steps.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}
        </ul>
        <div><strong>최종 답변</strong></div>
        <p>${escapeHtml(result["최종답변"]).replace(/\n/g, "<br>")}</p>
      </div>
    `;
  }

  return `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function buildPayload(value) {
  return {
    query: value,
    top_k: 3
  };
}

async function sendQuery() {
  const value = getQueryValue();

  if (!value) {
    alert("뉴스 URL 또는 기사 내용을 입력하세요.");
    return;
  }

  showChatMode();
  addMessage("user", value);
  clearInputs();

  const loadingId = "loading-" + Date.now();
  addLoadingMessage(loadingId);

  setApiStatus("loading", "검증 중");

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(buildPayload(value))
    });

    const data = await response.json();

    removeLoadingMessage(loadingId);

    if (!response.ok) {
      addMessage("assistant", "오류 발생:\n" + JSON.stringify(data, null, 2));
      setApiStatus("error", "오류");
      return;
    }

    addMessage("assistant", data);
    setApiStatus("ok", "연결됨");

    saveCurrentChat(value, data);
  } catch (error) {
    removeLoadingMessage(loadingId);
    addMessage("assistant", "요청 실패:\n" + error.message);
    setApiStatus("error", "실패");
  }
}

function addLoadingMessage(id) {
  const messages = document.getElementById("messages");
  if (!messages) return;

  const row = document.createElement("div");
  row.className = "message message-assistant";
  row.id = id;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = "검증 중입니다... 잠시만 기다려주세요.";

  row.appendChild(bubble);
  messages.appendChild(row);
}

function removeLoadingMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function saveCurrentChat(query, data) {
  if (!currentChatId) {
    currentChatId = Date.now().toString();
    chats.unshift({
      id: currentChatId,
      title: query.slice(0, 30) || "New chat",
      createdAt: new Date(),
      messages: []
    });
  }

  const chat = chats.find((c) => c.id === currentChatId);
  if (chat) {
    chat.title = query.slice(0, 30) || "New chat";
    chat.messages.push({ role: "user", content: query });
    chat.messages.push({ role: "assistant", content: data });
  }

  renderChatHistory();
}

function renderChatHistory() {
  const list = document.getElementById("chatListToday");
  const group = document.getElementById("historyToday");
  const empty = document.getElementById("historyEmpty");

  if (!list) return;

  list.innerHTML = "";

  if (chats.length === 0) {
    if (empty) empty.style.display = "block";
    if (group) group.style.display = "none";
    return;
  }

  if (empty) empty.style.display = "none";
  if (group) group.style.display = "block";

  chats.forEach((chat) => {
    const li = document.createElement("li");
    li.className = "chat-item";
    li.textContent = chat.title;
    li.onclick = () => loadChat(chat.id);
    list.appendChild(li);
  });
}

function loadChat(id) {
  const chat = chats.find((c) => c.id === id);
  if (!chat) return;

  currentChatId = id;
  showChatMode();

  const messages = document.getElementById("messages");
  if (messages) messages.innerHTML = "";

  chat.messages.forEach((m) => addMessage(m.role, m.content));
}

window.addEventListener("DOMContentLoaded", () => {
  setApiStatus("ok", "준비됨");
  renderChatHistory();
});
