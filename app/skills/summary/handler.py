from __future__ import annotations
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.skills.prompt_utils import render
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
        prompt = render(
            tpl,
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
