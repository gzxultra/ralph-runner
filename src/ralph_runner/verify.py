"""Verification helpers — run commands and track pass/fail history."""

from __future__ import annotations

import asyncio


async def run_verify(cmd: str, timeout: int = 300) -> tuple[bool, str]:
    """Run a verification command and return (passed, output)."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        return (False, f"Verify command timed out after {timeout}s")
    output = stdout.decode("utf-8", errors="replace") if stdout else ""
    return (proc.returncode == 0, output)


def verify_trend_str(history: list[bool | None]) -> str:
    """Return a compact trend string like (3/5 ↑)."""
    results = [r for r in history if r is not None]
    if not results:
        return ""
    passes = sum(results)
    total = len(results)
    arrow = ""
    if len(results) >= 4:
        recent = results[-3:]
        prior = results[-6:-3] if len(results) >= 6 else results[:-3]
        recent_rate = sum(recent) / len(recent)
        prior_rate = sum(prior) / len(prior) if prior else 0
        if recent_rate > prior_rate:
            arrow = " ↑"
        elif recent_rate < prior_rate:
            arrow = " ↓"
        else:
            arrow = " →"
    return f"({passes}/{total}{arrow})"


def verify_sequence_str(history: list[bool | None]) -> str:
    """Return a glyph sequence like ✓✓✗✓  (3/4 passed, converging)."""
    results = [r for r in history if r is not None]
    if not results:
        return ""
    glyphs = {None: "·", True: "✓", False: "✗"}
    chars = [glyphs[r] for r in history]
    passes = sum(results)
    total = len(results)
    seq = "".join(chars)
    trend = ""
    if len(results) >= 3:
        last_3 = results[-3:]
        if all(last_3):
            trend = ", converging"
        elif not any(last_3):
            trend = ", diverging"
    return f"{seq}  ({passes}/{total} passed{trend})"
