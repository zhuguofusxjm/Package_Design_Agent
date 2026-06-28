import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

@pytest.fixture
def client():
    with patch("app.services.deepseek_client.DeepSeekClient.chat_stream") as stream, \
         patch("app.services.deepseek_client.DeepSeekClient.chat") as chat:
        async def fake_stream(messages, temperature=0.7):
            yield '{"done": true, "summary": {"target_audience":"球迷","scenario":"世界杯","special_needs":["流量包"],"notes":""}}'
        stream.side_effect = fake_stream
        chat.return_value = '{"action":"chat","reply":"OK"}'
        from app.main import app
        yield TestClient(app)

def test_chat_endpoint_returns_stream_url(client):
    r = client.post("/api/chat", json={"session_id": "s1", "message": "帮我设计一个世界杯套餐"})
    assert r.status_code == 200
    assert r.json()["stream_url"] == "/api/stream/s1"

def test_cases_endpoint_known(client):
    r = client.get("/api/cases/case_001")
    assert r.status_code == 200
    assert r.json()["id"] == "case_001"

def test_cases_endpoint_missing(client):
    r = client.get("/api/cases/nope")
    assert r.status_code == 404
