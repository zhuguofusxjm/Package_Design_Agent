import pytest
from app.services.session_store import SessionStore
from app.models import Session

def test_get_or_create_creates_new():
    store = SessionStore()
    s = store.get_or_create("sid-1")
    assert s.session_id == "sid-1"
    assert s.phase == "socratic"

def test_get_or_create_returns_existing():
    store = SessionStore()
    s1 = store.get_or_create("sid-2")
    s1.socratic_round = 3
    s2 = store.get_or_create("sid-2")
    assert s2.socratic_round == 3

def test_get_missing_returns_none():
    store = SessionStore()
    assert store.get("nope") is None
