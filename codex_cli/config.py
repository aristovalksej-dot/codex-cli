"""Configuration management for Codex CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path.home() / ".codex-cli"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULT_MODEL = "gpt-5.3-codex"
DEFAULT_BASE_URL = "https://codex.sale/v1"

AVAILABLE_MODELS = [
    "gpt-5.3-codex",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.5",
]


@dataclass
class Config:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    max_tokens: int = 16384
    temperature: float = 0.2
    max_iterations: int = 50
    auto_approve: bool = False
    working_dir: str = field(default_factory=lambda: os.getcwd())
    system_prompt_extra: str = ""

    @classmethod
    def load(cls) -> Config:
        data: dict[str, Any] = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                data = yaml.safe_load(f) or {}

        api_key = (
            os.environ.get("CODEX_API_KEY")
            or os.environ.get("CODEX_SALE_API_KEY")
            or data.get("api_key", "")
        )
        base_url = os.environ.get("CODEX_BASE_URL") or data.get("base_url", DEFAULT_BASE_URL)
        model = os.environ.get("CODEX_MODEL") or data.get("model", DEFAULT_MODEL)

        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=int(data.get("max_tokens", 16384)),
            temperature=float(data.get("temperature", 0.2)),
            max_iterations=int(data.get("max_iterations", 50)),
            auto_approve=bool(data.get("auto_approve", False)),
            working_dir=data.get("working_dir", os.getcwd()),
            system_prompt_extra=data.get("system_prompt_extra", ""),
        )

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "max_iterations": self.max_iterations,
            "auto_approve": self.auto_approve,
            "system_prompt_extra": self.system_prompt_extra,
        }
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.api_key:
            errors.append(
                "API key not set. Use --api-key, "
                "env CODEX_API_KEY, or ~/.codex-cli/config.yaml"
            )
        if self.model not in AVAILABLE_MODELS:
            errors.append(f"Unknown model '{self.model}'. Available: {', '.join(AVAILABLE_MODELS)}")
        return errors
