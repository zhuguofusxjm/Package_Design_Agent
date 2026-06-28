import pytest
from app.skills.registry import SkillRegistry
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta

class DummySkill(Skill):
    async def run(self, ctx):
        yield SkillEvent(type="artifact_completed", skill_id=self.meta.id)

def test_register_and_topo_sort():
    reg = SkillRegistry()
    reg.register(DummySkill(SkillMeta(id="a", name="A", depends_on=[])))
    reg.register(DummySkill(SkillMeta(id="b", name="B", depends_on=["a"])))
    reg.register(DummySkill(SkillMeta(id="c", name="C", depends_on=["a"])))
    order = reg.topological_sort(["a", "b", "c"])
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")

def test_downstream_of():
    reg = SkillRegistry()
    reg.register(DummySkill(SkillMeta(id="a", name="A")))
    reg.register(DummySkill(SkillMeta(id="b", name="B", depends_on=["a"])))
    reg.register(DummySkill(SkillMeta(id="c", name="C", depends_on=["b"])))
    assert set(reg.downstream_of("a")) == {"b"}
    assert set(reg.downstream_of("b")) == {"c"}

def test_cycle_raises():
    reg = SkillRegistry()
    reg.register(DummySkill(SkillMeta(id="a", name="A", depends_on=["b"])))
    reg.register(DummySkill(SkillMeta(id="b", name="B", depends_on=["a"])))
    with pytest.raises(ValueError):
        reg.topological_sort(["a", "b"])
