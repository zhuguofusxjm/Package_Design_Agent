# 运营商套餐设计辅助智能体 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a conversational operator package design assistant prototype with 7 pluggable Skills, single-step ReAct dispatcher, and DAG-aware incremental rerun.

**Architecture:** FastAPI backend with self-registering Skill modules; SSE streaming of artifacts to a single-page HTML frontend with chat + collapsible right pane. Each Skill is a self-describing folder (yaml + prompt + handler). A SkillRunner does Full Run on first generation and partial reruns driven by a dispatcher Skill that emits structured JSON actions.

**Tech Stack:** Python 3.11, FastAPI, httpx, pydantic, pyyaml, pytest, Tailwind CDN, Alpine.js, DeepSeek API.

**Spec:** `docs/superpowers/specs/2026-06-28-operator-package-design-assistant-design.md`

---

## File Structure

```
SOD/
  pyproject.toml
  .env.example
  app/
    __init__.py
    main.py
    config.py
    models/
      __init__.py
      session.py
      skill_meta.py
    services/
      __init__.py
      deepseek_client.py
      session_store.py
      data_loader.py
      orchestrator.py
    api/
      __init__.py
      chat.py
      cases.py
      events.py
    skills/
      __init__.py
      base.py
      registry.py
      socratic/{skill.yaml,prompt.md,handler.py}
      tag_inference/{skill.yaml,prompt.md,handler.py}
      case_match/{skill.yaml,handler.py}
      llm_supplement/{skill.yaml,prompt.md,handler.py}
      self_analysis/{skill.yaml,prompt.md,handler.py}
      competitor_analysis/{skill.yaml,prompt.md,handler.py}
      summary/{skill.yaml,prompt.md,handler.py}
      dispatcher/{skill.yaml,prompt.md,handler.py}
    data/
      tags.json
      cases.json
      operator_profile.json
  static/
    index.html
    app.js
    style.css
  tests/
    conftest.py
    test_models.py
    test_session_store.py
    test_registry.py
    test_compute_rerun_set.py
    test_case_match.py
    test_dispatcher_parsing.py
    test_orchestrator_full_run.py
    test_orchestrator_partial_run.py
    test_api_integration.py
```

---

## Task 1: Project scaffold and dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "operator-package-design-assistant"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "httpx>=0.27",
  "pydantic>=2.6",
  "pyyaml>=6.0",
  "python-dotenv>=1.0",
  "sse-starlette>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "respx>=0.21"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create .env.example**

```
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

- [ ] **Step 3: Create app/__init__.py (empty file)**

- [ ] **Step 4: Create app/config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    data_dir: str = os.path.join(os.path.dirname(__file__), "data")
    skills_dir: str = os.path.join(os.path.dirname(__file__), "skills")
    static_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

settings = Settings()
```

- [ ] **Step 5: Create tests/conftest.py**

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 6: Install dependencies**

Run: `pip install -e ".[dev]"`
Expected: install succeeds.

- [ ] **Step 7: Commit**

```bash
git init
git add pyproject.toml .env.example app/__init__.py app/config.py tests/conftest.py
git commit -m "chore: bootstrap project scaffold and dependencies"
```

---

## Task 2: Data models

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/session.py`
- Create: `app/models/skill_meta.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Create app/models/__init__.py**

```python
from .session import Session, Message, Artifact, RequirementSummary
from .skill_meta import SkillMeta

__all__ = ["Session", "Message", "Artifact", "RequirementSummary", "SkillMeta"]
```

- [ ] **Step 2: Write failing test for Session creation**

`tests/test_models.py`:

```python
from datetime import datetime
from app.models import Session, Message, Artifact, RequirementSummary

def test_session_initial_state():
    s = Session(session_id="abc")
    assert s.phase == "socratic"
    assert s.socratic_round == 0
    assert s.messages == []
    assert s.artifacts == {}
    assert s.artifact_versions == {}
    assert s.requirement is None

def test_artifact_bump_version():
    a = Artifact(skill_id="x", type="markdown", title="X", content="", version=1, status="done")
    assert a.version == 1

def test_requirement_summary_fields():
    r = RequirementSummary(target_audience="球迷", scenario="世界杯", special_needs=["流量包"])
    assert r.target_audience == "球迷"
```

- [ ] **Step 3: Run test, expect ImportError**

Run: `pytest tests/test_models.py -v`
Expected: FAIL (module not found).

- [ ] **Step 4: Implement app/models/session.py**

```python
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    meta: dict[str, Any] = Field(default_factory=dict)

class RequirementSummary(BaseModel):
    target_audience: str = ""
    scenario: str = ""
    special_needs: list[str] = Field(default_factory=list)
    notes: str = ""

class Artifact(BaseModel):
    skill_id: str
    type: Literal["markdown", "tag_list", "case_cards"]
    title: str
    content: Any = ""
    version: int = 1
    status: Literal["pending", "streaming", "done", "error"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(BaseModel):
    session_id: str
    messages: list[Message] = Field(default_factory=list)
    requirement: RequirementSummary | None = None
    artifacts: dict[str, Artifact] = Field(default_factory=dict)
    artifact_versions: dict[str, list[Artifact]] = Field(default_factory=dict)
    phase: Literal["socratic", "ready", "running", "idle"] = "socratic"
    socratic_round: int = 0
```

- [ ] **Step 5: Implement app/models/skill_meta.py**

```python
from typing import Literal
from pydantic import BaseModel, Field

class SkillMeta(BaseModel):
    id: str
    name: str
    description: str = ""
    artifact_type: Literal["markdown", "tag_list", "case_cards"] = "markdown"
    artifact_title: str = ""
    depends_on: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    uses_llm: bool = True
    streaming: bool = True
    propagate_downstream: bool = False
```

- [ ] **Step 6: Run tests, expect pass**

Run: `pytest tests/test_models.py -v`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add app/models tests/test_models.py
git commit -m "feat(models): add Session, Message, Artifact, SkillMeta"
```

---

## Task 3: Session store

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/session_store.py`
- Create: `tests/test_session_store.py`

- [ ] **Step 1: Create app/services/__init__.py (empty)**

- [ ] **Step 2: Write failing test**

`tests/test_session_store.py`:

```python
import pytest
from app.services.session_store import SessionStore
from app.models import Session

def test_get_or_create_creates_new():
    store = SessionStore()
    s = store.get_or_create("sid-1")
    assert s.session_id == "sid-1"
    assert s.phase == "socratic"

def test_get_or_create_returns_existing():
    store = SessionStore()
    s1 = store.get_or_create("sid-2")
    s1.socratic_round = 3
    s2 = store.get_or_create("sid-2")
    assert s2.socratic_round == 3

def test_get_missing_returns_none():
    store = SessionStore()
    assert store.get("nope") is None
```

- [ ] **Step 3: Run test, expect ImportError**

Run: `pytest tests/test_session_store.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement session_store.py**

```python
from app.models import Session

class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def all_ids(self) -> list[str]:
        return list(self._sessions.keys())

session_store = SessionStore()
```

- [ ] **Step 5: Run tests, expect pass**

Run: `pytest tests/test_session_store.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/services/__init__.py app/services/session_store.py tests/test_session_store.py
git commit -m "feat(services): add in-memory SessionStore"
```

---

## Task 4: Skill base, events, and context

**Files:**
- Create: `app/skills/__init__.py`
- Create: `app/skills/base.py`

- [ ] **Step 1: Create app/skills/__init__.py (empty)**

- [ ] **Step 2: Implement app/skills/base.py**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Literal
from pydantic import BaseModel, Field
from app.models import Artifact, Session, SkillMeta

class SkillEvent(BaseModel):
    type: Literal[
        "artifact_started", "artifact_delta", "artifact_completed",
        "artifact_error", "chat_message",
    ]
    skill_id: str | None = None
    title: str | None = None
    version: int | None = None
    chunk: str | None = None
    payload: Any = None
    message: str | None = None
    role: Literal["user", "assistant"] | None = None
    content: str | None = None

class SkillContext(BaseModel):
    session: Session
    data: dict[str, Any] = Field(default_factory=dict)
    deepseek: Any = None
    hint: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    def upstream_artifact(self, skill_id: str) -> Artifact | None:
        return self.session.artifacts.get(skill_id)

class Skill(ABC):
    meta: SkillMeta

    def __init__(self, meta: SkillMeta) -> None:
        self.meta = meta

    @abstractmethod
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        ...
        if False:
            yield  # pragma: no cover
```

- [ ] **Step 3: Quick smoke test**

Run: `python -c "from app.skills.base import Skill, SkillContext, SkillEvent; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add app/skills/__init__.py app/skills/base.py
git commit -m "feat(skills): add Skill base class, SkillEvent, SkillContext"
```

---

## Task 5: Skill registry and DAG with rerun-set computation

**Files:**
- Create: `app/skills/registry.py`
- Create: `tests/test_registry.py`
- Create: `tests/test_compute_rerun_set.py`

- [ ] **Step 1: Write failing test for registry**

`tests/test_registry.py`:

```python
import pytest
from app.skills.registry import SkillRegistry
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta

class DummySkill(Skill):
    async def run(self, ctx):
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id)

def test_register_and_topo_sort():
    reg = SkillRegistry()
    reg.register(DummySkill(SkillMeta(id="a", name="A", depends_on=[])))
    reg.register(DummySkill(SkillMeta(id="b", name="B", depends_on=["a"])))
    reg.register(DummySkill(SkillMeta(id="c", name="C", depends_on=["a"])))
    order = reg.topological_sort(["a", "b", "c"])
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")

def test_downstream_of():
    reg = SkillRegistry()
    reg.register(DummySkill(SkillMeta(id="a", name="A")))
    reg.register(DummySkill(SkillMeta(id="b", name="B", depends_on=["a"])))
    reg.register(DummySkill(SkillMeta(id="c", name="C", depends_on=["b"])))
    assert set(reg.downstream_of("a")) == {"b"}
    assert set(reg.downstream_of("b")) == {"c"}

def test_cycle_raises():
    reg = SkillRegistry()
    reg.register(DummySkill(SkillMeta(id="a", name="A", depends_on=["b"])))
    reg.register(DummySkill(SkillMeta(id="b", name="B", depends_on=["a"])))
    with pytest.raises(ValueError):
        reg.topological_sort(["a", "b"])
```

- [ ] **Step 2: Write failing test for compute_rerun_set**

`tests/test_compute_rerun_set.py`:

```python
import pytest
from app.skills.registry import SkillRegistry
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta

class _S(Skill):
    async def run(self, ctx):
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id)

@pytest.fixture
def reg():
    r = SkillRegistry()
    r.register(_S(SkillMeta(id="tag_inference", name="T", depends_on=[], propagate_downstream=True)))
    r.register(_S(SkillMeta(id="case_match", name="C", depends_on=["tag_inference"], propagate_downstream=False)))
    r.register(_S(SkillMeta(id="llm_supplement", name="L", depends_on=["tag_inference"], propagate_downstream=False)))
    r.register(_S(SkillMeta(id="self_analysis", name="S", depends_on=["tag_inference"], propagate_downstream=False)))
    r.register(_S(SkillMeta(id="competitor_analysis", name="X", depends_on=["tag_inference"], propagate_downstream=False)))
    r.register(_S(SkillMeta(id="summary", name="SM",
                  depends_on=["case_match","llm_supplement","self_analysis","competitor_analysis"],
                  propagate_downstream=True)))
    return r

def test_rerun_tag_inference_only_adds_summary(reg):
    out = reg.compute_rerun_set(["tag_inference"])
    assert set(out) == {"tag_inference", "summary"}

def test_rerun_competitor_only_adds_summary(reg):
    out = reg.compute_rerun_set(["competitor_analysis"])
    assert set(out) == {"competitor_analysis", "summary"}

def test_rerun_summary_only_stays_summary(reg):
    out = reg.compute_rerun_set(["summary"])
    assert set(out) == {"summary"}

def test_rerun_returns_topological_order(reg):
    out = reg.compute_rerun_set(["competitor_analysis"])
    assert out.index("competitor_analysis") < out.index("summary")

def test_rerun_combination(reg):
    out = reg.compute_rerun_set(["tag_inference", "competitor_analysis"])
    assert set(out) == {"tag_inference", "competitor_analysis", "summary"}
```

- [ ] **Step 3: Run tests, expect ImportError/FAIL**

Run: `pytest tests/test_registry.py tests/test_compute_rerun_set.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement app/skills/registry.py**

```python
from __future__ import annotations
from collections import defaultdict, deque
from typing import Iterable
from app.skills.base import Skill

class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.meta.id] = skill

    def get(self, skill_id: str) -> Skill:
        return self._skills[skill_id]

    def all_ids(self) -> list[str]:
        return list(self._skills.keys())

    def downstream_of(self, skill_id: str) -> list[str]:
        return [s.meta.id for s in self._skills.values()
                if skill_id in s.meta.depends_on]

    def topological_sort(self, skill_ids: Iterable[str]) -> list[str]:
        ids = set(skill_ids)
        indeg: dict[str, int] = {sid: 0 for sid in ids}
        for sid in ids:
            for dep in self._skills[sid].meta.depends_on:
                if dep in ids:
                    indeg[sid] += 1
        queue = deque([sid for sid, d in indeg.items() if d == 0])
        order: list[str] = []
        while queue:
            n = queue.popleft()
            order.append(n)
            for d in self.downstream_of(n):
                if d in indeg:
                    indeg[d] -= 1
                    if indeg[d] == 0:
                        queue.append(d)
        if len(order) != len(ids):
            raise ValueError("Cycle detected in skill DAG")
        return order

    def compute_rerun_set(self, seed: Iterable[str]) -> list[str]:
        rerun: set[str] = set(seed)
        changed = True
        while changed:
            changed = False
            for sid, skill in self._skills.items():
                if sid in rerun:
                    continue
                if not skill.meta.propagate_downstream:
                    continue
                if self._has_ancestor_in(sid, rerun):
                    rerun.add(sid)
                    changed = True
        return self.topological_sort(rerun)

    def _has_ancestor_in(self, sid: str, target: set[str]) -> bool:
        visited: set[str] = set()
        stack: list[str] = list(self._skills[sid].meta.depends_on)
        while stack:
            a = stack.pop()
            if a in target:
                return True
            if a in visited:
                continue
            visited.add(a)
            if a in self._skills:
                stack.extend(self._skills[a].meta.depends_on)
        return False

registry = SkillRegistry()
```

- [ ] **Step 5: Run tests, expect pass**

Run: `pytest tests/test_registry.py tests/test_compute_rerun_set.py -v`
Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add app/skills/registry.py tests/test_registry.py tests/test_compute_rerun_set.py
git commit -m "feat(skills): add SkillRegistry with topo sort and rerun-set computation"
```

---

## Task 6: DeepSeek client (streaming)

**Files:**
- Create: `app/services/deepseek_client.py`
- Create: `tests/test_deepseek_client.py`

- [ ] **Step 1: Write failing test using respx**

`tests/test_deepseek_client.py`:

```python
import pytest
import respx
import httpx
from app.services.deepseek_client import DeepSeekClient

@pytest.mark.asyncio
@respx.mock
async def test_chat_stream_yields_chunks():
    body = (
        'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"好"}}]}\n\n'
        'data: [DONE]\n\n'
    )
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(200, text=body,
            headers={"content-type": "text/event-stream"})
    )
    client = DeepSeekClient(api_key="k", base_url="https://api.deepseek.com", model="m")
    chunks: list[str] = []
    async for c in client.chat_stream([{"role": "user", "content": "hi"}]):
        chunks.append(c)
    assert chunks == ["你", "好"]

@pytest.mark.asyncio
@respx.mock
async def test_chat_non_stream():
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices":[{"message":{"content":"hello world"}}]
        })
    )
    client = DeepSeekClient(api_key="k", base_url="https://api.deepseek.com", model="m")
    text = await client.chat([{"role": "user", "content": "hi"}])
    assert text == "hello world"
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `pytest tests/test_deepseek_client.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement deepseek_client.py**

```python
from __future__ import annotations
import json
from typing import Any, AsyncIterator
import httpx

class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 60.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def chat(self, messages: list[dict[str, Any]], temperature: float = 0.7) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages,
                   "temperature": temperature, "stream": False}
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            r = await cli.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def chat_stream(
        self, messages: list[dict[str, Any]], temperature: float = 0.7
    ) -> AsyncIterator[str]:
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages,
                   "temperature": temperature, "stream": True}
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            async with cli.stream("POST", url, headers=self._headers(), json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_deepseek_client.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/deepseek_client.py tests/test_deepseek_client.py
git commit -m "feat(services): add streaming DeepSeek client"
```

---

## Task 7: Predefined data files and data loader

**Files:**
- Create: `app/data/tags.json`
- Create: `app/data/cases.json`
- Create: `app/data/operator_profile.json`
- Create: `app/services/data_loader.py`
- Create: `tests/test_data_loader.py`

- [ ] **Step 1: Create app/data/tags.json**

```json
[
  {
    "id": "try_and_buy",
    "name": "TryAndBuy",
    "description": "用户先免费试用一段时间，期满后按使用情况转付费。",
    "applicable_audience": ["新用户", "价格敏感型"],
    "applicable_scenarios": ["新业务推广", "高端服务试水"]
  },
  {
    "id": "user_get_user",
    "name": "UserGetUser",
    "description": "老用户邀请新用户加入，双方均获得权益奖励。",
    "applicable_audience": ["年轻用户", "社交活跃群体"],
    "applicable_scenarios": ["拉新增长", "私域裂变"]
  },
  {
    "id": "tiered_billing",
    "name": "分档计费",
    "description": "按使用量划分阶梯，不同档位单价不同。",
    "applicable_audience": ["大流量用户", "重度用户"],
    "applicable_scenarios": ["流量分级", "降低基础门槛"]
  },
  {
    "id": "event_bundle",
    "name": "赛事/事件捆绑",
    "description": "围绕特定赛事或活动周期推出限时套餐，含相关权益。",
    "applicable_audience": ["体育迷", "娱乐用户"],
    "applicable_scenarios": ["世界杯", "演唱会", "电竞赛季"]
  },
  {
    "id": "family_share",
    "name": "家庭共享",
    "description": "多终端/多成员共享一份资源池，主副卡机制。",
    "applicable_audience": ["家庭用户"],
    "applicable_scenarios": ["家庭付费", "多终端打包"]
  }
]
```

- [ ] **Step 2: Create app/data/cases.json**

```json
[
  {
    "id": "case_001",
    "name": "T-Mobile 5G Home Internet 试用计划",
    "operator": "T-Mobile",
    "region": "US",
    "tag_ids": ["try_and_buy", "tiered_billing"],
    "summary": "新用户 15 天免费试用，期满转付费，按速率分档计费。",
    "detail_md": "## 概况\n15 天试用期内不收费，期满转入分档付费。包含三档速率：基础/标准/极速。\n\n## 关键设计\n- 试用期：15 天\n- 转化激励：续费首月 8 折\n- 退订无门槛"
  },
  {
    "id": "case_002",
    "name": "Vodafone World Cup Pass",
    "operator": "Vodafone",
    "region": "EU",
    "tag_ids": ["event_bundle", "tiered_billing"],
    "summary": "世界杯期间 30 天无限流量 + 官方直播权益。",
    "detail_md": "## 概况\n世界杯赛事窗口期推出，含官方直播 APP 免流。\n\n## 关键设计\n- 周期：赛事开赛前 7 天到结束\n- 权益：官方直播 APP 定向流量免计\n- 套餐档：30GB / 60GB / 不限量"
  },
  {
    "id": "case_003",
    "name": "Verizon Family Share Plan",
    "operator": "Verizon",
    "region": "US",
    "tag_ids": ["family_share", "tiered_billing"],
    "summary": "1 主卡带 4 副卡共享 100GB，超出后降速不停。",
    "detail_md": "## 概况\n家庭共享资源池，副卡每张固定月费。\n\n## 关键设计\n- 主卡 + 最多 4 张副卡\n- 100GB 池子，超量降速到 3Mbps\n- 副卡可独立设置消费上限"
  },
  {
    "id": "case_004",
    "name": "Reliance Jio Refer & Earn",
    "operator": "Jio",
    "region": "IN",
    "tag_ids": ["user_get_user"],
    "summary": "邀请好友双方各得 1GB 数据，月上限 10GB。",
    "detail_md": "## 概况\n通过 App 内分享邀请链接，新用户激活后双方各获 1GB。\n\n## 关键设计\n- 上限：每人每月 10GB 奖励\n- 双向激励：邀请方与被邀请方都得益\n- 集成在主 App 内分享"
  },
  {
    "id": "case_005",
    "name": "SK Telecom 5G Try Before You Buy",
    "operator": "SK Telecom",
    "region": "KR",
    "tag_ids": ["try_and_buy"],
    "summary": "5G 套餐 7 天免费体验，无需绑定支付方式。",
    "detail_md": "## 概况\n注册即开通 7 天 5G 体验，期满不自动续费。\n\n## 关键设计\n- 不绑卡试用\n- 体验期权益与正式套餐一致\n- 提供一键转付费引导"
  },
  {
    "id": "case_006",
    "name": "Orange Euro Cup Bundle",
    "operator": "Orange",
    "region": "EU",
    "tag_ids": ["event_bundle", "family_share"],
    "summary": "欧洲杯赛季家庭包，多终端共享，含赛事直播权益。",
    "detail_md": "## 概况\n面向家庭用户，赛事档限时上线。\n\n## 关键设计\n- 主副卡共享数据池\n- 含赛事直播流媒体免流\n- 套餐结束自动转回常规家庭包"
  }
]
```

- [ ] **Step 3: Create app/data/operator_profile.json**

```json
{
  "self": {
    "name": "Acme Mobile",
    "user_segments": [
      {"name": "年轻流量重度用户", "share": 0.32, "arpu": 85, "notes": "对热门赛事和娱乐内容敏感"},
      {"name": "家庭主力用户", "share": 0.28, "arpu": 120, "notes": "倾向多终端家庭包"},
      {"name": "商务用户", "share": 0.18, "arpu": 180, "notes": "看重稳定性和国际漫游"},
      {"name": "价格敏感老用户", "share": 0.22, "arpu": 35, "notes": "对促销和试用敏感"}
    ],
    "current_packages": [
      {"name": "Acme Lite", "price": 39, "data_gb": 10, "features": ["语音 100 分钟"]},
      {"name": "Acme Family 100", "price": 159, "data_gb": 100, "features": ["主卡+3 副卡","家庭池"]},
      {"name": "Acme Pro Unlimited", "price": 199, "data_gb": -1, "features": ["不限量","会员权益"]}
    ]
  },
  "competitors": [
    {
      "name": "Beta Telecom",
      "positioning": "性价比领先",
      "packages": [
        {"name": "Beta Saver 20", "price": 29, "data_gb": 20, "features": ["低价大流量"]},
        {"name": "Beta Sports Pass", "price": 79, "data_gb": 50, "features": ["赛季直播免流"]}
      ],
      "recent_moves": "近期推出赛季限时包，主打体育内容"
    },
    {
      "name": "Gamma Wireless",
      "positioning": "家庭+终端套捆",
      "packages": [
        {"name": "Gamma Home Bundle", "price": 169, "data_gb": 150, "features": ["家宽+移动捆绑"]},
        {"name": "Gamma Try30", "price": 0, "data_gb": 20, "features": ["30 天免费试用"]}
      ],
      "recent_moves": "扩展 TryAndBuy 路径，主推零门槛拉新"
    }
  ]
}
```

- [ ] **Step 4: Write failing test for data_loader**

`tests/test_data_loader.py`:

```python
from app.services.data_loader import load_all

def test_load_all_returns_tags_cases_operator():
    data = load_all()
    assert "tags" in data and "cases" in data and "operator" in data
    assert len(data["tags"]) >= 3
    assert len(data["cases"]) >= 3
    assert data["operator"]["self"]["name"]

def test_tags_indexable_by_id():
    data = load_all()
    by_id = {t["id"]: t for t in data["tags"]}
    assert "try_and_buy" in by_id
```

- [ ] **Step 5: Run test, expect FAIL**

Run: `pytest tests/test_data_loader.py -v`
Expected: FAIL.

- [ ] **Step 6: Implement data_loader.py**

```python
from __future__ import annotations
import json
import os
from app.config import settings

def _read(name: str):
    with open(os.path.join(settings.data_dir, name), "r", encoding="utf-8") as f:
        return json.load(f)

def load_all() -> dict:
    return {
        "tags": _read("tags.json"),
        "cases": _read("cases.json"),
        "operator": _read("operator_profile.json"),
    }
```

- [ ] **Step 7: Run tests, expect pass**

Run: `pytest tests/test_data_loader.py -v`
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add app/data app/services/data_loader.py tests/test_data_loader.py
git commit -m "feat(data): add tags/cases/operator seed JSON and loader"
```

---

## Task 8: Socratic Skill

**Files:**
- Create: `app/skills/socratic/__init__.py`
- Create: `app/skills/socratic/skill.yaml`
- Create: `app/skills/socratic/prompt.md`
- Create: `app/skills/socratic/handler.py`

- [ ] **Step 1: Create `__init__.py` (empty)**

- [ ] **Step 2: Create skill.yaml**

```yaml
id: socratic
name: 苏格拉底问询
description: 通过多轮提问澄清用户的套餐设计需求，最多 5 轮后生成需求摘要
artifact_type: markdown
artifact_title: 思考过程
depends_on: []
inputs: []
outputs: [requirement_summary]
uses_llm: true
streaming: true
propagate_downstream: true
```

- [ ] **Step 3: Create prompt.md**

```
你是一位资深运营商套餐设计顾问。用户刚刚提出一个套餐设计的想法。

你的任务：
1. 如果信息不足以做设计（缺目标人群、场景、特殊需求中的任意一项），请提出 1 个最关键的澄清问题。直接输出问题文字，不要带"问题："前缀。
2. 如果已经轮询了 {round} 轮，或者信息已经足够，请改为输出严格 JSON：
   {"done": true, "summary": {"target_audience": "...", "scenario": "...", "special_needs": ["..."], "notes": "..."}}

已有对话历史：
{history}

用户最新输入：
{user_message}

当前已完成 {round} 轮（上限 5 轮）。
```

- [ ] **Step 4: Implement handler.py**

```python
from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, Artifact, RequirementSummary, Message

class SocraticSkill(Skill):
    MAX_ROUNDS = 5

    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        session = ctx.session
        session.socratic_round += 1
        round_no = session.socratic_round

        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        history = "\n".join(f"{m.role}: {m.content}" for m in session.messages[-10:])
        user_message = session.messages[-1].content if session.messages else ""

        force_done = round_no >= self.MAX_ROUNDS
        instructions = template.format(
            round=round_no, history=history, user_message=user_message
        )
        if force_done:
            instructions += "\n\n注意：已达上限，必须输出 done:true 的 JSON 摘要。"

        yield SkillEvent(
            type="artifact_started", skill_id=self.meta.id,
            title=self.meta.artifact_title, version=1,
        )

        buf = ""
        async for chunk in ctx.deepseek.chat_stream(
            [{"role": "system", "content": "你只输出问题文字或单一 JSON 对象。"},
             {"role": "user", "content": instructions}]
        ):
            buf += chunk
            yield SkillEvent(type="artifact_delta", skill_id=self.meta.id, chunk=chunk)

        parsed = self._try_parse_done(buf)
        if parsed is not None:
            session.requirement = RequirementSummary(**parsed["summary"])
            session.phase = "ready"
            content = f"### 需求摘要\n- 目标人群: {session.requirement.target_audience}\n- 场景: {session.requirement.scenario}\n- 特殊需求: {', '.join(session.requirement.special_needs) or '无'}\n- 备注: {session.requirement.notes}"
        else:
            session.messages.append(Message(role="assistant", content=buf.strip()))
            content = f"### 第 {round_no} 轮问询\n{buf.strip()}"

        session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="markdown",
            title=self.meta.artifact_title, content=content,
            version=1, status="done",
        )
        yield SkillEvent(
            type="artifact_completed", skill_id=self.meta.id, version=1,
            payload={"phase": session.phase},
        )

    @staticmethod
    def _try_parse_done(text: str) -> dict | None:
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            obj = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
        if obj.get("done") and "summary" in obj:
            return obj
        return None

def load() -> SocraticSkill:
    yaml_path = os.path.join(os.path.dirname(__file__), "skill.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return SocraticSkill(meta)
```

- [ ] **Step 5: Smoke test load**

Run: `python -c "from app.skills.socratic.handler import load; print(load().meta.id)"`
Expected: prints `socratic`.

- [ ] **Step 6: Commit**

```bash
git add app/skills/socratic
git commit -m "feat(skills): add Socratic skill"
```

---

## Task 9: Tag inference Skill

**Files:**
- Create: `app/skills/tag_inference/{__init__.py, skill.yaml, prompt.md, handler.py}`

- [ ] **Step 1: __init__.py (empty)**

- [ ] **Step 2: skill.yaml**

```yaml
id: tag_inference
name: 设计标签推理
description: 基于需求摘要从标签库中推理 1-3 个最合适的设计标签
artifact_type: tag_list
artifact_title: 设计标签建议
depends_on: [socratic]
inputs: [requirement_summary]
outputs: [selected_tags, reasoning]
uses_llm: true
streaming: true
propagate_downstream: true
```

- [ ] **Step 3: prompt.md**

```
你是套餐设计专家。根据下面的需求摘要，从标签库中挑选 1-3 个最合适的设计标签。

需求摘要：
- 目标人群: {target_audience}
- 场景: {scenario}
- 特殊需求: {special_needs}
- 备注: {notes}

可选标签库（id | name | description）：
{tag_catalog}

仅输出严格 JSON，格式：
{"selected": [{"tag_id":"...","reason":"为什么选它，1-2 句话"}], "overall_reasoning": "整体选择逻辑"}
```

- [ ] **Step 4: handler.py**

```python
from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, Artifact

class TagInferenceSkill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        tags = ctx.data["tags"]
        req = ctx.session.requirement
        catalog = "\n".join(f'- {t["id"]} | {t["name"]} | {t["description"]}' for t in tags)
        with open(os.path.join(os.path.dirname(__file__), "prompt.md"), "r", encoding="utf-8") as f:
            template = f.read()
        prompt = template.format(
            target_audience=req.target_audience if req else "",
            scenario=req.scenario if req else "",
            special_needs=", ".join(req.special_needs) if req else "",
            notes=req.notes if req else "",
            tag_catalog=catalog,
        )

        prev = ctx.session.artifacts.get(self.meta.id)
        version = (prev.version + 1) if prev else 1
        if prev:
            ctx.session.artifact_versions.setdefault(self.meta.id, []).append(prev)

        yield SkillEvent(type="artifact_started", skill_id=self.meta.id,
                         title=self.meta.artifact_title, version=version)

        buf = ""
        async for chunk in ctx.deepseek.chat_stream(
            [{"role": "system", "content": "只输出 JSON，不要任何其他文字。"},
             {"role": "user", "content": prompt}]
        ):
            buf += chunk
            yield SkillEvent(type="artifact_delta", skill_id=self.meta.id, chunk=chunk)

        parsed = self._extract_json(buf)
        tag_by_id = {t["id"]: t for t in tags}
        selected: list[dict] = []
        for item in parsed.get("selected", []):
            tid = item.get("tag_id")
            if tid in tag_by_id:
                selected.append({"tag_id": tid,
                                 "name": tag_by_id[tid]["name"],
                                 "reason": item.get("reason", "")})
        content = {"selected": selected, "reasoning": parsed.get("overall_reasoning", "")}

        ctx.session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="tag_list",
            title=self.meta.artifact_title, content=content,
            version=version, status="done",
        )
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version)

    @staticmethod
    def _extract_json(text: str) -> dict:
        s, e = text.find("{"), text.rfind("}")
        if s == -1 or e == -1:
            return {"selected": [], "overall_reasoning": text.strip()}
        try:
            return json.loads(text[s:e + 1])
        except json.JSONDecodeError:
            return {"selected": [], "overall_reasoning": text.strip()}

def load() -> TagInferenceSkill:
    with open(os.path.join(os.path.dirname(__file__), "skill.yaml"), "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return TagInferenceSkill(meta)
```

- [ ] **Step 5: Smoke test load**

Run: `python -c "from app.skills.tag_inference.handler import load; print(load().meta.id)"`
Expected: prints `tag_inference`.

- [ ] **Step 6: Commit**

```bash
git add app/skills/tag_inference
git commit -m "feat(skills): add tag inference skill"
```

---

## Task 10: Case match Skill (no LLM)

**Files:**
- Create: `app/skills/case_match/{__init__.py, skill.yaml, handler.py}`
- Create: `tests/test_case_match.py`

- [ ] **Step 1: __init__.py (empty)**

- [ ] **Step 2: skill.yaml**

```yaml
id: case_match
name: 案例匹配
description: 用标签 Jaccard 相似度匹配最多 10 个最相关案例
artifact_type: case_cards
artifact_title: 匹配案例
depends_on: [tag_inference]
inputs: [selected_tags]
outputs: [matched_cases]
uses_llm: false
streaming: false
propagate_downstream: false
```

- [ ] **Step 3: Write failing test**

`tests/test_case_match.py`:

```python
import pytest
from app.skills.case_match.handler import jaccard_match

CASES = [
    {"id":"c1","name":"A","tag_ids":["t1","t2"],"summary":"...","operator":"O","region":"R"},
    {"id":"c2","name":"B","tag_ids":["t2","t3"],"summary":"...","operator":"O","region":"R"},
    {"id":"c3","name":"C","tag_ids":["t4"],"summary":"...","operator":"O","region":"R"},
]

def test_jaccard_returns_only_intersecting():
    out = jaccard_match({"t1","t2"}, CASES, top_k=10)
    ids = [c["case_id"] for c in out]
    assert "c1" in ids and "c2" in ids and "c3" not in ids

def test_jaccard_score_ordering():
    out = jaccard_match({"t1","t2"}, CASES, top_k=10)
    assert out[0]["case_id"] == "c1"

def test_top_k_caps_results():
    out = jaccard_match({"t1","t2"}, CASES, top_k=1)
    assert len(out) == 1
```

- [ ] **Step 4: Run, expect FAIL**

Run: `pytest tests/test_case_match.py -v`
Expected: FAIL.

- [ ] **Step 5: Implement handler.py**

```python
from __future__ import annotations
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, Artifact

def jaccard_match(selected_ids: set[str], cases: list[dict], top_k: int) -> list[dict]:
    scored: list[dict] = []
    for c in cases:
        tags = set(c.get("tag_ids", []))
        inter = tags & selected_ids
        if not inter:
            continue
        union = tags | selected_ids
        score = len(inter) / len(union) if union else 0.0
        scored.append({
            "case_id": c["id"],
            "name": c["name"],
            "operator": c.get("operator", ""),
            "region": c.get("region", ""),
            "summary": c.get("summary", ""),
            "matched_tags": sorted(inter),
            "score": round(score, 3),
        })
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]

class CaseMatchSkill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        prev = ctx.session.artifacts.get(self.meta.id)
        version = (prev.version + 1) if prev else 1
        if prev:
            ctx.session.artifact_versions.setdefault(self.meta.id, []).append(prev)

        yield SkillEvent(type="artifact_started", skill_id=self.meta.id,
                         title=self.meta.artifact_title, version=version)

        tag_art = ctx.upstream_artifact("tag_inference")
        selected_ids: set[str] = set()
        if tag_art and isinstance(tag_art.content, dict):
            selected_ids = {t["tag_id"] for t in tag_art.content.get("selected", [])}
        matched = jaccard_match(selected_ids, ctx.data["cases"], top_k=10)

        ctx.session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="case_cards",
            title=self.meta.artifact_title, content={"cases": matched},
            version=version, status="done",
        )
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version)

def load() -> CaseMatchSkill:
    with open(os.path.join(os.path.dirname(__file__), "skill.yaml"), "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return CaseMatchSkill(meta)
```

- [ ] **Step 6: Run tests, expect pass**

Run: `pytest tests/test_case_match.py -v`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add app/skills/case_match tests/test_case_match.py
git commit -m "feat(skills): add case match skill with Jaccard scoring"
```

---

## Task 11: Four parallel analysis Skills (LLM supplement / self / competitor / summary)

These four follow nearly identical handler structure. Pattern: read upstream artifacts → fill prompt → stream LLM → save markdown artifact.

**Files (4 folders, each with `__init__.py`, `skill.yaml`, `prompt.md`, `handler.py`):**
- Create: `app/skills/llm_supplement/`
- Create: `app/skills/self_analysis/`
- Create: `app/skills/competitor_analysis/`
- Create: `app/skills/summary/`

- [ ] **Step 1: llm_supplement/skill.yaml**

```yaml
id: llm_supplement
name: LLM 通用补充推理
description: 在标签和案例基础上做与外部 LLM 一致的通用补充推理
artifact_type: markdown
artifact_title: LLM 补充建议
depends_on: [tag_inference]
inputs: [requirement_summary, selected_tags]
outputs: [supplement_md]
uses_llm: true
streaming: true
propagate_downstream: false
```

- [ ] **Step 2: llm_supplement/prompt.md**

```
你是一位运营商套餐设计专家。基于需求摘要和已选设计标签，做通用补充推理：
- 关键设计要素
- 价格与权益建议
- 风险点提示

需求摘要：
{requirement_block}

已选设计标签：
{tags_block}

{hint_block}

请输出 markdown，结构清晰，不要重复需求摘要本身。
```

- [ ] **Step 3: self_analysis/skill.yaml**

```yaml
id: self_analysis
name: 看自己
description: 基于本运营商画像和现有套餐，给出适配性与补充建议
artifact_type: markdown
artifact_title: 看自己
depends_on: [tag_inference]
inputs: [requirement_summary, selected_tags, operator.self]
outputs: [self_md]
uses_llm: true
streaming: true
propagate_downstream: false
```

- [ ] **Step 4: self_analysis/prompt.md**

```
你是运营商内部分析师。基于本运营商画像，分析新套餐设计与现有产品/用户画像的适配性。

本运营商画像：
{self_block}

需求摘要：
{requirement_block}

已选设计标签：
{tags_block}

{hint_block}

输出 markdown，包含：用户画像匹配度、与现有套餐的冲突/互补、潜在 ARPU 影响、上市建议。
```

- [ ] **Step 5: competitor_analysis/skill.yaml**

```yaml
id: competitor_analysis
name: 看对手
description: 基于竞品画像，给出差异化与防守建议
artifact_type: markdown
artifact_title: 看对手
depends_on: [tag_inference]
inputs: [requirement_summary, selected_tags, operator.competitors]
outputs: [competitor_md]
uses_llm: true
streaming: true
propagate_downstream: false
```

- [ ] **Step 6: competitor_analysis/prompt.md**

```
你是市场竞争分析师。基于竞品画像，分析本设计如何相对竞品形成差异化或防守。

竞品画像：
{competitors_block}

需求摘要：
{requirement_block}

已选设计标签：
{tags_block}

{hint_block}

输出 markdown，逐个竞品做对比，给出具体的差异化建议或反制策略。
```

- [ ] **Step 7: summary/skill.yaml**

```yaml
id: summary
name: 汇总报告
description: 汇总以上所有产出，输出一份完整设计摘要
artifact_type: markdown
artifact_title: Summary
depends_on: [case_match, llm_supplement, self_analysis, competitor_analysis]
inputs: [all_upstream]
outputs: [summary_md]
uses_llm: true
streaming: true
propagate_downstream: true
```

- [ ] **Step 8: summary/prompt.md**

```
你是套餐设计报告的主笔人。请基于以下所有上游材料，输出一份完整设计 summary。

需求摘要：
{requirement_block}

已选设计标签：
{tags_block}

匹配的参考案例（最多 5 个摘要）：
{cases_block}

LLM 通用补充：
{llm_block}

看自己：
{self_block}

看对手：
{competitor_block}

{hint_block}

输出 markdown，包含：套餐名建议、目标人群、核心权益、定价档位、上市路径、风险与对冲。
```

- [ ] **Step 9: llm_supplement/handler.py** — reusable markdown handler

```python
from __future__ import annotations
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, Artifact

def _format_requirement(req) -> str:
    if not req:
        return "（未提供）"
    return (f"- 目标人群: {req.target_audience}\n"
            f"- 场景: {req.scenario}\n"
            f"- 特殊需求: {', '.join(req.special_needs) or '无'}\n"
            f"- 备注: {req.notes}")

def _format_tags(tag_art) -> str:
    if not tag_art or not isinstance(tag_art.content, dict):
        return "（无）"
    items = tag_art.content.get("selected", [])
    return "\n".join(f'- {it["name"]}（{it["tag_id"]}）: {it["reason"]}' for it in items) or "（无）"

class LLMSupplementSkill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        prev = ctx.session.artifacts.get(self.meta.id)
        version = (prev.version + 1) if prev else 1
        if prev:
            ctx.session.artifact_versions.setdefault(self.meta.id, []).append(prev)

        with open(os.path.join(os.path.dirname(__file__), "prompt.md"), "r", encoding="utf-8") as f:
            tpl = f.read()
        prompt = tpl.format(
            requirement_block=_format_requirement(ctx.session.requirement),
            tags_block=_format_tags(ctx.upstream_artifact("tag_inference")),
            hint_block=f"补充指示：{ctx.hint}" if ctx.hint else "",
        )

        yield SkillEvent(type="artifact_started", skill_id=self.meta.id,
                         title=self.meta.artifact_title, version=version)
        buf = ""
        async for chunk in ctx.deepseek.chat_stream(
            [{"role": "user", "content": prompt}]
        ):
            buf += chunk
            yield SkillEvent(type="artifact_delta", skill_id=self.meta.id, chunk=chunk)

        ctx.session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="markdown",
            title=self.meta.artifact_title, content=buf.strip(),
            version=version, status="done",
        )
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version)

def load() -> LLMSupplementSkill:
    with open(os.path.join(os.path.dirname(__file__), "skill.yaml"), "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return LLMSupplementSkill(meta)
```

- [ ] **Step 10: self_analysis/handler.py** — same shape, different prompt slot

```python
from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, Artifact
from app.skills.llm_supplement.handler import _format_requirement, _format_tags

class SelfAnalysisSkill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        prev = ctx.session.artifacts.get(self.meta.id)
        version = (prev.version + 1) if prev else 1
        if prev:
            ctx.session.artifact_versions.setdefault(self.meta.id, []).append(prev)

        with open(os.path.join(os.path.dirname(__file__), "prompt.md"), "r", encoding="utf-8") as f:
            tpl = f.read()
        self_block = json.dumps(ctx.data["operator"]["self"], ensure_ascii=False, indent=2)
        prompt = tpl.format(
            self_block=self_block,
            requirement_block=_format_requirement(ctx.session.requirement),
            tags_block=_format_tags(ctx.upstream_artifact("tag_inference")),
            hint_block=f"补充指示：{ctx.hint}" if ctx.hint else "",
        )
        yield SkillEvent(type="artifact_started", skill_id=self.meta.id,
                         title=self.meta.artifact_title, version=version)
        buf = ""
        async for chunk in ctx.deepseek.chat_stream([{"role": "user", "content": prompt}]):
            buf += chunk
            yield SkillEvent(type="artifact_delta", skill_id=self.meta.id, chunk=chunk)
        ctx.session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="markdown",
            title=self.meta.artifact_title, content=buf.strip(),
            version=version, status="done",
        )
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version)

def load() -> SelfAnalysisSkill:
    with open(os.path.join(os.path.dirname(__file__), "skill.yaml"), "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return SelfAnalysisSkill(meta)
```

- [ ] **Step 11: competitor_analysis/handler.py**

```python
from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, Artifact
from app.skills.llm_supplement.handler import _format_requirement, _format_tags

class CompetitorAnalysisSkill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        prev = ctx.session.artifacts.get(self.meta.id)
        version = (prev.version + 1) if prev else 1
        if prev:
            ctx.session.artifact_versions.setdefault(self.meta.id, []).append(prev)

        with open(os.path.join(os.path.dirname(__file__), "prompt.md"), "r", encoding="utf-8") as f:
            tpl = f.read()
        competitors_block = json.dumps(ctx.data["operator"]["competitors"], ensure_ascii=False, indent=2)
        prompt = tpl.format(
            competitors_block=competitors_block,
            requirement_block=_format_requirement(ctx.session.requirement),
            tags_block=_format_tags(ctx.upstream_artifact("tag_inference")),
            hint_block=f"补充指示：{ctx.hint}" if ctx.hint else "",
        )
        yield SkillEvent(type="artifact_started", skill_id=self.meta.id,
                         title=self.meta.artifact_title, version=version)
        buf = ""
        async for chunk in ctx.deepseek.chat_stream([{"role": "user", "content": prompt}]):
            buf += chunk
            yield SkillEvent(type="artifact_delta", skill_id=self.meta.id, chunk=chunk)
        ctx.session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="markdown",
            title=self.meta.artifact_title, content=buf.strip(),
            version=version, status="done",
        )
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version)

def load() -> CompetitorAnalysisSkill:
    with open(os.path.join(os.path.dirname(__file__), "skill.yaml"), "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return CompetitorAnalysisSkill(meta)
```

- [ ] **Step 12: summary/handler.py**

```python
from __future__ import annotations
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, Artifact
from app.skills.llm_supplement.handler import _format_requirement, _format_tags

def _format_cases(art) -> str:
    if not art or not isinstance(art.content, dict):
        return "（无）"
    cases = art.content.get("cases", [])[:5]
    return "\n".join(f'- {c["name"]}（{c["operator"]}/{c["region"]}）: {c["summary"]}' for c in cases) or "（无）"

def _md(art) -> str:
    if not art:
        return "（无）"
    return art.content if isinstance(art.content, str) else str(art.content)

class SummarySkill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        prev = ctx.session.artifacts.get(self.meta.id)
        version = (prev.version + 1) if prev else 1
        if prev:
            ctx.session.artifact_versions.setdefault(self.meta.id, []).append(prev)

        with open(os.path.join(os.path.dirname(__file__), "prompt.md"), "r", encoding="utf-8") as f:
            tpl = f.read()
        prompt = tpl.format(
            requirement_block=_format_requirement(ctx.session.requirement),
            tags_block=_format_tags(ctx.upstream_artifact("tag_inference")),
            cases_block=_format_cases(ctx.upstream_artifact("case_match")),
            llm_block=_md(ctx.upstream_artifact("llm_supplement")),
            self_block=_md(ctx.upstream_artifact("self_analysis")),
            competitor_block=_md(ctx.upstream_artifact("competitor_analysis")),
            hint_block=f"补充指示：{ctx.hint}" if ctx.hint else "",
        )
        yield SkillEvent(type="artifact_started", skill_id=self.meta.id,
                         title=self.meta.artifact_title, version=version)
        buf = ""
        async for chunk in ctx.deepseek.chat_stream([{"role": "user", "content": prompt}]):
            buf += chunk
            yield SkillEvent(type="artifact_delta", skill_id=self.meta.id, chunk=chunk)
        ctx.session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="markdown",
            title=self.meta.artifact_title, content=buf.strip(),
            version=version, status="done",
        )
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version)

def load() -> SummarySkill:
    with open(os.path.join(os.path.dirname(__file__), "skill.yaml"), "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return SummarySkill(meta)
```

- [ ] **Step 13: Create `__init__.py` (empty) in each of the four folders**

- [ ] **Step 14: Smoke test load**

Run:
```
python -c "from app.skills.llm_supplement.handler import load as a; from app.skills.self_analysis.handler import load as b; from app.skills.competitor_analysis.handler import load as c; from app.skills.summary.handler import load as d; print(a().meta.id, b().meta.id, c().meta.id, d().meta.id)"
```
Expected: `llm_supplement self_analysis competitor_analysis summary`

- [ ] **Step 15: Commit**

```bash
git add app/skills/llm_supplement app/skills/self_analysis app/skills/competitor_analysis app/skills/summary
git commit -m "feat(skills): add llm_supplement, self_analysis, competitor_analysis, summary"
```

---

## Task 12: Dispatcher Skill (ReAct)

**Files:**
- Create: `app/skills/dispatcher/{__init__.py, skill.yaml, prompt.md, handler.py}`
- Create: `tests/test_dispatcher_parsing.py`

- [ ] **Step 1: __init__.py (empty)**

- [ ] **Step 2: skill.yaml**

```yaml
id: dispatcher
name: ReAct 调度器
description: 在 idle 阶段决定如何处理用户新消息：闲聊回复、改需求、或重跑哪些 skill
artifact_type: markdown
artifact_title: 调度决策
depends_on: []
inputs: []
outputs: [decision]
uses_llm: true
streaming: false
propagate_downstream: false
```

- [ ] **Step 3: prompt.md**

```
你是套餐设计 Agent 的调度器。

当前会话已有 artifacts（skill_id | title | 摘要）：
{artifact_index}

用户新消息：
{user_message}

请输出一个严格 JSON，三选一：
1. {"action":"chat","reply":"<对用户的回答>"}
2. {"action":"revise_requirement","patch":{"target_audience":"...","scenario":"...","special_needs":["..."],"notes":"..."}}
3. {"action":"rerun","skills":["skill_id1",...],"hint":"<给重跑 skill 的额外指示，可省略>"}

可用的 skill id 仅限：tag_inference, case_match, llm_supplement, self_analysis, competitor_analysis, summary

仅输出 JSON。不要 markdown 代码块包裹，不要其他文字。
```

- [ ] **Step 4: Write failing parsing test**

`tests/test_dispatcher_parsing.py`:

```python
from app.skills.dispatcher.handler import parse_decision

def test_parse_chat():
    d = parse_decision('{"action":"chat","reply":"你好"}')
    assert d["action"] == "chat" and d["reply"] == "你好"

def test_parse_rerun():
    d = parse_decision('{"action":"rerun","skills":["competitor_analysis"],"hint":"加上 5G 维度"}')
    assert d["action"] == "rerun"
    assert d["skills"] == ["competitor_analysis"]
    assert d["hint"] == "加上 5G 维度"

def test_parse_handles_markdown_fence():
    d = parse_decision('```json\n{"action":"chat","reply":"hi"}\n```')
    assert d["action"] == "chat"

def test_parse_fallback_to_chat_on_invalid():
    d = parse_decision("just plain text reply not JSON")
    assert d["action"] == "chat"
    assert "just plain text" in d["reply"]

def test_parse_rejects_unknown_skill_id():
    d = parse_decision('{"action":"rerun","skills":["does_not_exist","summary"]}')
    assert d["action"] == "rerun"
    assert d["skills"] == ["summary"]
```

- [ ] **Step 5: Run, expect FAIL**

Run: `pytest tests/test_dispatcher_parsing.py -v`
Expected: FAIL.

- [ ] **Step 6: Implement handler.py**

```python
from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta

VALID_SKILLS = {"tag_inference", "case_match", "llm_supplement",
                "self_analysis", "competitor_analysis", "summary"}

def parse_decision(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    s, e = t.find("{"), t.rfind("}")
    obj = None
    if s != -1 and e != -1:
        try:
            obj = json.loads(t[s:e + 1])
        except json.JSONDecodeError:
            obj = None
    if not isinstance(obj, dict) or obj.get("action") not in {"chat", "revise_requirement", "rerun"}:
        return {"action": "chat", "reply": text.strip()}
    if obj["action"] == "rerun":
        obj["skills"] = [s for s in obj.get("skills", []) if s in VALID_SKILLS]
        obj.setdefault("hint", None)
    return obj

class DispatcherSkill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        index_lines: list[str] = []
        for sid, art in ctx.session.artifacts.items():
            if sid in {"socratic", "dispatcher"}:
                continue
            preview = ""
            if isinstance(art.content, str):
                preview = art.content[:120].replace("\n", " ")
            elif isinstance(art.content, dict):
                preview = json.dumps(art.content, ensure_ascii=False)[:120]
            index_lines.append(f"- {sid} | {art.title} | v{art.version} | {preview}")
        user_message = ctx.session.messages[-1].content if ctx.session.messages else ""

        with open(os.path.join(os.path.dirname(__file__), "prompt.md"), "r", encoding="utf-8") as f:
            tpl = f.read()
        prompt = tpl.format(
            artifact_index="\n".join(index_lines) or "(empty)",
            user_message=user_message,
        )
        raw = await ctx.deepseek.chat(
            [{"role": "system", "content": "你只输出 JSON。"},
             {"role": "user", "content": prompt}]
        )
        decision = parse_decision(raw)
        yield SkillEvent(type="chat_message", role="assistant",
                         content=json.dumps(decision, ensure_ascii=False),
                         payload=decision, skill_id=self.meta.id)

def load() -> DispatcherSkill:
    with open(os.path.join(os.path.dirname(__file__), "skill.yaml"), "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return DispatcherSkill(meta)
```

- [ ] **Step 7: Run tests, expect pass**

Run: `pytest tests/test_dispatcher_parsing.py -v`
Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add app/skills/dispatcher tests/test_dispatcher_parsing.py
git commit -m "feat(skills): add ReAct dispatcher skill"
```

---

## Task 13: Skill autoloader

**Files:**
- Modify: `app/skills/__init__.py`

- [ ] **Step 1: Implement autoload**

`app/skills/__init__.py`:

```python
from __future__ import annotations
import importlib
import os
from app.skills.registry import registry, SkillRegistry

SKILL_FOLDERS = [
    "socratic", "tag_inference", "case_match",
    "llm_supplement", "self_analysis", "competitor_analysis",
    "summary", "dispatcher",
]

def autoload() -> SkillRegistry:
    for folder in SKILL_FOLDERS:
        mod = importlib.import_module(f"app.skills.{folder}.handler")
        registry.register(mod.load())
    return registry
```

- [ ] **Step 2: Smoke test**

Run:
```
python -c "from app.skills import autoload; r = autoload(); print(sorted(r.all_ids()))"
```
Expected: prints `['case_match', 'competitor_analysis', 'dispatcher', 'llm_supplement', 'self_analysis', 'socratic', 'summary', 'tag_inference']`

- [ ] **Step 3: Commit**

```bash
git add app/skills/__init__.py
git commit -m "feat(skills): add skill autoloader"
```

---

## Task 14: Orchestrator (SkillRunner)

**Files:**
- Create: `app/services/orchestrator.py`
- Create: `tests/test_orchestrator_full_run.py`
- Create: `tests/test_orchestrator_partial_run.py`

- [ ] **Step 1: Write failing test — full run**

`tests/test_orchestrator_full_run.py`:

```python
import pytest
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.skills.registry import SkillRegistry
from app.models import SkillMeta, Session, RequirementSummary, Artifact
from app.services.orchestrator import SkillRunner

class _Skill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        yield SkillEvent(type="artifact_started", skill_id=self.meta.id, version=1)
        yield SkillEvent(type="artifact_delta", skill_id=self.meta.id, chunk="x")
        ctx.session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="markdown", title=self.meta.id,
            content="x", version=1, status="done",
        )
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=1)

@pytest.fixture
def runner():
    reg = SkillRegistry()
    for sid, deps, prop in [
        ("tag_inference", [], True),
        ("case_match", ["tag_inference"], False),
        ("llm_supplement", ["tag_inference"], False),
        ("self_analysis", ["tag_inference"], False),
        ("competitor_analysis", ["tag_inference"], False),
        ("summary", ["case_match","llm_supplement","self_analysis","competitor_analysis"], True),
    ]:
        reg.register(_Skill(SkillMeta(id=sid, name=sid, depends_on=deps, propagate_downstream=prop)))
    return SkillRunner(reg)

@pytest.mark.asyncio
async def test_full_run_executes_all_in_topo_order(runner):
    session = Session(session_id="t", phase="ready",
                      requirement=RequirementSummary(target_audience="x", scenario="y"))
    events = []
    skill_order = ["tag_inference", "case_match", "llm_supplement",
                   "self_analysis", "competitor_analysis", "summary"]
    async for ev in runner.run_all(session, data={}, deepseek=None):
        events.append(ev)
    started = [ev.skill_id for ev in events if ev.type == "artifact_started"]
    for s in skill_order:
        assert s in started
    assert started.index("tag_inference") < started.index("case_match")
    assert started.index("competitor_analysis") < started.index("summary")
    assert session.phase == "idle"
```

- [ ] **Step 2: Write failing test — partial run**

`tests/test_orchestrator_partial_run.py`:

```python
import pytest
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.skills.registry import SkillRegistry
from app.models import SkillMeta, Session, Artifact
from app.services.orchestrator import SkillRunner

class _S(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        prev = ctx.session.artifacts.get(self.meta.id)
        version = (prev.version + 1) if prev else 1
        if prev:
            ctx.session.artifact_versions.setdefault(self.meta.id, []).append(prev)
        ctx.session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="markdown", title=self.meta.id,
            content="x", version=version, status="done",
        )
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version)

@pytest.fixture
def runner():
    reg = SkillRegistry()
    reg.register(_S(SkillMeta(id="tag_inference", name="T", depends_on=[], propagate_downstream=True)))
    reg.register(_S(SkillMeta(id="case_match", name="C", depends_on=["tag_inference"], propagate_downstream=False)))
    reg.register(_S(SkillMeta(id="llm_supplement", name="L", depends_on=["tag_inference"], propagate_downstream=False)))
    reg.register(_S(SkillMeta(id="self_analysis", name="S", depends_on=["tag_inference"], propagate_downstream=False)))
    reg.register(_S(SkillMeta(id="competitor_analysis", name="X", depends_on=["tag_inference"], propagate_downstream=False)))
    reg.register(_S(SkillMeta(id="summary", name="SM",
                  depends_on=["case_match","llm_supplement","self_analysis","competitor_analysis"],
                  propagate_downstream=True)))
    return SkillRunner(reg)

@pytest.mark.asyncio
async def test_partial_rerun_competitor_pulls_in_summary_only(runner):
    session = Session(session_id="t", phase="idle")
    for sid in ["tag_inference","case_match","llm_supplement","self_analysis","competitor_analysis","summary"]:
        session.artifacts[sid] = Artifact(skill_id=sid, type="markdown", title=sid, content="x", version=1, status="done")
    completed: list[str] = []
    async for ev in runner.run_partial(session, ["competitor_analysis"], data={}, deepseek=None):
        if ev.type == "artifact_completed":
            completed.append(ev.skill_id)
    assert set(completed) == {"competitor_analysis", "summary"}
    assert session.artifacts["competitor_analysis"].version == 2
    assert session.artifacts["case_match"].version == 1

@pytest.mark.asyncio
async def test_partial_rerun_tag_inference_skips_middle(runner):
    session = Session(session_id="t", phase="idle")
    for sid in ["tag_inference","case_match","llm_supplement","self_analysis","competitor_analysis","summary"]:
        session.artifacts[sid] = Artifact(skill_id=sid, type="markdown", title=sid, content="x", version=1, status="done")
    completed: list[str] = []
    async for ev in runner.run_partial(session, ["tag_inference"], data={}, deepseek=None):
        if ev.type == "artifact_completed":
            completed.append(ev.skill_id)
    assert set(completed) == {"tag_inference", "summary"}
    assert session.artifacts["case_match"].version == 1
```

- [ ] **Step 3: Run tests, expect FAIL**

Run: `pytest tests/test_orchestrator_full_run.py tests/test_orchestrator_partial_run.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement orchestrator.py**

```python
from __future__ import annotations
from typing import Any, AsyncIterator
from app.skills.base import SkillContext, SkillEvent
from app.skills.registry import SkillRegistry
from app.models import Session

DAG_SKILLS = ["tag_inference", "case_match", "llm_supplement",
              "self_analysis", "competitor_analysis", "summary"]

class SkillRunner:
    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def _ctx(self, session: Session, data: dict, deepseek: Any, hint: str | None) -> SkillContext:
        return SkillContext(session=session, data=data, deepseek=deepseek, hint=hint)

    async def run_all(
        self, session: Session, data: dict, deepseek: Any, hint: str | None = None,
    ) -> AsyncIterator[SkillEvent]:
        session.phase = "running"
        order = self.registry.topological_sort(DAG_SKILLS)
        ctx = self._ctx(session, data, deepseek, hint)
        for sid in order:
            async for ev in self.registry.get(sid).run(ctx):
                yield ev
        session.phase = "idle"

    async def run_partial(
        self, session: Session, seed: list[str], data: dict, deepseek: Any, hint: str | None = None,
    ) -> AsyncIterator[SkillEvent]:
        session.phase = "running"
        order = self.registry.compute_rerun_set(seed)
        ctx = self._ctx(session, data, deepseek, hint)
        for sid in order:
            async for ev in self.registry.get(sid).run(ctx):
                yield ev
        session.phase = "idle"
```

- [ ] **Step 5: Run tests, expect pass**

Run: `pytest tests/test_orchestrator_full_run.py tests/test_orchestrator_partial_run.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/services/orchestrator.py tests/test_orchestrator_full_run.py tests/test_orchestrator_partial_run.py
git commit -m "feat(services): add SkillRunner with full_run and partial_run"
```

---

## Task 15: API layer + SSE bridge

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/events.py`
- Create: `app/api/chat.py`
- Create: `app/api/cases.py`
- Create: `app/main.py`

- [ ] **Step 1: app/api/__init__.py (empty)**

- [ ] **Step 2: app/api/events.py — per-session event queue**

```python
from __future__ import annotations
import asyncio
from collections import defaultdict

class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    def queue(self, session_id: str) -> asyncio.Queue:
        return self._queues[session_id]

    async def publish(self, session_id: str, event: dict) -> None:
        await self._queues[session_id].put(event)

bus = EventBus()
```

- [ ] **Step 3: app/api/chat.py**

```python
from __future__ import annotations
import json
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.config import settings
from app.services.session_store import session_store
from app.services.data_loader import load_all
from app.services.deepseek_client import DeepSeekClient
from app.services.orchestrator import SkillRunner
from app.skills import autoload
from app.models import Message, RequirementSummary
from app.api.events import bus

router = APIRouter()
registry = autoload()
runner = SkillRunner(registry)
DATA = load_all()
DEEPSEEK = DeepSeekClient(settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model)

class ChatIn(BaseModel):
    session_id: str
    message: str

@router.post("/api/chat")
async def chat(payload: ChatIn):
    session = session_store.get_or_create(payload.session_id)
    session.messages.append(Message(role="user", content=payload.message))
    asyncio.create_task(_handle(payload.session_id, payload.message))
    return {"ok": True, "stream_url": f"/api/stream/{payload.session_id}"}

async def _handle(session_id: str, user_message: str) -> None:
    session = session_store.get_or_create(session_id)

    async def emit(ev: dict):
        await bus.publish(session_id, ev)

    try:
        if session.phase == "socratic":
            async for ev in registry.get("socratic").run(
                _ctx(session, hint=None)
            ):
                await emit(_ev_to_dict(ev))
            if session.phase == "ready":
                await emit({"type": "phase_change", "phase": "ready"})
            await emit({"type": "run_completed"})
            return

        if session.phase == "ready":
            confirm = user_message.strip().lower()
            negative = {"no", "不", "不对", "修改", "改"}
            if any(n in confirm for n in negative):
                session.phase = "socratic"
                await emit({"type": "phase_change", "phase": "socratic"})
                await emit({"type": "chat_message", "role": "assistant",
                            "content": "好的，请补充你想调整的需求方向。"})
                await emit({"type": "run_completed"})
                return
            await emit({"type": "phase_change", "phase": "running"})
            async for ev in runner.run_all(session, DATA, DEEPSEEK):
                await emit(_ev_to_dict(ev))
            await emit({"type": "phase_change", "phase": "idle"})
            await emit({"type": "run_completed"})
            return

        if session.phase == "idle":
            decision = None
            async for ev in registry.get("dispatcher").run(_ctx(session, hint=None)):
                if ev.type == "chat_message" and ev.payload:
                    decision = ev.payload
            if not decision:
                await emit({"type": "error", "message": "dispatcher returned no decision"})
                await emit({"type": "run_completed"})
                return
            await _apply_decision(session, decision, emit)
            await emit({"type": "run_completed"})
            return
    except Exception as exc:
        await emit({"type": "error", "message": str(exc)})
        await emit({"type": "run_completed"})

async def _apply_decision(session, decision, emit) -> None:
    action = decision["action"]
    if action == "chat":
        session.messages.append(Message(role="assistant", content=decision["reply"]))
        await emit({"type": "chat_message", "role": "assistant", "content": decision["reply"]})
        return
    if action == "revise_requirement":
        patch = decision.get("patch", {})
        if session.requirement is None:
            session.requirement = RequirementSummary()
        for k, v in patch.items():
            if hasattr(session.requirement, k):
                setattr(session.requirement, k, v)
        session.phase = "ready"
        await emit({"type": "phase_change", "phase": "ready"})
        await emit({"type": "chat_message", "role": "assistant",
                    "content": "我已经更新了需求摘要，请确认后继续。"})
        return
    if action == "rerun":
        skills = decision.get("skills", [])
        hint = decision.get("hint")
        if not skills:
            await emit({"type": "chat_message", "role": "assistant",
                        "content": "没有识别出要刷新的章节，请再描述一下。"})
            return
        await emit({"type": "phase_change", "phase": "running"})
        async for ev in runner.run_partial(session, skills, DATA, DEEPSEEK, hint=hint):
            await emit(_ev_to_dict(ev))
        await emit({"type": "phase_change", "phase": "idle"})

def _ctx(session, hint):
    from app.skills.base import SkillContext
    return SkillContext(session=session, data=DATA, deepseek=DEEPSEEK, hint=hint)

def _ev_to_dict(ev) -> dict:
    return ev.model_dump(exclude_none=True)

@router.get("/api/stream/{session_id}")
async def stream(session_id: str):
    queue = bus.queue(session_id)

    async def event_gen():
        while True:
            ev = await queue.get()
            yield {"event": ev.get("type", "message"), "data": json.dumps(ev, ensure_ascii=False)}
            if ev.get("type") == "run_completed":
                continue

    return EventSourceResponse(event_gen())
```

- [ ] **Step 4: app/api/cases.py**

```python
from fastapi import APIRouter, HTTPException
from app.services.data_loader import load_all

router = APIRouter()
_CASES = {c["id"]: c for c in load_all()["cases"]}

@router.get("/api/cases/{case_id}")
def get_case(case_id: str):
    if case_id not in _CASES:
        raise HTTPException(404, "not found")
    return _CASES[case_id]
```

- [ ] **Step 5: app/main.py**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.chat import router as chat_router
from app.api.cases import router as cases_router
from app.config import settings
import os

app = FastAPI(title="Operator Package Design Assistant")
app.include_router(chat_router)
app.include_router(cases_router)
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

@app.get("/")
def root():
    return FileResponse(os.path.join(settings.static_dir, "index.html"))
```

- [ ] **Step 6: Quick smoke test**

Run: `python -c "from app.main import app; print(len(app.routes))"`
Expected: prints a number > 0.

- [ ] **Step 7: Commit**

```bash
git add app/api app/main.py
git commit -m "feat(api): add chat/cases routes, SSE bridge, FastAPI entry"
```

---

## Task 16: Frontend single page

**Files:**
- Create: `static/index.html`
- Create: `static/app.js`
- Create: `static/style.css`

- [ ] **Step 1: static/style.css**

```css
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f6f7f9; }
.app { display: flex; height: 100vh; }
.chat-pane { flex: 1.2; display: flex; flex-direction: column; border-right: 1px solid #e5e7eb; background: #fff; }
.side-pane { flex: 1; background: #fafafa; display: flex; flex-direction: column; }
.side-pane.collapsed { flex: 0 0 0; overflow: hidden; }
.messages { flex: 1; overflow-y: auto; padding: 16px; }
.message { margin-bottom: 12px; max-width: 80%; padding: 10px 14px; border-radius: 12px; line-height: 1.55; white-space: pre-wrap; }
.message.user { background: #2563eb; color: #fff; margin-left: auto; }
.message.assistant { background: #f1f5f9; color: #111; }
.message .view-link { margin-top: 6px; font-size: 12px; color: #2563eb; cursor: pointer; }
.composer { display: flex; padding: 12px; border-top: 1px solid #e5e7eb; }
.composer input { flex: 1; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; }
.composer button { margin-left: 8px; padding: 10px 18px; background: #2563eb; color: #fff; border: 0; border-radius: 8px; cursor: pointer; }
.composer button:disabled { background: #93c5fd; cursor: not-allowed; }
.tabs { display: flex; flex-wrap: wrap; gap: 4px; padding: 8px; border-bottom: 1px solid #e5e7eb; background: #fff; }
.tab { padding: 6px 10px; font-size: 12px; border-radius: 6px; cursor: pointer; background: #f3f4f6; }
.tab.active { background: #2563eb; color: #fff; }
.tab .ver { opacity: 0.7; margin-left: 4px; }
.artifact { flex: 1; overflow-y: auto; padding: 16px; }
.tag-pill { display: inline-block; padding: 4px 10px; background: #eef2ff; border-radius: 999px; margin: 4px 6px 4px 0; font-size: 12px; }
.case-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.case-card { background: #fff; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer; }
.case-card h4 { margin: 0 0 4px; font-size: 14px; }
.case-card .meta { font-size: 11px; color: #6b7280; margin-bottom: 6px; }
.case-card .score { font-size: 11px; color: #2563eb; }
.toggle { padding: 4px 10px; font-size: 12px; cursor: pointer; }
.phase-pill { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #fef3c7; color: #92400e; margin-left: 8px; }
.markdown h1, .markdown h2, .markdown h3 { margin-top: 16px; }
```

- [ ] **Step 2: static/index.html**

```html
<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8" />
  <title>运营商套餐设计助手</title>
  <link rel="stylesheet" href="/static/style.css" />
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
  <div class="app">
    <section class="chat-pane">
      <div style="padding:12px;border-bottom:1px solid #e5e7eb;font-weight:600;">
        套餐设计助手
        <span id="phase-pill" class="phase-pill">socratic</span>
        <span class="toggle" id="toggle-side" style="float:right;">折叠右栏</span>
      </div>
      <div class="messages" id="messages"></div>
      <div class="composer">
        <input id="input" placeholder="告诉我你的套餐设计想法…" />
        <button id="send">发送</button>
      </div>
    </section>
    <aside class="side-pane" id="side-pane">
      <div class="tabs" id="tabs"></div>
      <div class="artifact" id="artifact"></div>
    </aside>
  </div>
  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: static/app.js**

```javascript
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
```

- [ ] **Step 4: Commit**

```bash
git add static
git commit -m "feat(frontend): add chat + collapsible artifact pane SPA"
```

---

## Task 17: Integration smoke test

**Files:**
- Create: `tests/test_api_integration.py`

- [ ] **Step 1: Write test using mocked DeepSeek**

`tests/test_api_integration.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

@pytest.fixture
def client():
    with patch("app.services.deepseek_client.DeepSeekClient.chat_stream") as stream, \
         patch("app.services.deepseek_client.DeepSeekClient.chat") as chat:
        async def fake_stream(messages, temperature=0.7):
            yield '{"done": true, "summary": {"target_audience":"球迷","scenario":"世界杯","special_needs":["流量包"],"notes":""}}'
        stream.side_effect = fake_stream
        chat.return_value = '{"action":"chat","reply":"OK"}'
        from app.main import app
        yield TestClient(app)

def test_chat_endpoint_returns_stream_url(client):
    r = client.post("/api/chat", json={"session_id": "s1", "message": "帮我设计一个世界杯套餐"})
    assert r.status_code == 200
    assert r.json()["stream_url"] == "/api/stream/s1"

def test_cases_endpoint_known(client):
    r = client.get("/api/cases/case_001")
    assert r.status_code == 200
    assert r.json()["id"] == "case_001"

def test_cases_endpoint_missing(client):
    r = client.get("/api/cases/nope")
    assert r.status_code == 404
```

- [ ] **Step 2: Run, expect pass**

Run: `pytest tests/test_api_integration.py -v`
Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_integration.py
git commit -m "test(api): add basic integration tests with mocked DeepSeek"
```

---

## Task 18: README and run instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

```markdown
# 运营商套餐设计辅助智能体（原型）

## 启动

1. 安装依赖: `pip install -e ".[dev]"`
2. 复制 `.env.example` 为 `.env` 并填入 `DEEPSEEK_API_KEY`
3. 运行: `uvicorn app.main:app --reload --port 8000`
4. 浏览器打开 http://localhost:8000

## 测试

`pytest -v`

## 目录速览

- `app/skills/*` — 每个文件夹一个 Skill，含 yaml + prompt + handler
- `app/services/orchestrator.py` — Full Run 与 Partial Run
- `app/data/*.json` — 预置标签 / 案例 / 运营商档案
- `static/` — 单页前端
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with run/test instructions"
```

---

## Task 19: Manual end-to-end verification

This task is exploratory; no automated assertions.

- [ ] **Step 1: Start server**

Run: `uvicorn app.main:app --reload --port 8000`

- [ ] **Step 2: In browser, run scenarios**

打开 http://localhost:8000，依次验证：

1. 输入"帮我设计一个世界杯套餐"——出现澄清问题
2. 回答 1-2 轮直到出现"需求摘要"
3. 回复"确认"——观察 6 个 artifact 依次产出（标签 → 案例 → LLM 补充 → 看自己 → 看对手 → Summary）
4. 在 idle 阶段说"看对手部分再补充 5G 维度"——只有 competitor_analysis 和 summary 重新生成（其它 tab 保留 v1）
5. 说"换设计标签试试 TryAndBuy"——只有 tag_inference 和 summary 刷新；case_match 等保留旧版本
6. 折叠/展开右栏；点击聊天里的"查看 X"链接切换 tab；点击案例卡片打开详情

- [ ] **Step 3: 记录任何观察到的问题**

如有问题，回到对应 Task 修复后再次验证。

---

## Self-Review

Coverage check vs spec:

- §3 技术栈 — Task 1 ✓
- §4.1 目录结构 — Tasks 1-15 ✓
- §4.2 前端布局 — Task 16 ✓
- §5.1 Skill — Tasks 4, 8-12 ✓
- §5.2 Artifact — Task 2 + 各 skill handler ✓
- §6 状态机 — Tasks 2 (model), 15 (chat.py 控制 phase 转换) ✓
- §7 DAG — Tasks 5 (registry), 14 (runner) ✓
- §8.1 Full Run — Task 14 ✓
- §8.2 Incremental Run — Task 14 + Task 15 _apply_decision ✓
- §9 传染设计 — Task 5 compute_rerun_set + 各 skill.yaml 的 propagate_downstream ✓
- §10 Dispatcher — Task 12 ✓
- §11 数据预置 — Task 7 ✓
- §12 案例匹配算法 — Task 10 ✓
- §13 API — Task 15 ✓
- §14 错误处理 — Task 15 try/except + dispatcher fallback ✓
- §15 测试 — Tasks 2, 3, 5, 6, 7, 10, 12, 14, 17 ✓






