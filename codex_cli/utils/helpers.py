"""Utility helpers."""

from __future__ import annotations

from pathlib import Path


def resolve_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def truncate(text: str, max_length: int = 5000) -> str:
    if len(text) <= max_length:
        return text
    half = max_length // 2
    return text[:half] + "\n\n... [truncated] ...\n\n" + text[-half:]


def is_binary_file(path: str | Path) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except (OSError, PermissionError):
        return False
