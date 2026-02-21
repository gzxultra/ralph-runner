---
description: Check status of ralph-runner runs
---

Check the status of ralph-runner orchestration runs.

If a specific run directory is provided in `$ARGUMENTS`, inspect that run. Otherwise, list recent runs and show the latest.

```bash
# List recent runs
ls -lt ~/.ralph-runner/runs/ | head -10

# Show latest run's progress
LATEST=$(ls -t ~/.ralph-runner/runs/ | head -1)
echo "=== Latest run: $LATEST ==="
cat ~/.ralph-runner/runs/$LATEST/summary.md 2>/dev/null || echo "No summary yet"
echo ""
echo "=== Stats ==="
cat ~/.ralph-runner/runs/$LATEST/stats.json 2>/dev/null | python3 -m json.tool | head -30
```
