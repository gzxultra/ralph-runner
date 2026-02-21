"""Stats tracking, progress file management, and summary generation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from .display import fmt_duration, fmt_tokens
from .models import IterationResult


def find_last_iteration(output_dir: Path) -> int:
    """Find the highest iteration number in an existing run directory."""
    last = 0
    for f in output_dir.glob("iter-*.jsonl"):
        try:
            n = int(f.stem.split("-")[1])
            last = max(last, n)
        except (IndexError, ValueError):
            pass
    return last


def append_orchestrator_progress(
    progress_file: Path,
    iteration: int,
    result: IterationResult,
    verify_passed: bool | None,
    verify_cmd: str,
) -> None:
    """Append an iteration summary to the progress file."""
    if result.timed_out:
        status = "TIMED OUT (hard)"
    elif result.idle_timed_out:
        status = "TIMED OUT (idle)"
    elif result.exit_code != 0:
        status = f"FAILED (exit {result.exit_code})"
    else:
        status = "OK"

    lines = [
        f"\n---\n## [Orchestrator] Iteration {iteration} Summary",
        f"- **Status:** {status}",
        f"- **Duration:** {fmt_duration(result.duration)}",
        f"- **Cost:** ${result.cost_usd:.4f}",
        f"- **Tokens:** {fmt_tokens(result.input_tokens)} in / {fmt_tokens(result.output_tokens)} out",
    ]

    if verify_cmd and verify_passed is not None:
        lines.append(f"- **Verify:** {'PASS' if verify_passed else 'FAIL'}")

    if result.text:
        preview = result.text[:500].strip()
        if len(result.text) > 500:
            preview += "..."
        lines.append(
            f"\n<details><summary>Output preview</summary>\n\n{preview}\n\n</details>"
        )

    lines.append("")

    with open(progress_file, "a") as f:
        f.write("\n".join(lines))


def write_stats(
    output_dir: Path,
    prompt: str,
    started: str,
    settings: dict,
    iterations_data: list[dict],
) -> None:
    """Write cumulative stats to stats.json."""
    totals = {
        "iterations": len(iterations_data),
        "duration_s": sum(d["duration_s"] for d in iterations_data),
        "cost_usd": sum(d["cost_usd"] for d in iterations_data),
        "input_tokens": sum(d["input_tokens"] for d in iterations_data),
        "output_tokens": sum(d["output_tokens"] for d in iterations_data),
        "cache_read_tokens": sum(d["cache_read_tokens"] for d in iterations_data),
        "cache_write_tokens": sum(d["cache_write_tokens"] for d in iterations_data),
        "verify_passes": sum(1 for d in iterations_data if d.get("verify") is True),
        "verify_fails": sum(1 for d in iterations_data if d.get("verify") is False),
    }
    stats = {
        "task": prompt,
        "started": started,
        "settings": settings,
        "iterations": iterations_data,
        "totals": totals,
    }
    (output_dir / "stats.json").write_text(json.dumps(stats, indent=2))


def accumulate_model_usage(
    totals: dict[str, dict], iteration_usage: dict
) -> None:
    """Merge per-iteration model usage into running totals."""
    for model, data in iteration_usage.items():
        if model not in totals:
            totals[model] = {
                "inputTokens": 0,
                "outputTokens": 0,
                "cacheReadInputTokens": 0,
                "cacheCreationInputTokens": 0,
                "costUSD": 0.0,
            }
        for key in totals[model]:
            totals[model][key] += data.get(key, 0)


async def generate_summary(progress_file: Path) -> str:
    """Use Claude (haiku) to generate a concise summary of the run."""
    try:
        progress_text = progress_file.read_text()
    except (FileNotFoundError, OSError):
        return ""
    if not progress_text.strip():
        return ""
    if len(progress_text) > 30_000:
        progress_text = progress_text[:30_000] + "\n\n[truncated]"

    prompt = (
        "Summarize what was accomplished across all iterations of this task. "
        "Be concise — 5-10 bullet points max. Focus on concrete outcomes, "
        "not process details.\n\n"
        f"Progress file:\n\n{progress_text}"
    )

    proc = await asyncio.create_subprocess_exec(
        "claude",
        "-p",
        "--model",
        "haiku",
        "--output-format",
        "text",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(
            proc.communicate(prompt.encode("utf-8")), timeout=60
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        return "(Summary generation timed out)"
    return stdout.decode("utf-8", errors="replace").strip() if stdout else ""
