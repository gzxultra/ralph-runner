---
name: status
description: Check the status of ralph-runner runs. Use to inspect progress, costs, and results of current or past outer-loop orchestration sessions.
disable-model-invocation: true
---

# Ralph Runner — Check Run Status

Inspect the progress and results of ralph-runner orchestration runs.

## List Recent Runs

```bash
ls -lt ~/.ralph-runner/runs/ | head -20
```

## Check the Latest Run

```bash
LATEST=$(ls -t ~/.ralph-runner/runs/ | head -1)
echo "=== Run: $LATEST ==="
echo ""
echo "--- Summary ---"
cat ~/.ralph-runner/runs/$LATEST/summary.md 2>/dev/null || echo "(no summary yet)"
echo ""
echo "--- Stats ---"
python3 -c "
import json, sys
try:
    s = json.load(open(sys.argv[1]))
    t = s.get('totals', {})
    print(f\"Iterations: {t.get('iterations', '?')}\")
    print(f\"Duration:   {t.get('duration_s', 0):.0f}s\")
    print(f\"Cost:       \${t.get('cost_usd', 0):.2f}\")
    print(f\"Tokens in:  {t.get('input_tokens', 0):,}\")
    print(f\"Tokens out: {t.get('output_tokens', 0):,}\")
    print(f\"Verify:     {t.get('verify_passes', 0)} pass / {t.get('verify_fails', 0)} fail\")
except Exception as e:
    print(f'(could not read stats: {e})')
" ~/.ralph-runner/runs/$LATEST/stats.json
```

## Check a Specific Run

If `$ARGUMENTS` contains a run directory name, inspect that run:

```bash
cat ~/.ralph-runner/runs/$ARGUMENTS/progress.md
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
