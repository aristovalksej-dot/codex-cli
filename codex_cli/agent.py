"""Agent loop — orchestrates conversation, tool selection, and execution."""

from __future__ import annotations

import os
import platform
from typing import Any

from codex_cli.api_client import APIClient, APIError
from codex_cli.config import Config
from codex_cli.tools import ToolRegistry
from codex_cli.ui.console import (
    clear_thinking,
    print_error,
    print_thinking,
    print_tool_approval,
    print_tool_call,
    print_tool_result,
    print_warning,
)

DANGEROUS_TOOLS = {
    "run_command",
    "write_file",
    "edit_file",
    "delete_file",
    "append_file",
    "clone_repo",
    "git_command",
}

SYSTEM_PROMPT = """\
You are Codex CLI — a powerful AI coding agent running directly on the user's server (VDS).
You have access to a comprehensive set of tools to help the user with any task.

## Your Capabilities
- **Files**: Read, write, edit, delete, create files/dirs, tree view.
- **Shell**: Execute any command — packages, builds, processes.
- **Web**: Fetch/read web pages, search the web.
- **GitHub**: Clone repos, view info, search, git commands.
- **Code Analysis**: Structure, line counts, languages, functions.
- **Code Generation**: Generate code in any language.
- **Search**: Regex search (grep/ripgrep), find files by name.

## Guidelines
1. Use tools proactively, don't just explain.
2. Chain tools for multi-step tasks automatically.
3. Give SHORT answers. Only show what was asked.
4. For "which directory" — just answer the path.
5. For "list files" — use `ls`, not `ls -la`.
6. Don't add extra flags the user didn't ask for.
7. On failure, explain error and try alternatives.
8. Confirm destructive ops unless auto-approve is on.
9. Use the most efficient tool for each task.

## Context
- OS: {os_info}
- CWD: {cwd}
- Shell: bash
{extra_prompt}

Respond in the user's language. Be concise but thorough.
"""


class Agent:
    def __init__(self, config: Config, registry: ToolRegistry) -> None:
        self.config = config
        self.registry = registry
        self.client = APIClient(config)
        self.messages: list[dict[str, Any]] = []
        self.auto_approve = config.auto_approve
        self._init_system_prompt()

    def _init_system_prompt(self) -> None:
        extra = ""
        if self.config.system_prompt_extra:
            extra = f"\n## Additional Instructions\n{self.config.system_prompt_extra}\n"

        system_content = SYSTEM_PROMPT.format(
            os_info=f"{platform.system()} {platform.release()}",
            cwd=os.getcwd(),
            extra_prompt=extra,
        )
        self.messages = [{"role": "system", "content": system_content}]

    def clear_history(self) -> None:
        self._init_system_prompt()

    async def run(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        tools_schema = self.registry.to_openai_tools()

        final_response = ""
        iterations = 0

        while iterations < self.config.max_iterations:
            iterations += 1
            print_thinking()

            try:
                response = await self.client.chat_completion(
                    messages=self.messages,
                    tools=tools_schema if tools_schema else None,
                )
            except APIError as e:
                clear_thinking()
                error_msg = f"API Error: {e.message}"
                print_error(error_msg)
                return error_msg
            except Exception as e:
                clear_thinking()
                error_msg = f"Connection error: {e}"
                print_error(error_msg)
                return error_msg

            clear_thinking()

            message = self.client.extract_message(response)
            self.messages.append(message)

            if not self.client.has_tool_calls(message):
                final_response = message.get("content", "")
                break

            tool_calls = self.client.extract_tool_calls(message)

            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                arguments_str = func.get("arguments", "{}")
                tool_call_id = tc.get("id", "")

                print_tool_call(tool_name, arguments_str)

                if tool_name in DANGEROUS_TOOLS and not self.auto_approve:
                    approval = print_tool_approval(tool_name, arguments_str)
                    if approval == "always":
                        self.auto_approve = True
                    elif approval not in ("y", "yes", "д", "да"):
                        result = "Tool execution denied by user."
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": result,
                            }
                        )
                        print_tool_result(tool_name, result)
                        continue

                result = await self.registry.execute(tool_name, arguments_str)
                print_tool_result(tool_name, result)

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result,
                    }
                )

        if iterations >= self.config.max_iterations:
            print_warning(f"Reached max iterations ({self.config.max_iterations})")

        return final_response

    async def close(self) -> None:
        await self.client.close()
