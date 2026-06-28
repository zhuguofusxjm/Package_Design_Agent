from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.skills.prompt_utils import render
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
        prompt = render(
            tpl,
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
