from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    meta: dict[str, Any] = Field(default_factory=dict)

class RequirementSummary(BaseModel):
    target_audience: str = ""
    scenario: str = ""
    special_needs: list[str] = Field(default_factory=list)
    notes: str = ""

class Artifact(BaseModel):
    skill_id: str
    type: Literal["markdown", "tag_list", "case_cards"]
    title: str
    content: Any = ""
    version: int = 1
    status: Literal["pending", "streaming", "done", "error"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(BaseModel):
    session_id: str
    messages: list[Message] = Field(default_factory=list)
    requirement: RequirementSummary | None = None
    artifacts: dict[str, Artifact] = Field(default_factory=dict)
    artifact_versions: dict[str, list[Artifact]] = Field(default_factory=dict)
    phase: Literal["socratic", "ready", "running", "idle"] = "socratic"
    socratic_round: int = 0
