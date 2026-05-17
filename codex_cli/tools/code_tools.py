"""Code analysis and generation tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from codex_cli.tools.base import Tool


LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".md": "markdown",
    ".dockerfile": "dockerfile",
}


class AnalyzeCodeTool(Tool):
    name = "analyze_code"
    description = (
        "Analyze a code file or directory — count lines, detect language, list functions/classes, "
        "show structure. Useful for understanding a codebase."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to file or directory to analyze",
            },
        },
        "required": ["path"],
    }

    async def execute(self, path: str, **_: Any) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: Path not found: {p}"

        if p.is_file():
            return self._analyze_file(p)
        elif p.is_dir():
            return self._analyze_directory(p)
        return f"Error: Unknown path type: {p}"

    def _analyze_file(self, path: Path) -> str:
        ext = path.suffix.lower()
        language = LANGUAGE_EXTENSIONS.get(ext, "unknown")

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except PermissionError:
            return f"Error: Permission denied: {path}"

        lines = content.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for l in lines if not l.strip())
        comment_lines = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("#", "//", "/*", "*", "*/", "<!--", "--")):
                comment_lines += 1
        code_lines = total_lines - blank_lines - comment_lines

        functions: list[str] = []
        classes: list[str] = []
        imports: list[str] = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if language == "python":
                if stripped.startswith("def "):
                    name = stripped.split("(")[0].replace("def ", "")
                    functions.append(f"  L{i}: def {name}()")
                elif stripped.startswith("class "):
                    name = stripped.split("(")[0].split(":")[0].replace("class ", "")
                    classes.append(f"  L{i}: class {name}")
                elif stripped.startswith(("import ", "from ")):
                    imports.append(f"  {stripped[:80]}")
            elif language in ("javascript", "typescript", "jsx", "tsx"):
                if "function " in stripped and "(" in stripped:
                    functions.append(f"  L{i}: {stripped[:80]}")
                elif stripped.startswith("class "):
                    classes.append(f"  L{i}: {stripped[:80]}")
                elif stripped.startswith(("import ", "const ", "export ")):
                    if "require(" in stripped or "from " in stripped:
                        imports.append(f"  {stripped[:80]}")
            elif language == "go":
                if stripped.startswith("func "):
                    functions.append(f"  L{i}: {stripped[:80]}")
                elif stripped.startswith("type ") and "struct" in stripped:
                    classes.append(f"  L{i}: {stripped[:80]}")

        parts = [
            f"File: {path}",
            f"Language: {language}",
            f"Size: {path.stat().st_size:,} bytes",
            f"Lines: {total_lines} total ({code_lines} code, {blank_lines} blank, {comment_lines} comments)",
        ]

        if imports:
            parts.append(f"\nImports ({len(imports)}):")
            parts.extend(imports[:20])
        if classes:
            parts.append(f"\nClasses ({len(classes)}):")
            parts.extend(classes[:30])
        if functions:
            parts.append(f"\nFunctions ({len(functions)}):")
            parts.extend(functions[:50])

        return "\n".join(parts)

    def _analyze_directory(self, path: Path) -> str:
        stats: dict[str, int] = {}
        total_files = 0
        total_lines = 0
        total_size = 0

        skip_dirs = {
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            ".tox", "dist", "build", ".next", ".nuxt", "target",
        }

        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                fp = Path(root) / f
                ext = fp.suffix.lower()
                lang = LANGUAGE_EXTENSIONS.get(ext)
                if lang:
                    total_files += 1
                    try:
                        size = fp.stat().st_size
                        total_size += size
                        line_count = fp.read_text(
                            encoding="utf-8", errors="replace"
                        ).count("\n")
                        total_lines += line_count
                        stats[lang] = stats.get(lang, 0) + line_count
                    except (PermissionError, OSError):
                        pass

        parts = [
            f"Directory: {path}",
            f"Code files: {total_files}",
            f"Total lines: {total_lines:,}",
            f"Total size: {total_size / 1024:.1f} KB",
            "\nLanguage breakdown (by lines):",
        ]

        for lang, count in sorted(stats.items(), key=lambda x: -x[1]):
            pct = (count / total_lines * 100) if total_lines else 0
            parts.append(f"  {lang}: {count:,} ({pct:.1f}%)")

        return "\n".join(parts)


class GenerateCodeTool(Tool):
    name = "generate_code"
    description = (
        "Generate a code snippet or file based on a description. "
        "Specify the language and what you want to create. "
        "This tool returns the generated code as text — use write_file to save it."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "What code to generate (be specific about functionality, inputs, outputs)",
            },
            "language": {
                "type": "string",
                "description": "Programming language (e.g. python, javascript, go, rust)",
            },
            "filename": {
                "type": "string",
                "description": "Suggested filename for the code (optional)",
            },
        },
        "required": ["description", "language"],
    }

    async def execute(
        self, description: str, language: str, filename: str = "", **_: Any
    ) -> str:
        return (
            f"[Code generation request]\n"
            f"Language: {language}\n"
            f"Description: {description}\n"
            f"Filename: {filename or '(not specified)'}\n\n"
            f"Note: The AI model will generate the actual code based on this request. "
            f"Use write_file to save the generated code to disk."
        )
