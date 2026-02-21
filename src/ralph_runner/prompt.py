"""Prompt construction for each iteration."""

from __future__ import annotations

import re
from pathlib import Path

from .models import IterationResult

COMPLETION_SIGNAL = "###RALPH_COMPLETE###"
MAX_PROGRESS_SIZE = 50_000
PROGRESS_TAIL_SIZE = 20_000


def sanitize_prefix(prompt: str) -> str:
    prefix = prompt[:40].lower()
    prefix = re.sub(r"[^a-z0-9]+", "-", prefix)
    prefix = prefix.strip("-")
    return prefix or "ralph"


def _error_context(prev: IterationResult) -> str:
    if prev.timed_out:
        return (
            "The previous iteration hit the hard timeout. "
            "It may have been stuck in a long-running operation. "
            "Try breaking work into smaller steps."
        )
    if prev.idle_timed_out:
        return (
            "The previous iteration timed out due to inactivity. "
            "It likely got stuck waiting for a tool call or response. "
            "Try smaller, faster operations and avoid long-running commands."
        )
    if prev.exit_code is not None and prev.exit_code != 0:
        return (
            f"The previous iteration crashed with exit code {prev.exit_code}. "
            "Check the progress file for what was completed before the crash "
            "and continue from there."
        )
    return ""


def build_prompt(
    user_prompt: str,
    iteration: int,
    min_iterations: int,
    progress_file: Path,
    plan_file: Path | None,
    verify_cmd: str,
    prev_result: IterationResult | None = None,
) -> str:
    parts: list[str] = []

    parts.append(user_prompt)
    parts.append("")
    parts.append("---")
    parts.append(f"## Outer Loop (Iteration {iteration})")
    parts.append("")
    parts.append(
        "You're in an outer loop. Each iteration is a fresh Claude session "
        "with no memory of previous sessions."
    )
    parts.append("")

    # Iteration discipline
    if iteration == 1:
        parts.append(
            "This is the first iteration. Start by reading any existing files "
            "in the output directory, then begin work."
        )
    else:
        parts.append("### Iteration Discipline")
        parts.append(
            "- **Read progress first.** Check the progress file before doing anything."
        )
        parts.append(
            "- **Never redo completed work.** If a phase or step is marked done, skip it."
        )
        parts.append(
            "- **Build incrementally.** Each iteration should advance beyond where the last one stopped."
        )
        parts.append(
            "- **Go deeper, not wider.** Improve existing work rather than starting fresh."
        )
        parts.append(
            "- **If stuck, try a different approach** rather than repeating what failed."
        )
    parts.append("")

    # Error context injection from previous iteration
    if prev_result is not None:
        ctx = _error_context(prev_result)
        if ctx:
            parts.append("### Previous Iteration Status")
            parts.append(ctx)
            parts.append("")

    if plan_file is not None:
        if iteration == 1:
            parts.append("### Planning (First Iteration)")
            parts.append(
                f"Before starting work, create a plan file at `{plan_file}`:"
            )
            parts.append("- Break the task into 3-7 phases with checkboxes")
            parts.append("- Include key questions to answer")
            parts.append("- Then start Phase 1")
            parts.append("")
        else:
            try:
                plan_text = plan_file.read_text()
                all_plan_lines = plan_text.splitlines()
                plan_lines = all_plan_lines[:80]
                if plan_lines:
                    parts.append("### Current Plan")
                    parts.append("```markdown")
                    parts.append("\n".join(plan_lines))
                    parts.append("```")
                    if len(all_plan_lines) > 80:
                        parts.append(
                            f"(truncated, {len(all_plan_lines)} total lines)"
                        )
                    parts.append("")
                    parts.append(
                        f"Read `{plan_file}` before major decisions. "
                        "Update phase status as you progress."
                    )
                    parts.append("")
            except (FileNotFoundError, OSError):
                parts.append("### Planning")
                parts.append(
                    f"Create a plan file at `{plan_file}` with 3-7 phases "
                    "and checkboxes. Then continue work."
                )
                parts.append("")

    try:
        progress_text = progress_file.read_text()
    except (FileNotFoundError, OSError):
        progress_text = ""
    if progress_text.strip():
        if len(progress_text) > MAX_PROGRESS_SIZE:
            progress_text = (
                f"[Earlier iterations summarized — showing last "
                f"{PROGRESS_TAIL_SIZE // 1000}K chars]\n\n"
                + progress_text[-PROGRESS_TAIL_SIZE:]
            )
        parts.append("### Progress from Previous Iterations")
        parts.append("```")
        parts.append(progress_text)
        parts.append("```")
        parts.append("")

    parts.append(
        f"Before ending, update `{progress_file}` with what you accomplished this iteration."
    )
    parts.append("")

    if verify_cmd:
        parts.append("### Verification")
        parts.append("This command will be run after your iteration:")
        parts.append(f"```\n{verify_cmd}\n```")
        parts.append("")

    parts.append(
        f"To signal completion: output {COMPLETION_SIGNAL} "
        f"(only accepted after iteration {min_iterations})"
    )

    return "\n".join(parts)
