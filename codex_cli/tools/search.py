"""File and code search tools."""

from __future__ import annotations

import asyncio
import fnmatch
import os
from pathlib import Path
from typing import Any

from codex_cli.tools.base import Tool

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", "dist", "build", ".next", ".nuxt", "target",
    ".cache", ".pytest_cache", ".mypy_cache",
}


class GrepSearchTool(Tool):
    name = "grep_search"
    description = (
        "Search for a pattern in files using regex or literal string matching. "
        "Similar to grep/ripgrep. Searches file contents recursively."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Search pattern (regex supported)",
            },
            "path": {
                "type": "string",
                "description": "Directory or file to search in (default: current dir)",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g. '*.py', '*.js'). Optional.",
            },
            "case_insensitive": {
                "type": "boolean",
                "description": "Case-insensitive search (default: false)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of matches to return (default: 50)",
            },
            "context_lines": {
                "type": "integer",
                "description": "Number of context lines before/after each match (default: 0)",
            },
        },
        "required": ["pattern"],
    }

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "",
        case_insensitive: bool = False,
        max_results: int = 50,
        context_lines: int = 0,
        **_: Any,
    ) -> str:
        search_path = Path(path).expanduser().resolve()
        if not search_path.exists():
            return f"Error: Path not found: {search_path}"

        rg_cmd = _build_rg_command(
            pattern, str(search_path), file_pattern, case_insensitive, max_results, context_lines
        )
        if rg_cmd:
            return await self._run_rg(rg_cmd)

        grep_cmd = _build_grep_command(
            pattern, str(search_path), file_pattern, case_insensitive, max_results, context_lines
        )
        return await self._run_grep(grep_cmd)

    async def _run_rg(self, cmd: str) -> str:
        return await _run_search_cmd(cmd)

    async def _run_grep(self, cmd: str) -> str:
        return await _run_search_cmd(cmd)


class FindFilesTool(Tool):
    name = "find_files"
    description = (
        "Find files by name pattern, extension, or size. "
        "Searches recursively through directories."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": (
                    "Filename pattern with wildcards "
                    "(e.g. '*.py', 'test_*', 'Dockerfile*')"
                ),
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: current dir)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 50)",
            },
        },
        "required": ["pattern"],
    }

    async def execute(
        self, pattern: str, path: str = ".", max_results: int = 50, **_: Any
    ) -> str:
        search_path = Path(path).expanduser().resolve()
        if not search_path.exists():
            return f"Error: Path not found: {search_path}"

        results: list[str] = []
        try:
            for root, dirs, files in os.walk(search_path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for f in files:
                    if fnmatch.fnmatch(f, pattern) or fnmatch.fnmatch(f.lower(), pattern.lower()):
                        full_path = Path(root) / f
                        try:
                            size = full_path.stat().st_size
                            if size < 1024:
                                size_str = f"{size} B"
                            elif size < 1024 * 1024:
                                size_str = f"{size / 1024:.1f} KB"
                            else:
                                size_str = f"{size / (1024 * 1024):.1f} MB"
                            results.append(f"  {full_path}  ({size_str})")
                        except OSError:
                            results.append(f"  {full_path}")
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break
        except PermissionError:
            return f"Error: Permission denied accessing {search_path}"

        if not results:
            return f"No files matching '{pattern}' found in {search_path}"
        header = f"Files matching '{pattern}' in {search_path} ({len(results)} found):"
        return header + "\n" + "\n".join(results)


def _build_rg_command(
    pattern: str,
    path: str,
    file_pattern: str,
    case_insensitive: bool,
    max_results: int,
    context_lines: int,
) -> str:
    parts = ["rg", "--no-heading", "--line-number", "--color=never"]
    if case_insensitive:
        parts.append("-i")
    if context_lines > 0:
        parts.append(f"-C{context_lines}")
    parts.append(f"-m{max_results}")
    if file_pattern:
        parts.append(f"--glob='{file_pattern}'")
    for skip in SKIP_DIRS:
        parts.append(f"--glob='!{skip}/'")
    parts.append(f"'{pattern}'")
    parts.append(f"'{path}'")
    return " ".join(parts)


def _build_grep_command(
    pattern: str,
    path: str,
    file_pattern: str,
    case_insensitive: bool,
    max_results: int,
    context_lines: int,
) -> str:
    parts = ["grep", "-rn", "--color=never"]
    if case_insensitive:
        parts.append("-i")
    if context_lines > 0:
        parts.append(f"-C{context_lines}")
    if file_pattern:
        parts.append(f"--include='{file_pattern}'")
    for skip in SKIP_DIRS:
        parts.append(f"--exclude-dir='{skip}'")
    parts.append(f"'{pattern}'")
    parts.append(f"'{path}'")
    parts.append(f"| head -n {max_results * (1 + 2 * context_lines + 1)}")
    return " ".join(parts)


async def _run_search_cmd(cmd: str) -> str:
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError:
        return "Error: Search timed out after 30s"
    except Exception as e:
        return f"Error: {e}"

    output = stdout.decode("utf-8", errors="replace").strip()
    if not output:
        return "No matches found."
    if len(output) > 60000:
        output = output[:30000] + "\n\n... [truncated] ...\n\n" + output[-30000:]
    return output
