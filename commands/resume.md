---
description: Resume an interrupted ralph-runner orchestration session
---

Resume a ralph-runner outer-loop session that was previously interrupted.

If `$ARGUMENTS` contains a run directory path or name, use that. Otherwise, find the most recent run.

```bash
# Find the target run
if [ -n "$ARGUMENTS" ] && [ -d "$ARGUMENTS" ]; then
  RUN_DIR="$ARGUMENTS"
elif [ -n "$ARGUMENTS" ] && [ -d ~/.ralph-runner/runs/$ARGUMENTS ]; then
  RUN_DIR=~/.ralph-runner/runs/$ARGUMENTS
else
  LATEST=$(ls -t ~/.ralph-runner/runs/ 2>/dev/null | head -1)
  if [ -z "$LATEST" ]; then
    echo "No ralph-runner runs found to resume."
    exit 1
  fi
  RUN_DIR=~/.ralph-runner/runs/$LATEST
  echo "Resuming latest run: $LATEST"
fi

# Extract the original task
TASK=$(head -5 $RUN_DIR/progress.md | grep 'Task:' | sed 's/Task: //')
echo "Original task: $TASK"

ralph-runner --resume "$RUN_DIR" --prompt "$TASK"
```
