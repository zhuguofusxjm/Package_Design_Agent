from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Literal
from pydantic import BaseModel, Field
from app.models import Artifact, Session, SkillMeta

class SkillEvent(BaseModel):
    type: Literal[
        "artifact_started", "artifact_delta", "artifact_completed",
        "artifact_error", "chat_message",
    ]
    skill_id: str | None = None
    title: str | None = None
    version: int | None = None
    chunk: str | None = None
    payload: Any = None
    message: str | None = None
    role: Literal["user", "assistant"] | None = None
    content: str | None = None

class SkillContext(BaseModel):
    session: Session
    data: dict[str, Any] = Field(default_factory=dict)
    deepseek: Any = None
    hint: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    def upstream_artifact(self, skill_id: str) -> Artifact | None:
        return self.session.artifacts.get(skill_id)

class Skill(ABC):
    meta: SkillMeta

    def __init__(self, meta: SkillMeta) -> None:
        self.meta = meta

    @abstractmethod
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        ...
        if False:
            yield  # pragma: no cover
