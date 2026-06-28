from app.services.data_loader import load_all

def test_load_all_returns_tags_cases_operator():
    data = load_all()
    assert "tags" in data and "cases" in data and "operator" in data
    assert len(data["tags"]) >= 3
    assert len(data["cases"]) >= 3
    assert data["operator"]["self"]["name"]

def test_tags_indexable_by_id():
    data = load_all()
    by_id = {t["id"]: t for t in data["tags"]}
    assert "try_and_buy" in by_id
