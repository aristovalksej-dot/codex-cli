"""Shell command execution tool."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from codex_cli.tools.base import Tool


class ShellCommandTool(Tool):
    name = "run_command"
    description = (
        "Execute a shell command on the system and return its output. "
        "Use this for any system operations: installing packages, running builds, "
        "git operations, process management, and more. "
        "Commands run in a bash shell with a timeout."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"},
            "working_dir": {
                "type": "string",
                "description": "Working directory for the command (optional)",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 120, max: 600)",
            },
        },
        "required": ["command"],
    }

    async def execute(
        self, command: str, working_dir: str = "", timeout: int = 120, **_: Any
    ) -> str:
        cwd = working_dir or os.getcwd()
        timeout = min(max(timeout, 5), 600)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ},
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return f"Error: Command timed out after {timeout}s\nCommand: {command}"
        except FileNotFoundError:
            return f"Error: Working directory not found: {cwd}"
        except Exception as e:
            return f"Error executing command: {e}"

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if len(stdout_text) > 50000:
            stdout_text = (
                stdout_text[:25000]
                + "\n\n... [truncated] ...\n\n"
                + stdout_text[-25000:]
            )
        if len(stderr_text) > 20000:
            stderr_text = (
                stderr_text[:10000]
                + "\n\n... [truncated] ...\n\n"
                + stderr_text[-10000:]
            )

        parts: list[str] = []
        if stdout_text:
            parts.append(stdout_text)
        if stderr_text:
            parts.append(stderr_text)
        if process.returncode != 0:
            parts.append(f"[exit code: {process.returncode}]")
        if not parts:
            parts.append("(no output)")

        return "\n".join(parts)
