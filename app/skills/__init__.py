from __future__ import annotations
import importlib
import os
from app.skills.registry import registry, SkillRegistry

SKILL_FOLDERS = [
    "socratic", "tag_inference", "case_match",
    "llm_supplement", "self_analysis", "competitor_analysis",
    "summary", "dispatcher",
]

def autoload() -> SkillRegistry:
    for folder in SKILL_FOLDERS:
        mod = importlib.import_module(f"app.skills.{folder}.handler")
        registry.register(mod.load())
    return registry
