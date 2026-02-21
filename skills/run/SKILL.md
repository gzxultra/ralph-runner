---
name: run
description: Launch a ralph-runner outer-loop orchestration session. Use when a task requires multiple iterative Claude Code sessions to converge on a solution — large refactors, complex bug fixes, multi-file migrations, or any task that benefits from repeated attempts with progress tracking and verification.
---

# Ralph Runner — Outer-Loop Orchestration

Launch an iterative outer-loop run where ralph-runner spawns repeated Claude Code sessions, each building on the progress of the last.

## When to Use

- Tasks too large for a single Claude session
- Work that benefits from iterative refinement (refactors, migrations, complex features)
- Tasks with a clear verification command (tests, type checks, linters)
- Overnight or background autonomous coding runs

## How to Launch

Run ralph-runner from the project root. The `$ARGUMENTS` text becomes the task prompt.

```bash
ralph-runner --prompt "$ARGUMENTS"
```

### Common Patterns

**With verification (recommended):**
```bash
ralph-runner --prompt "$ARGUMENTS" --verify "pytest tests/ -x"
```

**Quick iteration (fewer rounds):**
```bash
ralph-runner --prompt "$ARGUMENTS" --iterations 3 --max-iterations 10
```

**Human-in-the-loop review:**
```bash
ralph-runner --prompt "$ARGUMENTS" --mode hitl --verify "make test"
```

**With internet access:**
```bash
ralph-runner --prompt "$ARGUMENTS" --internet
```

## Key Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--iterations N` | 10 | Min iterations before completion accepted |
| `--max-iterations N` | 50 | Hard stop |
| `--verify CMD` | none | Verification command (exit 0 = pass) |
| `--mode {afk,hitl}` | afk | Autonomous or human-in-the-loop |
| `--model NAME` | sonnet | Claude model |
| `--timeout SECS` | 900 | Hard timeout per iteration |
| `--idle-timeout SECS` | 120 | Idle timeout per iteration |
| `--internet` | off | Enable web access |
| `--resume DIR` | none | Resume a previous run |

## Output

Runs are saved to `~/.ralph-runner/runs/<timestamp>/` with:
- `progress.md` — cumulative progress across iterations
- `plan.md` — task plan from first iteration
- `stats.json` — costs, tokens, timing
- `summary.md` — LLM-generated summary

## Tips

1. **Always use `--verify`** when possible — it prevents false completion signals
2. **Start with `--mode hitl`** for unfamiliar tasks to review early iterations
3. **Use `--resume`** if a run is interrupted — no work is lost
4. **Check `stats.json`** for cost tracking across long runs
