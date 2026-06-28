from __future__ import annotations
import json
import os
from app.config import settings

def _read(name: str):
    with open(os.path.join(settings.data_dir, name), "r", encoding="utf-8") as f:
        return json.load(f)

def load_all() -> dict:
    return {
        "tags": _read("tags.json"),
        "cases": _read("cases.json"),
        "operator": _read("operator_profile.json"),
    }
