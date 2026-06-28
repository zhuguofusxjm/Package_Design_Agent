from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.skills.prompt_utils import render
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
        prompt = render(
            tpl,
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
