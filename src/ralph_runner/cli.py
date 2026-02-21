"""ralph-runner CLI — outer-loop orchestrator for Claude Code."""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time
from pathlib import Path

from .display import (
    BOLD,
    BLUE,
    CYAN,
    DIM,
    GREEN,
    PANEL_WIDTH,
    RED,
    RESET,
    WHITE,
    YELLOW,
    fmt_duration,
    fmt_tokens,
    log,
)
from .models import IterationResult
from .prompt import COMPLETION_SIGNAL, build_prompt, sanitize_prefix
from .runner import run_iteration
from .stats import (
    accumulate_model_usage,
    append_orchestrator_progress,
    find_last_iteration,
    generate_summary,
    write_stats,
)
from .verify import run_verify, verify_sequence_str, verify_trend_str


async def async_main() -> None:
    parser = argparse.ArgumentParser(
        prog="ralph-runner",
        description="Outer-loop orchestrator that spawns iterative Claude Code sessions.",
    )
    parser.add_argument("--prompt", required=True, help="The task prompt")
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Min iterations before completion accepted (default: 10)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Hard stop after this many iterations (default: 50)",
    )
    parser.add_argument("--plan", action="store_true", default=True, dest="plan")
    parser.add_argument("--no-plan", action="store_false", dest="plan")
    parser.add_argument(
        "--verify",
        default="",
        help="Verification command to run after each iteration",
    )
    parser.add_argument(
        "--mode",
        choices=["hitl", "afk"],
        default="afk",
        help="Mode: hitl (human-in-the-loop) or afk (autonomous, default)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Hard timeout per iteration in seconds (default: 900)",
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=120,
        help="Idle timeout per iteration in seconds (default: 120)",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Claude model to use (default: sonnet)",
    )
    parser.add_argument(
        "--internet", action="store_true", help="Enable internet access for Claude sessions"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "--resume",
        metavar="DIR",
        help="Resume a previous run from its output directory",
    )
    args = parser.parse_args()

    # Signal handling
    shutdown_requested = False
    loop = asyncio.get_running_loop()

    def handle_sigint() -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            log(f"{RED}Force quit.{RESET}")
            loop.stop()
            return
        shutdown_requested = True
        log(
            f"{YELLOW}Shutting down after current iteration... "
            f"(Ctrl+C again to force){RESET}"
        )

    loop.add_signal_handler(signal.SIGINT, handle_sigint)

    started = time.strftime("%Y-%m-%d %H:%M:%S")

    # Setup directories
    if args.resume:
        output_dir = Path(args.resume).expanduser().resolve()
        if not output_dir.is_dir():
            print(f"  {RED}Resume directory does not exist: {output_dir}{RESET}")
            sys.exit(1)
        progress_file = output_dir / "progress.md"
        plan_file = (output_dir / "plan.md") if args.plan else None
        start_iteration = find_last_iteration(output_dir)
        log(f"Resuming from iteration {start_iteration}")
    else:
        prefix = sanitize_prefix(args.prompt)
        ts = time.strftime("%Y%m%d-%H%M%S")
        output_dir = Path.home() / ".ralph-runner" / "runs" / f"{ts}-{prefix}"
        output_dir.mkdir(parents=True, exist_ok=True)
        progress_file = output_dir / "progress.md"
        plan_file = (output_dir / "plan.md") if args.plan else None
        progress_file.write_text(
            f"# Ralph Runner Progress\n\nTask: {args.prompt}\nStarted: {started}\n\n"
        )
        start_iteration = 0

    # Banner
    print()
    print(f"  {BOLD}{CYAN}◉ RALPH RUNNER{RESET}")
    print(f"  {DIM}{'─' * PANEL_WIDTH}{RESET}")
    col1 = f"{DIM}Iterations:{RESET} {WHITE}{args.iterations}–{args.max_iterations}{RESET}"
    col2 = f"{DIM}Mode:{RESET} {WHITE}{args.mode}{RESET}"
    col3 = f"{DIM}Timeout:{RESET} {WHITE}{fmt_duration(args.timeout)}{RESET}"
    print(f"  {col1}  {DIM}│{RESET}  {col2}  {DIM}│{RESET}  {col3}")
    col4 = f"{DIM}Plan:{RESET} {WHITE}{'ON' if args.plan else 'OFF'}{RESET}"
    col5 = f"{DIM}Idle:{RESET} {WHITE}{fmt_duration(args.idle_timeout)}{RESET}"
    col6 = f"{DIM}Internet:{RESET} {WHITE}{'ON' if args.internet else 'OFF'}{RESET}"
    print(f"  {col4}        {DIM}│{RESET}  {col5}  {DIM}│{RESET}  {col6}")
    col7 = f"{DIM}Model:{RESET} {WHITE}{args.model}{RESET}"
    print(f"  {col7}")
    if args.verify:
        print(f"  {DIM}Verify:{RESET}  {WHITE}{args.verify}{RESET}")
    if args.resume:
        print(f"  {DIM}Resume:{RESET}  from iteration {start_iteration}")
    print(f"  {DIM}Output:{RESET}  {output_dir}")
    print(f"  {DIM}{'─' * PANEL_WIDTH}{RESET}")
    print()

    # Stats
    run_start = time.monotonic()
    total_cost = 0.0
    verify_history: list[bool | None] = []
    model_usage_totals: dict[str, dict] = {}
    iterations_data: list[dict] = []
    settings = {
        "min_iterations": args.iterations,
        "max_iterations": args.max_iterations,
        "mode": args.mode,
        "timeout": args.timeout,
        "idle_timeout": args.idle_timeout,
        "plan": args.plan,
        "verify": args.verify,
        "internet": args.internet,
        "model": args.model,
    }

    prev_result: IterationResult | None = None
    iteration = start_iteration
    while True:
        iteration += 1

        if shutdown_requested:
            log(f"{YELLOW}Shutdown requested.{RESET}")
            break

        if iteration > args.max_iterations:
            log(
                f"{YELLOW}Max iterations reached ({args.max_iterations}). Stopping.{RESET}"
            )
            break

        # Iteration header
        if iteration == start_iteration + 1:
            print(f"\n  {BOLD}{BLUE}━━━ Iteration {iteration} ━━━{RESET}")
        else:
            elapsed_total = fmt_duration(time.monotonic() - run_start)
            total_in = sum(d["input_tokens"] for d in iterations_data)
            total_out = sum(d["output_tokens"] for d in iterations_data)
            print(
                f"\n  {BOLD}{BLUE}━━━ Iteration {iteration} ━━━{RESET}"
                f"  {DIM}elapsed: {elapsed_total} | ${total_cost:.2f}"
                f" | {fmt_tokens(total_in)} in / {fmt_tokens(total_out)} out{RESET}"
            )

        prompt = build_prompt(
            user_prompt=args.prompt,
            iteration=iteration,
            min_iterations=args.iterations,
            progress_file=progress_file,
            plan_file=plan_file,
            verify_cmd=args.verify,
            prev_result=prev_result,
        )

        if args.debug:
            prompt_file = output_dir / f"prompt-{iteration:02d}.md"
            prompt_file.write_text(prompt)
            from .display import debug_log

            debug_log(f"Saved prompt to {prompt_file}", args.debug)

        result = await run_iteration(
            prompt=prompt,
            iteration=iteration,
            output_dir=output_dir,
            timeout=args.timeout,
            idle_timeout=args.idle_timeout,
            mode=args.mode,
            internet=args.internet,
            debug=args.debug,
            cumulative_cost=total_cost,
            model=args.model,
        )

        total_cost += result.cost_usd
        accumulate_model_usage(model_usage_totals, result.model_usage)

        # Status line
        duration_str = fmt_duration(result.duration)
        if result.timed_out:
            icon = f"{RED}✗{RESET}"
            status_text = f"{RED}timeout{RESET} (hard)"
        elif result.idle_timed_out:
            icon = f"{YELLOW}✗{RESET}"
            status_text = f"{YELLOW}timeout{RESET} (idle)"
        elif result.exit_code != 0:
            icon = f"{RED}✗{RESET}"
            status_text = f"{RED}exit {result.exit_code}{RESET}"
        elif not result.text:
            icon = f"{YELLOW}○{RESET}"
            status_text = f"{YELLOW}no output{RESET}"
        else:
            icon = f"{GREEN}✓{RESET}"
            status_text = f"{GREEN}done{RESET}"

        cost_str = f"${result.cost_usd:.2f}" if result.cost_usd > 0 else "$-"
        token_str = (
            f"{fmt_tokens(result.input_tokens)} in / "
            f"{fmt_tokens(result.output_tokens)} out"
        )

        # Verify
        verify_passed: bool | None = None
        verify_output: str = ""
        if args.verify and result.text:
            verify_passed, verify_output = await run_verify(args.verify)

        verify_history.append(verify_passed)

        # Orchestrator progress
        append_orchestrator_progress(
            progress_file=progress_file,
            iteration=iteration,
            result=result,
            verify_passed=verify_passed,
            verify_cmd=args.verify,
        )

        # Record iteration data
        iter_status = "ok"
        if result.timed_out:
            iter_status = "timeout_hard"
        elif result.idle_timed_out:
            iter_status = "timeout_idle"
        elif result.exit_code != 0:
            iter_status = f"exit_{result.exit_code}"
        iterations_data.append(
            {
                "iteration": iteration,
                "status": iter_status,
                "duration_s": round(result.duration, 1),
                "cost_usd": round(result.cost_usd, 4),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_read_tokens": result.cache_read_tokens,
                "cache_write_tokens": result.cache_write_tokens,
                "num_turns": result.num_turns,
                "verify": verify_passed,
            }
        )
        write_stats(output_dir, args.prompt, started, settings, iterations_data)

        psize = progress_file.stat().st_size if progress_file.exists() else 0
        psize_str = f"{psize / 1024:.1f}KB" if psize > 1024 else f"{psize}B"

        print(
            f"\n  {icon}  {status_text}  {DIM}│{RESET}  {duration_str}"
            f"  {DIM}│{RESET}  {cost_str}  {DIM}│{RESET}  {token_str}"
            f"  {DIM}│{RESET}  {DIM}progress: {psize_str}{RESET}"
        )

        if args.verify and verify_passed is not None:
            trend = verify_trend_str(verify_history)
            if verify_passed:
                print(
                    f"  {GREEN}✓{RESET}  {DIM}verify passed{RESET}  {DIM}{trend}{RESET}"
                )
            else:
                print(
                    f"  {RED}✗{RESET}  {RED}verify failed{RESET}  {DIM}{trend}{RESET}"
                )
                if verify_output.strip():
                    for vline in verify_output.strip().splitlines()[-5:]:
                        print(f"     {DIM}{vline}{RESET}")

        # Iteration summary
        if result.text:
            text_lines = [
                line.strip()
                for line in result.text.strip().split("\n")
                if line.strip()
            ]
            if text_lines:
                print(f"  {DIM}{'─' * 40}{RESET}")
                for sline in text_lines[-3:]:
                    print(f"  {DIM}{sline[:100]}{RESET}")
                print(f"  {DIM}{'─' * 40}{RESET}")

        if not result.text and (
            result.timed_out or result.idle_timed_out or result.exit_code != 0
        ):
            prev_result = result
            continue

        # Completion check
        if COMPLETION_SIGNAL in result.text:
            if iteration >= args.iterations and (
                verify_passed is None or verify_passed
            ):
                print(f"\n  {BOLD}{GREEN}◉ Task completed!{RESET}")
                break
            elif iteration < args.iterations:
                print(
                    f"  {YELLOW}⏳{RESET}  {DIM}completion blocked: "
                    f"{iteration}/{args.iterations} iterations{RESET}"
                )
            elif verify_passed is not None and not verify_passed:
                print(
                    f"  {YELLOW}⏳{RESET}  {DIM}completion blocked: verify failed{RESET}"
                )

        prev_result = result

        if shutdown_requested:
            log(f"{YELLOW}Shutdown requested.{RESET}")
            break

        if args.mode == "hitl":
            try:
                response = await asyncio.to_thread(
                    input,
                    f"\n  {DIM}Press Enter to continue, 'q' to quit:{RESET} ",
                )
                if response.strip().lower() in ("q", "quit"):
                    log("Stopped by user.")
                    break
            except (EOFError, KeyboardInterrupt):
                log("Stopped.")
                break

    # Final summary
    total_time = time.monotonic() - run_start
    iters_done = iteration - start_iteration
    print()
    print(f"  {DIM}{'━' * PANEL_WIDTH}{RESET}")
    print(f"  {BOLD}{WHITE}Summary{RESET}")
    print(f"  {DIM}{'─' * PANEL_WIDTH}{RESET}")

    total_in = sum(d["input_tokens"] for d in iterations_data)
    total_out = sum(d["output_tokens"] for d in iterations_data)
    print(
        f"  {DIM}Iterations:{RESET}   {WHITE}{iters_done}{RESET}"
        f"  {DIM}│{RESET}  {DIM}Time:{RESET} {WHITE}{fmt_duration(total_time)}{RESET}"
        f"  {DIM}│{RESET}  {DIM}Cost:{RESET} {BOLD}${total_cost:.2f}{RESET}"
        f"  {DIM}│{RESET}  {DIM}Tokens:{RESET} {WHITE}{fmt_tokens(total_in)} in / "
        f"{fmt_tokens(total_out)} out{RESET}"
    )

    if args.verify:
        seq = verify_sequence_str(verify_history)
        if seq:
            print(f"  {DIM}Verify:{RESET}      {seq}")

    # Token usage breakdown by model
    if model_usage_totals:
        print(f"\n  {BOLD}{WHITE}Token Usage{RESET}")
        print(f"  {DIM}{'─' * PANEL_WIDTH}{RESET}")
        print(
            f"  {DIM}{'Model':<25} {'Input':>8} {'Output':>8} "
            f"{'Cache Rd':>10} {'Cache Wr':>10} {'Cost':>8}{RESET}"
        )
        for model in sorted(model_usage_totals):
            data = model_usage_totals[model]
            short = model.replace("claude-", "")
            cost = f"${data['costUSD']:.2f}"
            print(
                f"  {short:<25}"
                f" {fmt_tokens(data['inputTokens']):>8}"
                f" {fmt_tokens(data['outputTokens']):>8}"
                f" {fmt_tokens(data['cacheReadInputTokens']):>10}"
                f" {fmt_tokens(data['cacheCreationInputTokens']):>10}"
                f" {cost:>8}"
            )
        print(f"  {DIM}{'─' * PANEL_WIDTH}{RESET}")
        total_crd = sum(
            d["cacheReadInputTokens"] for d in model_usage_totals.values()
        )
        total_cwr = sum(
            d["cacheCreationInputTokens"] for d in model_usage_totals.values()
        )
        total_cost_str = f"${total_cost:.2f}"
        print(
            f"  {BOLD}{'Total':<25}"
            f" {fmt_tokens(total_in):>8}"
            f" {fmt_tokens(total_out):>8}"
            f" {fmt_tokens(total_crd):>10}"
            f" {fmt_tokens(total_cwr):>10}"
            f" {total_cost_str:>8}{RESET}"
        )

    # Generate LLM summary
    log(f"{DIM}Generating summary...{RESET}")
    summary_text = await generate_summary(progress_file)
    if summary_text:
        print(f"\n  {BOLD}{WHITE}What Was Accomplished{RESET}")
        print(f"  {DIM}{'─' * PANEL_WIDTH}{RESET}")
        for sline in summary_text.split("\n"):
            print(f"  {sline}")
        (output_dir / "summary.md").write_text(summary_text)

    # Write final stats
    write_stats(output_dir, args.prompt, started, settings, iterations_data)

    print(f"\n  {DIM}Output:{RESET}      {output_dir}")
    print(
        f"  {DIM}Resume:{RESET}      ralph-runner --resume {output_dir} --prompt '...'"
    )
    print(f"  {DIM}{'━' * PANEL_WIDTH}{RESET}")
    print()


def main() -> None:
    """Entry point for the ralph-runner CLI."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        from .display import DIM, RESET

        print(f"\n{DIM}Interrupted.{RESET}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
