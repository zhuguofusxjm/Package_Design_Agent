import pytest
import respx
import httpx
from app.services.deepseek_client import DeepSeekClient

@pytest.mark.asyncio
@respx.mock
async def test_chat_stream_yields_chunks():
    body = (
        'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"好"}}]}\n\n'
        'data: [DONE]\n\n'
    )
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(200, text=body,
            headers={"content-type": "text/event-stream"})
    )
    client = DeepSeekClient(api_key="k", base_url="https://api.deepseek.com", model="m")
    chunks: list[str] = []
    async for c in client.chat_stream([{"role": "user", "content": "hi"}]):
        chunks.append(c)
    assert chunks == ["你", "好"]

@pytest.mark.asyncio
@respx.mock
async def test_chat_non_stream():
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices":[{"message":{"content":"hello world"}}]
        })
    )
    client = DeepSeekClient(api_key="k", base_url="https://api.deepseek.com", model="m")
    text = await client.chat([{"role": "user", "content": "hi"}])
    assert text == "hello world"
