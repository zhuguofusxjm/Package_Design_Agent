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

const SIDE_SKILLS = new Set(["case_match", "summary"]);

const SKILL_TITLES = {
  socratic: "苏格拉底问询",
  tag_inference: "设计标签",
  case_match: "匹配案例",
  llm_supplement: "LLM 补充建议",
  self_analysis: "看自己",
  competitor_analysis: "看对手",
  summary: "Summary",
};

const sideArtifacts = {};
let activeTab = null;
const inlineBubbles = {};
let evtSource = null;

function renderTabs() {
  tabsEl.innerHTML = "";
  Object.values(sideArtifacts).forEach((a) => {
    const el = document.createElement("div");
    el.className = "tab" + (activeTab === a.skill_id ? " active" : "");
    el.innerHTML = `${a.title}<span class="ver">v${a.version}</span>`;
    el.onclick = () => { activeTab = a.skill_id; renderTabs(); renderArtifact(); };
    tabsEl.appendChild(el);
  });
}

function renderArtifact() {
  artifactEl.innerHTML = "";
  if (!activeTab) {
    artifactEl.innerHTML = '<div style="color:#9ca3af;padding:24px;text-align:center;font-size:13px;">尚未生成报告</div>';
    return;
  }
  const a = sideArtifacts[activeTab];
  if (!a) return;
  if (a.skill_id === "case_match") {
    const cases = (a.content && a.content.cases) || [];
    if (!cases.length) {
      artifactEl.innerHTML = '<div style="color:#9ca3af;padding:24px;text-align:center;font-size:13px;">没有匹配到案例</div>';
      return;
    }
    const grid = document.createElement("div");
    grid.className = "case-grid";
    cases.forEach((c) => {
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
  } else {
    const div = document.createElement("div");
    div.className = "markdown";
    div.innerHTML = marked.parse(a.content || "");
    artifactEl.appendChild(div);
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

function pushChat(role, content) {
  const el = document.createElement("div");
  el.className = "message " + role;
  el.textContent = content;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

function pushViewLink(skillId, version) {
  const el = document.createElement("div");
  el.className = "message assistant";
  const title = SKILL_TITLES[skillId] || skillId;
  el.textContent = `${title} 已生成（v${version}）`;
  const link = document.createElement("div");
  link.className = "view-link";
  link.textContent = `→ 在右栏查看 ${title}`;
  link.onclick = () => {
    activeTab = skillId;
    sidePane.classList.remove("collapsed");
    renderTabs();
    renderArtifact();
  };
  el.appendChild(link);
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function ensureInlineBubble(skillId, title) {
  let bubble = inlineBubbles[skillId];
  if (bubble) return bubble;
  const el = document.createElement("div");
  el.className = "message assistant skill-bubble";
  const head = document.createElement("div");
  head.className = "skill-head";
  head.textContent = title;
  const body = document.createElement("div");
  body.className = "skill-body markdown";
  el.appendChild(head);
  el.appendChild(body);
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  bubble = { el, head, body, buf: "" };
  inlineBubbles[skillId] = bubble;
  return bubble;
}

function renderTagList(bubble, content) {
  bubble.body.innerHTML = "";
  const wrap = document.createElement("div");
  (content.selected || []).forEach((t) => {
    const pill = document.createElement("span");
    pill.className = "tag-pill";
    pill.textContent = t.name;
    pill.title = t.reason;
    wrap.appendChild(pill);
  });
  bubble.body.appendChild(wrap);
  if (content.reasoning) {
    const reason = document.createElement("div");
    reason.style.marginTop = "8px";
    reason.style.fontSize = "13px";
    reason.style.color = "#374151";
    reason.textContent = content.reasoning;
    bubble.body.appendChild(reason);
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function handleEvent(ev) {
  if (ev.type === "phase_change") {
    phasePill.textContent = ev.phase;
    return;
  }
  if (ev.type === "chat_message") {
    pushChat("assistant", ev.content);
    return;
  }
  if (ev.type === "artifact_started") {
    const skillId = ev.skill_id;
    const title = SKILL_TITLES[skillId] || ev.title || skillId;
    if (SIDE_SKILLS.has(skillId)) {
      if (!sideArtifacts[skillId]) {
        sideArtifacts[skillId] = { skill_id: skillId, title, version: ev.version || 1, content: skillId === "case_match" ? { cases: [] } : "" };
      } else {
        sideArtifacts[skillId].version = ev.version || sideArtifacts[skillId].version;
      }
      renderTabs();
    } else {
      delete inlineBubbles[skillId];
      ensureInlineBubble(skillId, `${title}（生成中...）`);
    }
    return;
  }
  if (ev.type === "artifact_delta") {
    const skillId = ev.skill_id;
    if (SIDE_SKILLS.has(skillId)) {
      const a = sideArtifacts[skillId];
      if (a && typeof a.content === "string") {
        a.content += ev.chunk || "";
        if (activeTab === skillId) renderArtifact();
      }
      return;
    }
    if (skillId === "tag_inference") return;
    const bubble = inlineBubbles[skillId];
    if (bubble) {
      bubble.buf += ev.chunk || "";
      bubble.body.innerHTML = marked.parse(bubble.buf);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
    return;
  }
  if (ev.type === "artifact_completed") {
    const skillId = ev.skill_id;
    const title = SKILL_TITLES[skillId] || skillId;
    const payloadContent = ev.payload && ev.payload.content !== undefined ? ev.payload.content : null;
    if (SIDE_SKILLS.has(skillId)) {
      let a = sideArtifacts[skillId];
      if (!a) {
        a = { skill_id: skillId, title, version: ev.version || 1, content: skillId === "case_match" ? { cases: [] } : "" };
        sideArtifacts[skillId] = a;
      }
      if (payloadContent !== null) a.content = payloadContent;
      a.version = ev.version || a.version;
      if (!activeTab) activeTab = skillId;
      sidePane.classList.remove("collapsed");
      renderTabs();
      if (activeTab === skillId) renderArtifact();
      pushViewLink(skillId, a.version);
      return;
    }
    const bubble = inlineBubbles[skillId];
    if (skillId === "tag_inference" && bubble) {
      bubble.head.textContent = title;
      renderTagList(bubble, payloadContent || { selected: [], reasoning: "" });
      return;
    }
    if (bubble) {
      bubble.head.textContent = title;
      const finalText = (typeof payloadContent === "string" && payloadContent) || bubble.buf;
      bubble.body.innerHTML = marked.parse(finalText);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
    return;
  }
  if (ev.type === "error") {
    pushChat("assistant", `[错误] ${ev.message}`);
  }
}

function openStream() {
  if (evtSource) evtSource.close();
  evtSource = new EventSource(`/api/stream/${sessionId}`);
  const dispatch = (e) => { try { handleEvent(JSON.parse(e.data)); } catch (err) { console.error(err); } };
  evtSource.onmessage = dispatch;
  ["artifact_started", "artifact_delta", "artifact_completed", "phase_change", "chat_message"].forEach((t) => {
    evtSource.addEventListener(t, dispatch);
  });
  evtSource.addEventListener("error", (e) => { if (e.data) dispatch(e); });
}

async function send() {
  const msg = inputEl.value.trim();
  if (!msg) return;
  pushChat("user", msg);
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
renderArtifact();
openStream();
