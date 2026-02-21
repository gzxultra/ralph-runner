"""Terminal display helpers — colors, spinners, formatting."""

from __future__ import annotations

import time

# ANSI colors — 256-color for consistent rendering in iTerm2 + tmux
DIM = "\033[90m"
BOLD = "\033[1m"
RED = "\033[38;5;203m"
GREEN = "\033[38;5;114m"
YELLOW = "\033[38;5;221m"
BLUE = "\033[38;5;75m"
CYAN = "\033[38;5;81m"
WHITE = "\033[38;5;255m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K\r"

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
PANEL_WIDTH = 70


def fmt_duration(secs: float) -> str:
    if secs < 60:
        return f"{secs:.0f}s"
    m, s = divmod(int(secs), 60)
    return f"{m}m{s:02d}s"


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"  {DIM}{ts}{RESET}  {msg}", flush=True)


def debug_log(msg: str, debug: bool) -> None:
    import sys

    if debug:
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [DEBUG] {msg}", file=sys.stderr, flush=True)


def draw_box_line(text: str) -> str:
    ts = time.strftime("%H:%M:%S")
    return f"  {DIM}{ts}  {text}{RESET}"
