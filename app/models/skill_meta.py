from typing import Literal
from pydantic import BaseModel, Field

class SkillMeta(BaseModel):
    id: str
    name: str
    description: str = ""
    artifact_type: Literal["markdown", "tag_list", "case_cards"] = "markdown"
    artifact_title: str = ""
    depends_on: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    uses_llm: bool = True
    streaming: bool = True
    propagate_downstream: bool = False
