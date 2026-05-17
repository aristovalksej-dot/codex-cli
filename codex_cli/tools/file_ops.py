"""File operation tools — read, write, edit, delete, list, tree."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from codex_cli.tools.base import Tool


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file. Returns the file text with line numbers."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to the file"},
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (1-indexed). Optional.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read. Optional.",
            },
        },
        "required": ["path"],
    }

    async def execute(self, path: str, offset: int = 1, limit: int = 0, **_: Any) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: File not found: {p}"
        if not p.is_file():
            return f"Error: Not a file: {p}"
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except PermissionError:
            return f"Error: Permission denied: {p}"
        lines = text.splitlines()
        start = max(0, offset - 1)
        end = start + limit if limit > 0 else len(lines)
        selected = lines[start:end]
        numbered = [f"{i + start + 1:>6}\t{line}" for i, line in enumerate(selected)]
        header = f"File: {p} ({len(lines)} lines total)"
        return header + "\n" + "\n".join(numbered)


class WriteFileTool(Tool):
    name = "write_file"
    description = (
        "Write content to a file. Creates it if missing, overwrites if exists."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to write"},
            "content": {"type": "string", "description": "Content to write to the file"},
        },
        "required": ["path", "content"],
    }

    async def execute(self, path: str, content: str, **_: Any) -> str:
        p = Path(path).expanduser().resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            return f"Successfully wrote {len(content)} bytes ({lines} lines) to {p}"
        except PermissionError:
            return f"Error: Permission denied: {p}"
        except Exception as e:
            return f"Error writing file: {e}"


class EditFileTool(Tool):
    name = "edit_file"
    description = (
        "Edit a file by replacing an exact string match with new text. "
        "The old_string must be unique in the file."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to edit"},
            "old_string": {"type": "string", "description": "Exact text to find and replace"},
            "new_string": {"type": "string", "description": "Replacement text"},
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences (default false)",
            },
        },
        "required": ["path", "old_string", "new_string"],
    }

    async def execute(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        **_: Any,
    ) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: File not found: {p}"
        text = p.read_text(encoding="utf-8", errors="replace")
        count = text.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {p}"
        if count > 1 and not replace_all:
            return (
                f"Error: old_string found {count} times in {p}. "
                "Use replace_all=true or provide more context to make it unique."
            )
        if replace_all:
            new_text = text.replace(old_string, new_string)
        else:
            new_text = text.replace(old_string, new_string, 1)
        p.write_text(new_text, encoding="utf-8")
        return f"Successfully edited {p} ({count} replacement{'s' if count > 1 else ''} made)"


class AppendFileTool(Tool):
    name = "append_file"
    description = "Append content to the end of a file."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
            "content": {"type": "string", "description": "Content to append"},
        },
        "required": ["path", "content"],
    }

    async def execute(self, path: str, content: str, **_: Any) -> str:
        p = Path(path).expanduser().resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully appended {len(content)} bytes to {p}"
        except PermissionError:
            return f"Error: Permission denied: {p}"


class DeleteFileTool(Tool):
    name = "delete_file"
    description = "Delete a file or directory."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to delete"},
            "recursive": {
                "type": "boolean",
                "description": "Recursively delete directories (default false)",
            },
        },
        "required": ["path"],
    }

    async def execute(self, path: str, recursive: bool = False, **_: Any) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: Path not found: {p}"
        try:
            if p.is_file() or p.is_symlink():
                p.unlink()
                return f"Deleted file: {p}"
            elif p.is_dir():
                if recursive:
                    shutil.rmtree(p)
                    return f"Deleted directory (recursive): {p}"
                else:
                    p.rmdir()
                    return f"Deleted empty directory: {p}"
        except PermissionError:
            return f"Error: Permission denied: {p}"
        except OSError as e:
            return f"Error deleting: {e}"
        return f"Error: Unknown path type: {p}"


class CreateDirectoryTool(Tool):
    name = "create_directory"
    description = "Create a directory (and parent directories if needed)."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the directory to create"},
        },
        "required": ["path"],
    }

    async def execute(self, path: str, **_: Any) -> str:
        p = Path(path).expanduser().resolve()
        try:
            p.mkdir(parents=True, exist_ok=True)
            return f"Directory created: {p}"
        except PermissionError:
            return f"Error: Permission denied: {p}"


class ListDirectoryTool(Tool):
    name = "list_directory"
    description = "List files and directories in a given path."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the directory (default: current directory)",
            },
            "show_hidden": {
                "type": "boolean",
                "description": "Show hidden files (default false)",
            },
        },
        "required": [],
    }

    async def execute(self, path: str = ".", show_hidden: bool = False, **_: Any) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: Directory not found: {p}"
        if not p.is_dir():
            return f"Error: Not a directory: {p}"
        entries: list[str] = []
        try:
            for item in sorted(p.iterdir()):
                name = item.name
                if not show_hidden and name.startswith("."):
                    continue
                suffix = "/" if item.is_dir() else ""
                size = ""
                if item.is_file():
                    sz = item.stat().st_size
                    if sz < 1024:
                        size = f" ({sz} B)"
                    elif sz < 1024 * 1024:
                        size = f" ({sz / 1024:.1f} KB)"
                    else:
                        size = f" ({sz / (1024 * 1024):.1f} MB)"
                entries.append(f"  {name}{suffix}{size}")
        except PermissionError:
            return f"Error: Permission denied: {p}"
        header = f"Directory: {p} ({len(entries)} items)"
        return header + "\n" + "\n".join(entries) if entries else header + "\n  (empty)"


class TreeTool(Tool):
    name = "tree"
    description = "Show directory tree structure recursively."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Root path for the tree (default: current directory)",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth to traverse (default: 3)",
            },
            "show_hidden": {
                "type": "boolean",
                "description": "Show hidden files (default false)",
            },
        },
        "required": [],
    }

    async def execute(
        self, path: str = ".", max_depth: int = 3, show_hidden: bool = False, **_: Any
    ) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: Path not found: {p}"

        lines: list[str] = [str(p)]
        self._walk(p, "", 0, max_depth, show_hidden, lines)
        if len(lines) > 500:
            lines = lines[:500]
            lines.append("... (truncated, showing 500 of many entries)")
        return "\n".join(lines)

    def _walk(
        self,
        directory: Path,
        prefix: str,
        depth: int,
        max_depth: int,
        show_hidden: bool,
        lines: list[str],
    ) -> None:
        if depth >= max_depth:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            lines.append(f"{prefix}[permission denied]")
            return

        if not show_hidden:
            entries = [e for e in entries if not e.name.startswith(".")]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{connector}{entry.name}{suffix}")
            if entry.is_dir() and len(lines) < 500:
                extension = "    " if is_last else "│   "
                self._walk(entry, prefix + extension, depth + 1, max_depth, show_hidden, lines)
