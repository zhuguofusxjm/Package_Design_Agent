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
