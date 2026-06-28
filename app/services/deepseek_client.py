from __future__ import annotations
import json
from typing import Any, AsyncIterator
import httpx

class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 60.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def chat(self, messages: list[dict[str, Any]], temperature: float = 0.7) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages,
                   "temperature": temperature, "stream": False}
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            r = await cli.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def chat_stream(
        self, messages: list[dict[str, Any]], temperature: float = 0.7
    ) -> AsyncIterator[str]:
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages,
                   "temperature": temperature, "stream": True}
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            async with cli.stream("POST", url, headers=self._headers(), json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
