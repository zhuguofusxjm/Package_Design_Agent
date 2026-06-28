const SESSION_KEY = "package_design_session_id";
let sessionId = localStorage.getItem(SESSION_KEY);
if (!sessionId) {
  sessionId = Math.random().toString(36).slice(2);
  localStorage.setItem(SESSION_KEY, sessionId);
}

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const tabsEl = document.getElementById("tabs");
const artifactEl = document.getElementById("artifact");
const phasePill = document.getElementById("phase-pill");
const sidePane = document.getElementById("side-pane");
const toggleBtn = document.getElementById("toggle-side");

const artifacts = {};
let activeTab = null;
let evtSource = null;

const SKILL_TITLES = {
  socratic: "思考过程",
  tag_inference: "设计标签建议",
  case_match: "匹配案例",
  llm_supplement: "LLM 补充建议",
  self_analysis: "看自己",
  competitor_analysis: "看对手",
  summary: "Summary",
};

function renderTabs() {
  tabsEl.innerHTML = "";
  Object.values(artifacts).forEach((a) => {
    const el = document.createElement("div");
    el.className = "tab" + (activeTab === a.skill_id ? " active" : "");
    el.innerHTML = `${a.title}<span class="ver">v${a.version}</span>`;
    el.onclick = () => { activeTab = a.skill_id; renderTabs(); renderArtifact(); };
    tabsEl.appendChild(el);
  });
}

function renderArtifact() {
  artifactEl.innerHTML = "";
  if (!activeTab) return;
  const a = artifacts[activeTab];
  if (!a) return;
  if (a.type === "markdown") {
    const div = document.createElement("div");
    div.className = "markdown";
    div.innerHTML = marked.parse(a.content || "");
    artifactEl.appendChild(div);
  } else if (a.type === "tag_list") {
    const wrap = document.createElement("div");
    (a.content.selected || []).forEach((t) => {
      const pill = document.createElement("span");
      pill.className = "tag-pill";
      pill.textContent = t.name;
      pill.title = t.reason;
      wrap.appendChild(pill);
    });
    const reason = document.createElement("div");
    reason.style.marginTop = "12px";
    reason.style.fontSize = "13px";
    reason.style.color = "#374151";
    reason.textContent = a.content.reasoning || "";
    artifactEl.appendChild(wrap);
    artifactEl.appendChild(reason);
  } else if (a.type === "case_cards") {
    const grid = document.createElement("div");
    grid.className = "case-grid";
    (a.content.cases || []).forEach((c) => {
      const card = document.createElement("div");
      card.className = "case-card";
      card.innerHTML = `<h4>${c.name}</h4>
        <div class="meta">${c.operator} · ${c.region}</div>
        <div>${c.summary}</div>
        <div class="score">匹配度 ${c.score}</div>`;
      card.onclick = () => openCase(c.case_id);
      grid.appendChild(card);
    });
    artifactEl.appendChild(grid);
  }
}

async function openCase(id) {
  const r = await fetch(`/api/cases/${id}`);
  const c = await r.json();
  artifactEl.innerHTML = `<a style="cursor:pointer;color:#2563eb" id="back">← 返回</a>
    <h2>${c.name}</h2>
    <div class="markdown">${marked.parse(c.detail_md || "")}</div>`;
  document.getElementById("back").onclick = renderArtifact;
}

function pushMessage(role, content, meta) {
  const el = document.createElement("div");
  el.className = "message " + role;
  el.textContent = content;
  if (meta && meta.skill_id) {
    const link = document.createElement("div");
    link.className = "view-link";
    link.textContent = `→ 查看 ${SKILL_TITLES[meta.skill_id] || meta.skill_id}`;
    link.onclick = () => { activeTab = meta.skill_id; sidePane.classList.remove("collapsed"); renderTabs(); renderArtifact(); };
    el.appendChild(link);
  }
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function handleEvent(ev) {
  if (ev.type === "phase_change") {
    phasePill.textContent = ev.phase;
    return;
  }
  if (ev.type === "chat_message") {
    pushMessage("assistant", ev.content);
    return;
  }
  if (ev.type === "artifact_started") {
    artifacts[ev.skill_id] = {
      skill_id: ev.skill_id,
      title: ev.title || SKILL_TITLES[ev.skill_id] || ev.skill_id,
      version: ev.version || 1,
      type: guessType(ev.skill_id),
      content: guessType(ev.skill_id) === "markdown" ? "" : {},
    };
    if (!activeTab) activeTab = ev.skill_id;
    sidePane.classList.remove("collapsed");
    renderTabs();
    renderArtifact();
    return;
  }
  if (ev.type === "artifact_delta") {
    const a = artifacts[ev.skill_id];
    if (a && a.type === "markdown") {
      a.content += ev.chunk || "";
      if (activeTab === ev.skill_id) renderArtifact();
    }
    return;
  }
  if (ev.type === "artifact_completed") {
    const a = artifacts[ev.skill_id];
    if (a && ev.payload && ev.payload.content !== undefined) {
      a.content = ev.payload.content;
    }
    if (a) a.version = ev.version || a.version;
    if (activeTab === ev.skill_id) renderArtifact();
    renderTabs();
    pushMessage("assistant", `${SKILL_TITLES[ev.skill_id] || ev.skill_id} 已更新（v${ev.version}）`, { skill_id: ev.skill_id });
    return;
  }
  if (ev.type === "error") {
    pushMessage("assistant", `[错误] ${ev.message}`);
  }
}

function guessType(skillId) {
  if (skillId === "tag_inference") return "tag_list";
  if (skillId === "case_match") return "case_cards";
  return "markdown";
}

function openStream() {
  if (evtSource) evtSource.close();
  evtSource = new EventSource(`/api/stream/${sessionId}`);
  evtSource.onmessage = (e) => {
    try { handleEvent(JSON.parse(e.data)); } catch (err) { console.error(err); }
  };
  evtSource.addEventListener("artifact_started", (e) => handleEvent(JSON.parse(e.data)));
  evtSource.addEventListener("artifact_delta", (e) => handleEvent(JSON.parse(e.data)));
  evtSource.addEventListener("artifact_completed", (e) => handleEvent(JSON.parse(e.data)));
  evtSource.addEventListener("phase_change", (e) => handleEvent(JSON.parse(e.data)));
  evtSource.addEventListener("chat_message", (e) => handleEvent(JSON.parse(e.data)));
  evtSource.addEventListener("error", (e) => { if (e.data) handleEvent(JSON.parse(e.data)); });
}

async function send() {
  const msg = inputEl.value.trim();
  if (!msg) return;
  pushMessage("user", msg);
  inputEl.value = "";
  sendBtn.disabled = true;
  try {
    await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: msg }),
    });
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.onclick = send;
inputEl.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
toggleBtn.onclick = () => sidePane.classList.toggle("collapsed");
openStream();
