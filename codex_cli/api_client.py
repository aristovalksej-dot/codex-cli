"""API client for codex.sale (OpenAI-compatible)."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from codex_cli.config import Config


class APIError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"API error {status_code}: {message}")


def _sanitize(obj: Any) -> Any:
    """Remove surrogate characters that break UTF-8 encoding."""
    if isinstance(obj, str):
        return obj.encode("utf-8", errors="replace").decode("utf-8")
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


class APIClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(120.0, connect=15.0),
        )

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        payload = _sanitize(payload)
        response = await self._client.post("/chat/completions", json=payload)
        if response.status_code != 200:
            raise APIError(response.status_code, response.text)

        return response.json()

    async def chat_completion_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise APIError(resp.status_code, body.decode())

            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        yield chunk
                    except json.JSONDecodeError:
                        continue

    async def list_models(self) -> list[dict[str, Any]]:
        response = await self._client.get("/models")
        if response.status_code != 200:
            raise APIError(response.status_code, response.text)
        data = response.json()
        return data.get("data", [])

    async def close(self) -> None:
        await self._client.aclose()

    def extract_message(self, response: dict[str, Any]) -> dict[str, Any]:
        choices = response.get("choices", [])
        if not choices:
            return {"role": "assistant", "content": "No response from model."}
        return choices[0].get("message", {"role": "assistant", "content": ""})

    def extract_tool_calls(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        return message.get("tool_calls", [])

    def has_tool_calls(self, message: dict[str, Any]) -> bool:
        return bool(message.get("tool_calls"))
