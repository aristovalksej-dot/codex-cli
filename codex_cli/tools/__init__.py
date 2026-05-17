"""Tool registry — imports and exposes all available tools."""

from __future__ import annotations

from codex_cli.tools.base import Tool, ToolRegistry
from codex_cli.tools.code_tools import AnalyzeCodeTool, GenerateCodeTool
from codex_cli.tools.file_ops import (
    AppendFileTool,
    CreateDirectoryTool,
    DeleteFileTool,
    EditFileTool,
    ListDirectoryTool,
    ReadFileTool,
    TreeTool,
    WriteFileTool,
)
from codex_cli.tools.github_ops import (
    CloneRepoTool,
    GitCommandTool,
    GitHubRepoInfoTool,
    GitHubSearchTool,
)
from codex_cli.tools.search import FindFilesTool, GrepSearchTool
from codex_cli.tools.shell import ShellCommandTool
from codex_cli.tools.web import FetchWebpageTool, SearchWebTool


def create_registry() -> ToolRegistry:
    registry = ToolRegistry()
    tools: list[Tool] = [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        AppendFileTool(),
        DeleteFileTool(),
        CreateDirectoryTool(),
        ListDirectoryTool(),
        TreeTool(),
        ShellCommandTool(),
        FetchWebpageTool(),
        SearchWebTool(),
        CloneRepoTool(),
        GitCommandTool(),
        GitHubRepoInfoTool(),
        GitHubSearchTool(),
        GrepSearchTool(),
        FindFilesTool(),
        AnalyzeCodeTool(),
        GenerateCodeTool(),
    ]
    for tool in tools:
        registry.register(tool)
    return registry


__all__ = [
    "Tool",
    "ToolRegistry",
    "create_registry",
]
