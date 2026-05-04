---
description: Run full check then commit and push current changes. Usage: /ship "commit message"
---

Run sequentially:
1. `make check` (must pass; if fails, abort with clear error report)
2. `git add -A`
3. `git status` (show user what will be committed)
4. `git commit -m "$ARGUMENTS"` (use conventional commit format; if message doesn't start with feat/fix/refactor/test/docs/chore, prepend appropriate prefix based on changed files)
5. `git push` to current branch

Do not invoke any subagent. This is a deterministic command.
