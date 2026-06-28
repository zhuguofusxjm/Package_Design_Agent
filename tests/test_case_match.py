import pytest
from app.skills.case_match.handler import jaccard_match

CASES = [
    {"id":"c1","name":"A","tag_ids":["t1","t2"],"summary":"...","operator":"O","region":"R"},
    {"id":"c2","name":"B","tag_ids":["t2","t3"],"summary":"...","operator":"O","region":"R"},
    {"id":"c3","name":"C","tag_ids":["t4"],"summary":"...","operator":"O","region":"R"},
]

def test_jaccard_returns_only_intersecting():
    out = jaccard_match({"t1","t2"}, CASES, top_k=10)
    ids = [c["case_id"] for c in out]
    assert "c1" in ids and "c2" in ids and "c3" not in ids

def test_jaccard_score_ordering():
    out = jaccard_match({"t1","t2"}, CASES, top_k=10)
    assert out[0]["case_id"] == "c1"

def test_top_k_caps_results():
    out = jaccard_match({"t1","t2"}, CASES, top_k=1)
    assert len(out) == 1
