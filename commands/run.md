---
description: Launch a ralph-runner outer-loop session
---

Launch a ralph-runner outer-loop orchestration session for the following task:

**Task:** $ARGUMENTS

Determine the best flags based on the task:
1. If the project has tests, add `--verify` with the appropriate test command
2. For large tasks, use default iterations (10). For smaller tasks, use `--iterations 3 --max-iterations 10`
3. Use `--internet` if the task requires web access

Then run:

```bash
ralph-runner --prompt "$ARGUMENTS" [flags]
```
