---
description: Check status of ralph-runner orchestration runs
---

Check the status of ralph-runner orchestration runs.

If `$ARGUMENTS` contains a specific run directory name, inspect that run. Otherwise, show the latest run.

```bash
# Find the target run
if [ -n "$ARGUMENTS" ] && [ -d ~/.ralph-runner/runs/$ARGUMENTS ]; then
  RUN_DIR=~/.ralph-runner/runs/$ARGUMENTS
else
  LATEST=$(ls -t ~/.ralph-runner/runs/ 2>/dev/null | head -1)
  if [ -z "$LATEST" ]; then
    echo "No ralph-runner runs found in ~/.ralph-runner/runs/"
    exit 0
  fi
  RUN_DIR=~/.ralph-runner/runs/$LATEST
  echo "=== Latest run: $LATEST ==="
fi

echo ""
echo "--- Summary ---"
cat $RUN_DIR/summary.md 2>/dev/null || echo "(no summary yet)"
echo ""
echo "--- Stats ---"
cat $RUN_DIR/stats.json 2>/dev/null | python3 -m json.tool | head -40
echo ""
echo "--- Recent runs ---"
ls -lt ~/.ralph-runner/runs/ | head -10
```
