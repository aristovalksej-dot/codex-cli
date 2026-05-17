"""Main entry point — CLI argument parsing and interactive REPL."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from codex_cli import __version__
from codex_cli.agent import Agent
from codex_cli.config import AVAILABLE_MODELS, CONFIG_DIR, Config
from codex_cli.tools import create_registry
from codex_cli.ui.console import (
    console,
    print_config,
    print_error,
    print_info,
    print_message,
    print_models,
    print_success,
    print_tools,
    print_warning,
    print_welcome,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="codex",
        description="Codex CLI — AI-powered terminal agent for VDS",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"codex-cli {__version__}",
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=None,
        choices=AVAILABLE_MODELS,
        help="AI model to use",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for codex.sale",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Base API URL",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all tool executions (no confirmation prompts)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive setup to configure API key and preferences",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="One-shot prompt (if provided, runs without REPL)",
    )
    return parser.parse_args()


def run_setup() -> None:
    """Interactive setup wizard."""
    console.print("\n[bold cyan]Codex CLI Setup[/bold cyan]\n")

    config = Config.load()

    api_key = console.input("[bold]API Key from codex.sale: [/bold]").strip()
    if api_key:
        config.api_key = api_key

    console.print("\n[bold]Available models:[/bold]")
    for i, m in enumerate(AVAILABLE_MODELS, 1):
        marker = " (current)" if m == config.model else ""
        console.print(f"  {i}. {m}{marker}")
    prompt_msg = f"\n[bold]Select model [1-{len(AVAILABLE_MODELS)}] (keep current): [/bold]"
    choice = console.input(prompt_msg).strip()
    if choice.isdigit() and 1 <= int(choice) <= len(AVAILABLE_MODELS):
        config.model = AVAILABLE_MODELS[int(choice) - 1]

    auto = console.input("\n[bold]Auto-approve tool executions? (y/n, current: "
                         f"{'yes' if config.auto_approve else 'no'}): [/bold]").strip().lower()
    if auto in ("y", "yes", "д", "да"):
        config.auto_approve = True
    elif auto in ("n", "no", "н", "нет"):
        config.auto_approve = False

    config.save()
    print_success(f"\nConfiguration saved to {CONFIG_DIR}/config.yaml")
    console.print()


async def run_one_shot(agent: Agent, prompt: str) -> None:
    """Run a single prompt and exit."""
    response = await agent.run(prompt)
    if response:
        print_message("assistant", response)
    await agent.close()


async def run_repl(agent: Agent) -> None:
    """Run the interactive REPL loop."""
    print_welcome()
    auto_str = "ON" if agent.auto_approve else "OFF"
    print_info(f"Model: {agent.config.model} | Auto-approve: {auto_str}")
    print_info(f"Working directory: {os.getcwd()}")
    console.print()

    while True:
        try:
            user_input = console.input("[bold green]>>> [/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            handled = await _handle_command(user_input, agent)
            if handled == "exit":
                break
            continue

        response = await agent.run(user_input)
        if response:
            print_message("assistant", response)


async def _handle_command(cmd: str, agent: Agent) -> str:
    """Handle slash commands. Returns 'exit' to quit."""
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command in ("/exit", "/quit", "/q"):
        console.print("[dim]Goodbye![/dim]")
        return "exit"

    elif command == "/help":
        console.print(
            "\n[header]Commands:[/header]\n"
            "  [bold]/help[/bold]              — Show this help\n"
            "  [bold]/model[/bold] [name]      — Switch model or list models\n"
            "  [bold]/clear[/bold]             — Clear conversation history\n"
            "  [bold]/config[/bold]            — Show current configuration\n"
            "  [bold]/tools[/bold]             — List available tools\n"
            "  [bold]/auto[/bold]              — Toggle auto-approve mode\n"
            "  [bold]/cd[/bold] <path>         — Change working directory\n"
            "  [bold]/save[/bold]              — Save current config to file\n"
            "  [bold]/exit[/bold]              — Exit Codex CLI\n"
        )

    elif command == "/clear":
        agent.clear_history()
        print_success("Conversation cleared.")

    elif command == "/model":
        if arg:
            if arg in AVAILABLE_MODELS:
                agent.config.model = arg
                print_success(f"Model switched to: {arg}")
            else:
                print_error(f"Unknown model: {arg}")
                print_models(AVAILABLE_MODELS, agent.config.model)
        else:
            print_models(AVAILABLE_MODELS, agent.config.model)

    elif command == "/config":
        print_config(
            {
                "api_key": agent.config.api_key,
                "base_url": agent.config.base_url,
                "model": agent.config.model,
                "max_tokens": str(agent.config.max_tokens),
                "temperature": str(agent.config.temperature),
                "max_iterations": str(agent.config.max_iterations),
                "auto_approve": str(agent.auto_approve),
                "working_dir": os.getcwd(),
            }
        )

    elif command == "/tools":
        tools_list = [
            {"name": t.name, "description": t.description}
            for t in agent.registry.list_tools()
        ]
        print_tools(tools_list)

    elif command == "/auto":
        agent.auto_approve = not agent.auto_approve
        state = "ON" if agent.auto_approve else "OFF"
        print_info(f"Auto-approve: {state}")

    elif command == "/cd":
        if arg:
            try:
                target = os.path.expanduser(arg)
                os.chdir(target)
                print_success(f"Changed directory to: {os.getcwd()}")
            except FileNotFoundError:
                print_error(f"Directory not found: {arg}")
            except PermissionError:
                print_error(f"Permission denied: {arg}")
        else:
            print_info(f"Current directory: {os.getcwd()}")

    elif command == "/save":
        agent.config.save()
        print_success("Configuration saved.")

    else:
        print_warning(f"Unknown command: {command}. Type /help for help.")

    return ""


def main() -> None:
    args = parse_args()

    if args.setup:
        run_setup()
        return

    config = Config.load()

    if args.api_key:
        config.api_key = args.api_key
    if args.model:
        config.model = args.model
    if args.base_url:
        config.base_url = args.base_url
    if args.auto_approve:
        config.auto_approve = True

    errors = config.validate()
    if errors:
        for err in errors:
            print_error(err)
        console.print(
            "\n[dim]Run 'codex --setup' to configure, "
            "or set CODEX_API_KEY env variable.[/dim]"
        )
        sys.exit(1)

    registry = create_registry()
    agent = Agent(config, registry)

    if args.prompt:
        prompt_text = " ".join(args.prompt)
        asyncio.run(run_one_shot(agent, prompt_text))
    else:
        try:
            asyncio.run(run_repl(agent))
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
        finally:
            asyncio.run(agent.close())


if __name__ == "__main__":
    main()
