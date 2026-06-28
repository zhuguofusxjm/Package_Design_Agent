from __future__ import annotations
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.skills.prompt_utils import render
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
        prompt = render(
            tpl,
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
