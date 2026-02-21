"""Data models for ralph-runner."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IterationResult:
    """Result of a single Claude Code iteration."""

    text: str = ""
    duration: float = 0.0
    timed_out: bool = False
    idle_timed_out: bool = False
    exit_code: int | None = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    num_turns: int = 0
    model_usage: dict = field(default_factory=dict)
