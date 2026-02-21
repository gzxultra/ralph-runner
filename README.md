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

Each iteration is a fresh Claude Code session that reads the progress file, continues the work, and updates the file. Between iterations, ralph-runner runs your verification command, tracks token usage and costs, detects timeouts and crashes, and enforces minimum iteration counts before accepting completion.

## Installation

### As a CLI tool

```bash
pip install ralph-runner
```

Or install from source:

```bash
git clone https://github.com/gzxultra/ralph-runner.git
cd ralph-runner
pip install -e .
```

### As a Claude Code plugin

Install directly from the repo — no pip needed for plugin use:

```bash
# Add the marketplace
/plugin marketplace add gzxultra/ralph-runner

# Install the plugin
/plugin install ralph-runner@ralph-runner
```

Or install from a local clone:

```bash
claude plugin add ./ralph-runner
# or
claude --plugin-dir ./ralph-runner
```

### Prerequisites

- **Python 3.11+**
- **Claude Code CLI** (`claude`) installed and authenticated — see [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code)

## Quick Start

### From the command line

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

### From within Claude Code (plugin)

```
/ralph-runner:run Refactor the auth module to use JWT tokens
/ralph-runner:run --verify "pytest" Fix the failing tests
/ralph-runner:status
/ralph-runner:resume
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

The verification trend is displayed as a convergence sequence:

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

ralph-runner ships as a **Claude Code plugin**, so you can invoke it directly from within Claude Code sessions. The repository doubles as both a pip-installable Python package and a Claude Code plugin marketplace.

### Install from the marketplace

```bash
# Add the marketplace (one-time)
/plugin marketplace add gzxultra/ralph-runner

# Install the plugin
/plugin install ralph-runner@ralph-runner

# Update to latest version
/plugin marketplace update
```

### Install from local clone

```bash
# Option A: add as a plugin
claude plugin add ./ralph-runner

# Option B: load for a single session
claude --plugin-dir ./ralph-runner
```

### Available skills and commands

| Command | Description |
|---------|-------------|
| `/ralph-runner:run <task>` | Launch an outer-loop orchestration session |
| `/ralph-runner:status` | Check progress, costs, and results of runs |
| `/ralph-runner:resume` | Resume an interrupted run |

### Example plugin usage

```
> /ralph-runner:run Fix all failing tests and get to 100% pass rate
> /ralph-runner:run --verify "pytest" Refactor the database layer
> /ralph-runner:status
> /ralph-runner:resume
```

## Architecture

```
ralph-runner/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest (name, version, metadata)
│   └── marketplace.json     # Marketplace catalog for distribution
├── skills/
│   ├── run/SKILL.md         # Skill: launch an orchestration session
│   └── status/SKILL.md      # Skill: inspect run progress and costs
├── commands/
│   ├── run.md               # Slash command: /ralph-runner:run
│   ├── status.md            # Slash command: /ralph-runner:status
│   └── resume.md            # Slash command: /ralph-runner:resume
├── settings.json            # Default permission grants
├── src/ralph_runner/
│   ├── cli.py               # CLI entry point and main orchestration loop
│   ├── runner.py            # Core iteration engine — spawns and monitors Claude
│   ├── prompt.py            # Prompt construction with progress injection
│   ├── verify.py            # Verification command runner and trend tracking
│   ├── stats.py             # Stats, progress files, and summary generation
│   ├── display.py           # Terminal colors, spinners, formatting
│   ├── tools.py             # Tool-call description formatting
│   └── models.py            # Data classes (IterationResult)
├── tests/
│   └── test_basics.py       # Unit tests
├── pyproject.toml            # Python package configuration
├── LICENSE                   # MIT
└── README.md
```

## License

MIT — see [LICENSE](LICENSE).
