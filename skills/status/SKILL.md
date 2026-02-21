---
name: status
description: Check the status of ralph-runner runs. Use to inspect progress, costs, and results of current or past outer-loop orchestration sessions.
---

# Ralph Runner — Check Run Status

Inspect the progress and results of ralph-runner orchestration runs.

## List Recent Runs

```bash
ls -lt ~/.ralph-runner/runs/ | head -20
```

## Check a Specific Run

Read the progress file to see what was accomplished:

```bash
cat ~/.ralph-runner/runs/<run-dir>/progress.md
```

Read the stats for cost and token usage:

```bash
cat ~/.ralph-runner/runs/<run-dir>/stats.json | python3 -m json.tool
```

Read the summary:

```bash
cat ~/.ralph-runner/runs/<run-dir>/summary.md
```

## Resume a Run

If a run was interrupted or needs more iterations:

```bash
ralph-runner --resume ~/.ralph-runner/runs/<run-dir>/ --prompt "Continue the task"
```

## Key Files

| File | What It Contains |
|------|-----------------|
| `progress.md` | Cumulative notes from all iterations |
| `plan.md` | Task plan with phase checkboxes |
| `stats.json` | Per-iteration costs, tokens, timing, verify results |
| `summary.md` | LLM-generated summary of accomplishments |
| `iter-N.txt` | Raw text output from iteration N |
| `iter-N.jsonl` | Full JSON stream from iteration N |
