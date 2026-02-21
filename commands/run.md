---
description: Launch a ralph-runner outer-loop orchestration session
---

Launch a ralph-runner outer-loop orchestration session for the following task:

**Task:** $ARGUMENTS

Before running, determine the best configuration:

1. **Detect test framework.** Check if the project has tests by looking for `pytest.ini`, `pyproject.toml` with `[tool.pytest]`, `package.json` with test scripts, `Makefile` with a test target, or a `tests/` directory. If found, add `--verify` with the appropriate command (e.g., `pytest tests/ -x`, `npm test`, `make test`).

2. **Choose iteration count.** For large tasks (refactors, migrations, new features), use the defaults (10–50). For smaller tasks (bug fixes, single-file changes), use `--iterations 3 --max-iterations 10`.

3. **Enable internet** with `--internet` only if the task explicitly requires web access (fetching docs, downloading packages, etc.).

Then run:

```bash
ralph-runner --prompt "$ARGUMENTS" [flags]
```
