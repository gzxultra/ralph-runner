# ralph-runner

**Outer-loop orchestrator for Claude Code** — run iterative, self-improving coding sessions with automatic progress tracking, verification, and cost reporting.

ralph-runner spawns repeated Claude Code sessions in a loop, feeding each one the accumulated progress from prior iterations. Claude works on your task, writes progress notes, and ralph-runner verifies the result, tracks costs, and decides whether to continue or stop. The result is autonomous, multi-hour coding runs that converge on a solution.

## How It Works

```
┌─────────────────────────────────────────────────┐
│                  ralph-runner                    │
│                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │ Iter 1   │──▶│ Iter 2   │──▶│ Iter N   │    │
│  │ Claude   │   │ Claude   │   │ Claude   │    │
│  │ Session  │   │ Session  │   │ Session  │    │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘    │
│       │              │              │           │
│       ▼              ▼              ▼           │
│  ┌──────────────────────────────────────────┐   │
│  │            progress.md                    │   │
│  │  (shared memory across iterations)        │   │
│  └──────────────────────────────────────────┘   │
│       │              │              │           │
│       ▼              ▼              ▼           │
│  ┌──────────────────────────────────────────┐   │
│  │         verify command (optional)         │   │
│  │         e.g. make test, pytest            │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

Each iteration is a fresh Claude Code session that:

1. Reads the progress file to understand what was done before
2. Continues the work from where the last iteration left off
3. Updates the progress file with what it accomplished
4. Optionally signals completion when the task is done

Between iterations, ralph-runner:

- Runs your verification command (tests, linters, etc.)
- Tracks token usage, costs, and timing per iteration
- Detects timeouts and crashes, injecting error context into the next prompt
- Enforces minimum iteration counts before accepting completion

## Installation

```bash
pip install ralph-runner
```

Or install from source:

```bash
git clone https://github.com/root/ralph-runner.git
cd ralph-runner
pip install -e .
```

### Prerequisites

- **Python 3.11+**
- **Claude Code CLI** (`claude`) installed and authenticated — see [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code)

## Quick Start

```bash
# Basic run — 10 iterations on a task
ralph-runner --prompt "Refactor the auth module to use JWT tokens"

# With verification
ralph-runner --prompt "Fix the failing tests in src/api/" \
  --verify "pytest tests/ -x"

# Shorter run with internet access
ralph-runner --prompt "Add rate limiting to the API" \
  --iterations 5 --max-iterations 15 --internet
```

## Usage

```
ralph-runner --prompt PROMPT [OPTIONS]
```

### Required

| Flag | Description |
|------|-------------|
| `--prompt TEXT` | The task description for Claude to work on |

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--iterations N` | `10` | Minimum iterations before completion is accepted |
| `--max-iterations N` | `50` | Hard stop after this many iterations |
| `--verify CMD` | _(none)_ | Shell command to run after each iteration (exit 0 = pass) |
| `--mode {afk,hitl}` | `afk` | `afk` = fully autonomous, `hitl` = pause between iterations |
| `--model NAME` | `sonnet` | Claude model to use |
| `--timeout SECS` | `900` | Hard timeout per iteration (15 min) |
| `--idle-timeout SECS` | `120` | Kill iteration if no output for this long |
| `--internet` | off | Enable web access for Claude sessions |
| `--plan / --no-plan` | `--plan` | Create a plan.md file in the first iteration |
| `--resume DIR` | _(none)_ | Resume a previous run from its output directory |
| `--debug` | off | Save prompts and enable verbose stderr logging |

## Modes

### AFK Mode (default)

Fully autonomous. Claude runs with `bypassPermissions` — no confirmation prompts. Ideal for overnight or background runs on trusted codebases.

```bash
ralph-runner --prompt "Migrate the database schema to v2" --mode afk
```

### HITL Mode (Human-in-the-Loop)

Pauses after each iteration so you can review progress before continuing. Press Enter to continue or `q` to quit.

```bash
ralph-runner --prompt "Redesign the dashboard layout" --mode hitl
```

## Verification

The `--verify` flag runs a command after each iteration. If it exits 0, the iteration passes; otherwise it fails. ralph-runner tracks pass/fail trends and blocks completion if verification fails.

```bash
# Run tests
ralph-runner --prompt "Fix all type errors" --verify "mypy src/"

# Run a test suite
ralph-runner --prompt "Implement the search feature" --verify "pytest tests/test_search.py"

# Chain multiple checks
ralph-runner --prompt "Clean up the codebase" \
  --verify "ruff check src/ && mypy src/ && pytest tests/"
```

The verification trend is displayed as a sequence:

```
✓✓✗✓✓  (4/5 passed, converging)
```

## Output

All run artifacts are saved to `~/.ralph-runner/runs/<timestamp>-<prefix>/`:

| File | Description |
|------|-------------|
| `progress.md` | Cumulative progress notes from all iterations |
| `plan.md` | Task plan created in the first iteration |
| `stats.json` | Machine-readable stats (costs, tokens, timing) |
| `summary.md` | LLM-generated summary of accomplishments |
| `iter-N.jsonl` | Raw Claude stream output for iteration N |
| `iter-N.txt` | Claude's text output for iteration N |

### Resuming

If a run is interrupted, resume it:

```bash
ralph-runner --resume ~/.ralph-runner/runs/20260220-143000-fix-auth/ \
  --prompt "Fix the auth module"
```

## Live Display

ralph-runner shows a rich terminal display during execution:

- **Spinner** during Claude connection and MCP initialization
- **Live tool calls** — see what Claude is doing in real time (reading files, running commands, editing code)
- **Heartbeat** every 30 seconds showing elapsed time
- **Iteration summary** with status, duration, cost, and token counts
- **Verification results** with pass/fail trends
- **Final summary** with total cost, token breakdown by model, and an LLM-generated accomplishment summary

## Claude Code Plugin

ralph-runner also ships as a **Claude Code plugin**. This lets you invoke it directly from within Claude Code sessions.

### Install the plugin

```bash
# From a local clone
claude plugin add ./ralph-runner

# Or point to the directory
claude --plugin-dir ./ralph-runner
```

### Use the skills

```
/ralph-runner:run Refactor the auth module to use JWT tokens
/ralph-runner:run --verify "pytest" Fix the failing tests
```

See the `skills/` and `commands/` directories for the full plugin structure.

## Architecture

```
src/ralph_runner/
├── cli.py       # CLI entry point and main orchestration loop
├── runner.py    # Core iteration engine — spawns and monitors Claude
├── prompt.py    # Prompt construction with progress injection
├── verify.py    # Verification command runner and trend tracking
├── stats.py     # Stats, progress files, and summary generation
├── display.py   # Terminal colors, spinners, formatting
├── tools.py     # Tool-call description formatting
└── models.py    # Data classes (IterationResult)
```

## License

MIT — see [LICENSE](LICENSE).
