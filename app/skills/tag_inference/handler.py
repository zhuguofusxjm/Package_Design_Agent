from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.skills.prompt_utils import render
from app.models import SkillMeta, Artifact

class TagInferenceSkill(Skill):
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        tags = ctx.data["tags"]
        req = ctx.session.requirement
        catalog = "\n".join(f'- {t["id"]} | {t["name"]} | {t["description"]}' for t in tags)
        with open(os.path.join(os.path.dirname(__file__), "prompt.md"), "r", encoding="utf-8") as f:
            template = f.read()
        prompt = render(
            template,
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
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version, payload={"content": content})

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
