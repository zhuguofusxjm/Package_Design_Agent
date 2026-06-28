from datetime import datetime
from app.models import Session, Message, Artifact, RequirementSummary

def test_session_initial_state():
    s = Session(session_id="abc")
    assert s.phase == "socratic"
    assert s.socratic_round == 0
    assert s.messages == []
    assert s.artifacts == {}
    assert s.artifact_versions == {}
    assert s.requirement is None

def test_artifact_bump_version():
    a = Artifact(skill_id="x", type="markdown", title="X", content="", version=1, status="done")
    assert a.version == 1

def test_requirement_summary_fields():
    r = RequirementSummary(target_audience="球迷", scenario="世界杯", special_needs=["流量包"])
    assert r.target_audience == "球迷"
