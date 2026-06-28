from app.skills.dispatcher.handler import parse_decision

def test_parse_chat():
    d = parse_decision('{"action":"chat","reply":"你好"}')
    assert d["action"] == "chat" and d["reply"] == "你好"

def test_parse_rerun():
    d = parse_decision('{"action":"rerun","skills":["competitor_analysis"],"hint":"加上 5G 维度"}')
    assert d["action"] == "rerun"
    assert d["skills"] == ["competitor_analysis"]
    assert d["hint"] == "加上 5G 维度"

def test_parse_handles_markdown_fence():
    d = parse_decision('```json\n{"action":"chat","reply":"hi"}\n```')
    assert d["action"] == "chat"

def test_parse_fallback_to_chat_on_invalid():
    d = parse_decision("just plain text reply not JSON")
    assert d["action"] == "chat"
    assert "just plain text" in d["reply"]

def test_parse_rejects_unknown_skill_id():
    d = parse_decision('{"action":"rerun","skills":["does_not_exist","summary"]}')
    assert d["action"] == "rerun"
    assert d["skills"] == ["summary"]
