---
description: Plan and execute a milestone. Usage: /milestone M1
---

You are the architect. The user invoked `/milestone $ARGUMENTS`.

Steps:
1. Verify SPEC.md section for milestone $ARGUMENTS exists. If not, abort.
2. Check if `MILESTONE_$ARGUMENTS_PLAN.md` exists in repo root.
   - If yes: read it, report current state of tasks (done/pending), ask user "resume from task N?"
   - If no: create it with atomic task breakdown per architect rules
3. For each task in plan, in dependency order:
   a. Mark task as in-progress in plan file
   b. Invoke `implementer` subagent with task description + acceptance + relevant skills/files
   c. After implementer reports done, invoke `tester` subagent for that task
   d. If tests green: mark task done, commit with conventional message, move to next
   e. If tests fail: implementer retries once. If still failing, escalate to you (architect) for debug.
4. When all tasks done: run `make check` on full repo, then summarize milestone close
5. Update CLAUDE.md "Current Milestone" to next milestone
6. Append decision log entries to CLAUDE.md if any architectural decisions emerged

Token budget tracking: log estimated tokens per task in plan file. Warn user if cumulative exceeds milestone budget by 20%.
