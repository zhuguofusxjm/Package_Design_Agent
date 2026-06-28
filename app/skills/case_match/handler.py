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
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id, version=version, payload={"content": {"cases": matched}})

def load() -> CaseMatchSkill:
    with open(os.path.join(os.path.dirname(__file__), "skill.yaml"), "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return CaseMatchSkill(meta)
