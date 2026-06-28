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
