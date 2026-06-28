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
