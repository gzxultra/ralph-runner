---
description: Resume an interrupted ralph-runner session
---

Resume a ralph-runner outer-loop session that was previously interrupted.

If `$ARGUMENTS` contains a directory path, use that. Otherwise, find the most recent run:

```bash
LATEST=$(ls -t ~/.ralph-runner/runs/ | head -1)
RUN_DIR=~/.ralph-runner/runs/$LATEST
```

Read the original task from the progress file, then resume:

```bash
ralph-runner --resume "$RUN_DIR" --prompt "$(head -3 $RUN_DIR/progress.md | grep 'Task:' | sed 's/Task: //')"
```
