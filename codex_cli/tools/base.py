"""Base tool class and tool registry."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def parse_args(self, arguments_str: str) -> dict[str, Any]:
        try:
            return json.loads(arguments_str)
        except json.JSONDecodeError:
            return {}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: str) -> str:
        tool = self.get(name)
        if tool is None:
            return f"Error: Unknown tool '{name}'"
        try:
            kwargs = tool.parse_args(arguments)
            return await tool.execute(**kwargs)
        except Exception as e:
            return f"Error executing {name}: {type(e).__name__}: {e}"
