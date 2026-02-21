"""Core iteration runner — spawns and monitors a single Claude Code session."""

from __future__ import annotations

import asyncio
import json
import time

from pathlib import Path

from .display import (
    BLUE,
    CLEAR_LINE,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET,
    SPINNER_FRAMES,
    debug_log,
    draw_box_line,
    fmt_duration,
    log,
)
from .models import IterationResult
from .tools import tool_description


async def run_iteration(
    prompt: str,
    iteration: int,
    output_dir: Path,
    timeout: float,
    idle_timeout: float,
    mode: str,
    internet: bool,
    debug: bool,
    cumulative_cost: float,
    model: str = "sonnet",
) -> IterationResult:
    """Run a single Claude Code iteration and return the result."""
    result = IterationResult()
    start_time = time.monotonic()

    cmd = [
        "claude",
        "-p",
        "--verbose",
        "--model", model,
        "--output-format", "stream-json",
    ]
    if mode == "afk":
        cmd.extend(["--permission-mode", "bypassPermissions"])
    if internet:
        cmd.append("--internet")

    debug_log(f"Spawning: {' '.join(cmd)}", debug)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stderr_lines: list[str] = []

    async def drain_stderr() -> None:
        assert proc.stderr is not None
        async for raw in proc.stderr:
            line = raw.decode("utf-8", errors="replace").rstrip()
            if line:
                stderr_lines.append(line)
                debug_log(f"[stderr] {line}", debug)

    stderr_task = asyncio.create_task(drain_stderr())

    try:
        assert proc.stdin is not None
        proc.stdin.write(prompt.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()
    except (BrokenPipeError, ConnectionResetError, OSError) as e:
        log(f"{RED}Failed to write prompt: {e}{RESET}")
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        stderr_task.cancel()
        result.exit_code = proc.returncode
        result.duration = time.monotonic() - start_time
        return result

    raw_log = output_dir / f"iter-{iteration}.jsonl"
    result_file = output_dir / f"iter-{iteration}.txt"
    streamed_text_parts: list[str] = []
    result_text = ""
    first_output = True
    last_activity = time.monotonic()
    idle_killed = False
    hard_killed = False
    spinner_stop = False
    active_tools: dict[str, str] = {}  # tool_use_id -> description

    # Spinner during MCP init, then heartbeat during processing
    async def spinner() -> None:
        frame = 0
        last_heartbeat = 0
        while not spinner_stop:
            elapsed = time.monotonic() - start_time
            char = SPINNER_FRAMES[frame % len(SPINNER_FRAMES)]
            if first_output:
                status = (
                    f"  {CYAN}{char}{RESET}  {DIM}Connecting to Claude...{RESET} "
                    f"{DIM}{fmt_duration(elapsed)}{RESET}  "
                    f"{DIM}(${cumulative_cost:.2f} spent){RESET}"
                )
            else:
                tool_names = list(active_tools.values())
                if tool_names:
                    display_tools = tool_names[:2]
                    extra = len(tool_names) - 2
                    tool_str = ", ".join(display_tools)
                    if extra > 0:
                        tool_str += f" +{extra} more"
                    status = (
                        f"  {CYAN}{char}{RESET}  {DIM}{fmt_duration(elapsed)}{RESET}  "
                        f"{BLUE}▶{RESET} {DIM}{tool_str}{RESET}"
                    )
                else:
                    status = (
                        f"  {CYAN}{char}{RESET}  {DIM}{fmt_duration(elapsed)}{RESET}  "
                        f"{DIM}processing...{RESET}"
                    )

                mins = int(elapsed)
                if mins > 0 and mins % 30 == 0 and mins != last_heartbeat:
                    last_heartbeat = mins
                    print(CLEAR_LINE, end="")
                    ts = time.strftime("%H:%M:%S")
                    n_tools = len(tool_names)
                    if n_tools > 0:
                        print(
                            f"  {DIM}{ts}  ⏳ {fmt_duration(elapsed)} elapsed, "
                            f"{n_tools} tool{'s' if n_tools != 1 else ''} running...{RESET}",
                            flush=True,
                        )
                    else:
                        print(
                            f"  {DIM}{ts}  ⏳ {fmt_duration(elapsed)} elapsed, processing...{RESET}",
                            flush=True,
                        )

            print(f"{CLEAR_LINE}{status}", end="", flush=True)
            frame += 1
            await asyncio.sleep(0.1)

    spinner_task = asyncio.create_task(spinner())

    async def idle_watchdog() -> None:
        nonlocal idle_killed
        while proc.returncode is None:
            await asyncio.sleep(5)
            elapsed_idle = time.monotonic() - last_activity
            if elapsed_idle > idle_timeout:
                idle_killed = True
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                return

    watchdog_task = asyncio.create_task(idle_watchdog())

    try:
        with open(raw_log, "w") as log_f:
            assert proc.stdout is not None
            buf = b""
            while True:
                remaining = timeout - (time.monotonic() - start_time)
                if remaining <= 0:
                    hard_killed = True
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                    break

                try:
                    chunk = await asyncio.wait_for(
                        proc.stdout.read(65536),
                        timeout=min(remaining, idle_timeout + 10),
                    )
                except asyncio.TimeoutError:
                    continue

                if not chunk:
                    break

                last_activity = time.monotonic()
                buf += chunk

                while b"\n" in buf:
                    raw_line, buf = buf.split(b"\n", 1)
                    line_str = raw_line.decode("utf-8", errors="replace").strip()

                    if not line_str:
                        continue

                    log_f.write(line_str + "\n")
                    log_f.flush()

                    if first_output:
                        spinner_stop = True
                        spinner_task.cancel()
                        try:
                            await spinner_task
                        except asyncio.CancelledError:
                            pass
                        mcp_init_time = time.monotonic() - start_time
                        print(
                            f"{CLEAR_LINE}  {GREEN}●{RESET}  {DIM}Connected{RESET} "
                            f"{DIM}({fmt_duration(mcp_init_time)} init){RESET}"
                        )
                        first_output = False

                    try:
                        obj = json.loads(line_str)
                    except json.JSONDecodeError:
                        debug_log(f"Non-JSON line: {line_str[:100]}", debug)
                        continue

                    msg_type = obj.get("type", "")

                    if msg_type == "assistant":
                        content = obj.get("message", {}).get("content", [])
                        for block in content:
                            btype = block.get("type", "")
                            if btype == "text":
                                text = block.get("text", "")
                                if text:
                                    streamed_text_parts.append(text)
                                    print(CLEAR_LINE, end="")
                                    for tline in text.split("\n"):
                                        print(draw_box_line(tline), flush=True)

                            elif btype == "tool_use":
                                tool_name = block.get("name", "?")
                                tool_id = block.get("id", "")
                                tool_input = block.get("input", {})
                                desc = tool_description(tool_name, tool_input)
                                active_tools[tool_id] = desc
                                print(CLEAR_LINE, end="")
                                ts = time.strftime("%H:%M:%S")
                                print(
                                    f"  {DIM}{ts}{RESET}  {CYAN}→{RESET} {DIM}{desc}{RESET}",
                                    flush=True,
                                )

                            elif btype == "tool_result":
                                tool_id = block.get("tool_use_id", "")
                                if tool_id in active_tools:
                                    del active_tools[tool_id]

                    elif msg_type == "result":
                        result_text = obj.get("result", "")
                        result.cost_usd = obj.get("total_cost_usd", 0.0) or 0.0
                        result.num_turns = obj.get("num_turns", 0)
                        model_usage = obj.get("modelUsage", {})
                        result.model_usage = model_usage
                        for model_data in model_usage.values():
                            result.input_tokens += model_data.get("inputTokens", 0)
                            result.output_tokens += model_data.get("outputTokens", 0)
                            result.cache_read_tokens += model_data.get(
                                "cacheReadInputTokens", 0
                            )
                            result.cache_write_tokens += model_data.get(
                                "cacheCreationInputTokens", 0
                            )

    except Exception as e:
        spinner_stop = True
        spinner_task.cancel()
        log(f"{RED}Error: {e}{RESET}")
    finally:
        spinner_stop = True
        watchdog_task.cancel()
        stderr_task.cancel()
        spinner_task.cancel()
        for task in [watchdog_task, stderr_task, spinner_task]:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    try:
        await asyncio.wait_for(proc.wait(), timeout=10)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()

    full_text = "".join(streamed_text_parts)
    result.text = full_text if full_text else result_text
    result.duration = time.monotonic() - start_time
    result.timed_out = hard_killed
    result.idle_timed_out = idle_killed
    result.exit_code = proc.returncode

    if proc.returncode != 0 and stderr_lines:
        log(f"{RED}stderr:{RESET}")
        for sline in stderr_lines[-10:]:
            log(f"  {DIM}{sline}{RESET}")

    result_file.write_text(result.text)
    return result
