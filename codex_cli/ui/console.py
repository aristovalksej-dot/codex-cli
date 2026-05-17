"""Rich console output — formatting, syntax highlighting, spinners."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.theme import Theme

THEME = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "bold red",
        "tool_name": "bold magenta",
        "tool_result": "dim",
        "user_input": "bold white",
        "ai_response": "white",
        "header": "bold cyan",
    }
)

console = Console(theme=THEME)


def print_welcome() -> None:
    console.print()
    console.print(
        Panel(
            "[bold cyan]Codex CLI Agent[/bold cyan]\n"
            "[dim]AI-powered terminal assistant for VDS[/dim]\n\n"
            "[dim]Commands:[/dim]\n"
            "  [bold]/help[/bold]     — Show all commands\n"
            "  [bold]/model[/bold]    — Switch AI model\n"
            "  [bold]/clear[/bold]    — Clear conversation\n"
            "  [bold]/config[/bold]   — Show configuration\n"
            "  [bold]/tools[/bold]    — List available tools\n"
            "  [bold]/auto[/bold]     — Toggle auto-approve mode\n"
            "  [bold]/exit[/bold]     — Exit",
            title="[bold white]⚡ Codex CLI v1.0[/bold white]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


def print_message(role: str, content: str) -> None:
    if role == "user":
        console.print(f"\n[bold green]You:[/bold green] {content}")
    elif role == "assistant":
        console.print()
        md = Markdown(content)
        console.print(Panel(
            md, border_style="blue",
            title="[bold blue]Codex[/bold blue]",
            padding=(0, 1),
        ))
    elif role == "system":
        console.print(f"[dim]{content}[/dim]")


def print_tool_call(name: str, args_str: str) -> None:
    console.print(f"\n  [tool_name]⚙ Tool:[/tool_name] [bold]{name}[/bold]")
    if args_str and len(args_str) < 500:
        console.print(f"  [dim]Args: {args_str}[/dim]")
    elif args_str:
        console.print(f"  [dim]Args: {args_str[:500]}...[/dim]")


def print_tool_result(name: str, result: str, max_lines: int = 30) -> None:
    lines = result.splitlines()
    if len(lines) > max_lines:
        truncated = "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
    else:
        truncated = result

    console.print(
        Panel(
            truncated,
            title=f"[dim]Result: {name}[/dim]",
            border_style="dim",
            padding=(0, 1),
        )
    )


def print_error(msg: str) -> None:
    console.print(f"[error]Error: {msg}[/error]")


def print_info(msg: str) -> None:
    console.print(f"[info]{msg}[/info]")


def print_success(msg: str) -> None:
    console.print(f"[success]{msg}[/success]")


def print_warning(msg: str) -> None:
    console.print(f"[warning]{msg}[/warning]")


def print_tool_approval(name: str, args_str: str) -> str:
    console.print(f"\n  [warning]Tool requires approval:[/warning] [bold]{name}[/bold]")
    if args_str:
        display = args_str[:300] + ("..." if len(args_str) > 300 else "")
        console.print(f"  [dim]{display}[/dim]")
    try:
        response = console.input("  [bold]Allow? (y/n/always): [/bold]").strip().lower()
    except (EOFError, KeyboardInterrupt):
        response = "n"
    return response


def print_models(models: list[str], current: str) -> None:
    console.print("\n[header]Available Models:[/header]")
    for m in models:
        marker = " [bold green]← current[/bold green]" if m == current else ""
        console.print(f"  • {m}{marker}")
    console.print()


def print_tools(tools: list[dict[str, str]]) -> None:
    console.print("\n[header]Available Tools:[/header]")
    for t in tools:
        console.print(f"  [tool_name]{t['name']}[/tool_name] — {t['description']}")
    console.print()


def print_config(config_data: dict[str, str]) -> None:
    console.print("\n[header]Configuration:[/header]")
    for key, value in config_data.items():
        display_value = value
        if key == "api_key" and len(value) > 8:
            display_value = value[:4] + "..." + value[-4:]
        console.print(f"  [bold]{key}:[/bold] {display_value}")
    console.print()


def print_thinking() -> None:
    console.print("[dim]  Thinking...[/dim]", end="\r")


def clear_thinking() -> None:
    console.print("                              ", end="\r")


def print_streaming_token(token: str) -> None:
    console.print(token, end="", highlight=False)
