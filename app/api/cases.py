from fastapi import APIRouter, HTTPException
from app.services.data_loader import load_all

router = APIRouter()
_CASES = {c["id"]: c for c in load_all()["cases"]}

@router.get("/api/cases/{case_id}")
def get_case(case_id: str):
    if case_id not in _CASES:
        raise HTTPException(404, "not found")
    return _CASES[case_id]
