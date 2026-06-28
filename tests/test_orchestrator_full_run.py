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
