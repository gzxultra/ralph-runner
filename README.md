<p align="center">
  <img src="assets/banner.png" alt="ralph-runner banner" width="700">
</p>

<p align="center">
  <strong>Outer-loop orchestrator for Claude Code</strong><br>
  <em>Run iterative, self-improving coding sessions with automatic progress tracking, verification, and cost reporting.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/ralph-runner/"><img src="https://img.shields.io/pypi/v/ralph-runner?color=58a6ff&style=flat-square" alt="PyPI"></a>
  <a href="https://pypi.org/project/ralph-runner/"><img src="https://img.shields.io/pypi/pyversions/ralph-runner?color=3fb950&style=flat-square" alt="Python"></a>
  <a href="https://github.com/gzxultra/ralph-runner/blob/main/LICENSE"><img src="https://img.shields.io/github/license/gzxultra/ralph-runner?color=8b949e&style=flat-square" alt="License"></a>
  <a href="https://github.com/gzxultra/ralph-runner"><img src="https://img.shields.io/github/stars/gzxultra/ralph-runner?color=e3b341&style=flat-square" alt="Stars"></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-claude-code-plugin">Claude Code Plugin</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-how-it-works">How It Works</a>
</p>

---

## 🎯 What is ralph-runner?

ralph-runner spawns repeated Claude Code sessions in a loop, feeding each one the accumulated progress from prior iterations. Claude works on your task, writes progress notes, and ralph-runner verifies the result, tracks costs, and decides whether to continue or stop.

The result: **autonomous, multi-hour coding runs that converge on a solution.**

> **Think of it as a `while` loop around Claude Code** — each iteration picks up where the last left off, guided by a shared progress file and optional verification commands.

---

## ⚡ Quick Start

```bash
pip install ralph-runner

# Basic run
ralph-runner --prompt "Refactor the auth module to use JWT tokens"

# With verification (recommended)
ralph-runner --prompt "Fix all failing tests" --verify "pytest tests/ -x"

# Human-in-the-loop
ralph-runner --prompt "Redesign the API layer" --mode hitl --verify "make test"
```

---

## 📦 Installation

### From PyPI

```bash
pip install ralph-runner
```

### From source

```bash
git clone https://github.com/gzxultra/ralph-runner.git
cd ralph-runner
pip install -e .
```

### Prerequisites

| Requirement | Details |
|:---|:---|
| **Python** | 3.11 or later |
| **Claude Code CLI** | `claude` installed and authenticated ([docs](https://docs.anthropic.com/en/docs/claude-code)) |

---

## 🔌 Claude Code Plugin

ralph-runner ships as a **Claude Code plugin** — the repo itself is a plugin marketplace. Install it directly from within Claude Code:

```bash
# Add the marketplace (one-time)
/plugin marketplace add gzxultra/ralph-runner

# Install the plugin
/plugin install ralph-runner@ralph-runner
```

Or load from a local clone:

```bash
claude plugin add ./ralph-runner
# or for a single session:
claude --plugin-dir ./ralph-runner
```

### Plugin Commands

| Command | Description |
|:---|:---|
| `/ralph-runner:run <task>` | Launch an outer-loop orchestration session |
| `/ralph-runner:status` | Check progress, costs, and results of runs |
| `/ralph-runner:resume` | Resume an interrupted run |

```
> /ralph-runner:run Fix all failing tests and get to 100% pass rate
> /ralph-runner:run --verify "pytest" Refactor the database layer
> /ralph-runner:status
```

---

## 🚀 Usage

```
ralph-runner --prompt PROMPT [OPTIONS]
```

### Options

| Flag | Default | Description |
|:---|:---|:---|
| `--prompt TEXT` | _(required)_ | The task description for Claude |
| `--iterations N` | `10` | Minimum iterations before completion is accepted |
| `--max-iterations N` | `50` | Hard stop after N iterations |
| `--verify CMD` | _(none)_ | Shell command to run after each iteration (exit 0 = pass) |
| `--mode {afk,hitl}` | `afk` | `afk` = autonomous · `hitl` = pause between iterations |
| `--model NAME` | `sonnet` | Claude model to use |
| `--timeout SECS` | `900` | Hard timeout per iteration |
| `--idle-timeout SECS` | `120` | Kill iteration if no output for this long |
| `--internet` | off | Enable web access for Claude sessions |
| `--plan / --no-plan` | on | Create a plan.md in the first iteration |
| `--resume DIR` | _(none)_ | Resume a previous run from its output directory |
| `--debug` | off | Save prompts and enable verbose logging |

### Modes

<table>
<tr>
<td width="50%">

**🤖 AFK Mode** _(default)_

Fully autonomous. Claude runs with `bypassPermissions` — no confirmation prompts. Ideal for overnight or background runs.

```bash
ralph-runner \
  --prompt "Migrate the DB schema" \
  --mode afk
```

</td>
<td width="50%">

**👤 HITL Mode**

Pauses after each iteration for review. Press Enter to continue or `q` to quit.

```bash
ralph-runner \
  --prompt "Redesign the dashboard" \
  --mode hitl
```

</td>
</tr>
</table>

### Verification

The `--verify` flag runs a command after each iteration. Exit 0 = pass, anything else = fail. ralph-runner tracks trends and blocks completion on failure.

```bash
# Single check
ralph-runner --prompt "Fix type errors" --verify "mypy src/"

# Chained checks
ralph-runner --prompt "Clean up codebase" \
  --verify "ruff check src/ && mypy src/ && pytest tests/"
```

Convergence is displayed as a trend sequence:

```
Verify: ✓✓✗✓✓  (4/5 passed, converging)
```

---

## 🔄 How It Works

```
                        ┌─────────────────────┐
                        │    ralph-runner      │
                        │    (outer loop)      │
                        └──────────┬──────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
              ▼                    ▼                     ▼
       ┌─────────────┐    ┌─────────────┐       ┌─────────────┐
       │  Iteration 1 │    │  Iteration 2 │  ...  │  Iteration N │
       │  Claude Code  │    │  Claude Code  │       │  Claude Code  │
       └──────┬───────┘    └──────┬───────┘       └──────┬───────┘
              │                    │                      │
              ▼                    ▼                      ▼
       ┌──────────────────────────────────────────────────────┐
       │                   progress.md                         │
       │           (shared memory across iterations)           │
       └──────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
       ┌──────────────────────────────────────────────────────┐
       │              verify command (optional)                │
       │              e.g. pytest, mypy, make test             │
       └──────────────────────────────────────────────────────┘
```

Each iteration is a **fresh Claude Code session** that:

1. Reads the accumulated `progress.md` from all prior iterations
2. Continues the work from where the last iteration left off
3. Updates `progress.md` with what it accomplished
4. Emits `###RALPH_COMPLETE###` if it believes the task is done

Between iterations, ralph-runner:

- Runs your `--verify` command and records pass/fail
- Tracks token usage and costs per iteration
- Detects timeouts, crashes, and idle sessions
- Enforces minimum iteration counts before accepting completion

---

## 📁 Output

All run artifacts are saved to `~/.ralph-runner/runs/<timestamp>/`:

| File | Description |
|:---|:---|
| `progress.md` | Cumulative progress notes from all iterations |
| `plan.md` | Task plan created in the first iteration |
| `stats.json` | Machine-readable stats — costs, tokens, timing |
| `summary.md` | LLM-generated summary of accomplishments |
| `iter-N.jsonl` | Raw Claude stream output for iteration N |
| `iter-N.txt` | Claude's text output for iteration N |

### Resuming interrupted runs

```bash
ralph-runner --resume ~/.ralph-runner/runs/20260220-143000-fix-auth/ \
  --prompt "Fix the auth module"
```

---

## 🏗️ Project Structure

```
ralph-runner/
├── .claude-plugin/
│   ├── plugin.json            # Plugin manifest
│   └── marketplace.json       # Marketplace catalog
├── skills/
│   ├── run/SKILL.md           # Skill: launch orchestration
│   └── status/SKILL.md        # Skill: inspect run progress
├── commands/
│   ├── run.md                 # /ralph-runner:run
│   ├── status.md              # /ralph-runner:status
│   └── resume.md              # /ralph-runner:resume
├── settings.json              # Default permission grants
├── src/ralph_runner/
│   ├── cli.py                 # CLI entry point
│   ├── runner.py              # Core iteration engine
│   ├── prompt.py              # Prompt construction
│   ├── verify.py              # Verification runner
│   ├── stats.py               # Stats & progress tracking
│   ├── display.py             # Terminal formatting
│   ├── tools.py               # Tool-call formatting
│   └── models.py              # Data classes
├── tests/
├── pyproject.toml
├── LICENSE                    # MIT
└── README.md
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  <sub>Built for developers who want Claude to keep going until the job is done.</sub>
</p>
