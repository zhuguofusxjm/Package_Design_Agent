import pytest
from app.skills.registry import SkillRegistry
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta

class _S(Skill):
    async def run(self, ctx):
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id)

@pytest.fixture
def reg():
    r = SkillRegistry()
    r.register(_S(SkillMeta(id="tag_inference", name="T", depends_on=[], propagate_downstream=True)))
    r.register(_S(SkillMeta(id="case_match", name="C", depends_on=["tag_inference"], propagate_downstream=False)))
    r.register(_S(SkillMeta(id="llm_supplement", name="L", depends_on=["tag_inference"], propagate_downstream=False)))
    r.register(_S(SkillMeta(id="self_analysis", name="S", depends_on=["tag_inference"], propagate_downstream=False)))
    r.register(_S(SkillMeta(id="competitor_analysis", name="X", depends_on=["tag_inference"], propagate_downstream=False)))
    r.register(_S(SkillMeta(id="summary", name="SM",
                  depends_on=["case_match","llm_supplement","self_analysis","competitor_analysis"],
                  propagate_downstream=True)))
    return r

def test_rerun_tag_inference_only_adds_summary(reg):
    out = reg.compute_rerun_set(["tag_inference"])
    assert set(out) == {"tag_inference", "summary"}

def test_rerun_competitor_only_adds_summary(reg):
    out = reg.compute_rerun_set(["competitor_analysis"])
    assert set(out) == {"competitor_analysis", "summary"}

def test_rerun_summary_only_stays_summary(reg):
    out = reg.compute_rerun_set(["summary"])
    assert set(out) == {"summary"}

def test_rerun_returns_topological_order(reg):
    out = reg.compute_rerun_set(["competitor_analysis"])
    assert out.index("competitor_analysis") < out.index("summary")

def test_rerun_combination(reg):
    out = reg.compute_rerun_set(["tag_inference", "competitor_analysis"])
    assert set(out) == {"tag_inference", "competitor_analysis", "summary"}
