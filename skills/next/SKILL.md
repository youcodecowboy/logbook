---
name: next
description: >
  Pick up the highest-priority queued task and start working on it.
  Use when the user invokes /logbook:next or says "I'm done, what's
  next" / "give me the next task" / "pull the next one" — they want
  to work through the backlog sequentially. Sorts queued/ by priority
  desc, then date asc within same priority. Moves the picked task
  from queued/ to active/. To peek at what's coming without starting
  it, use /logbook:on-deck instead.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Task
---

# /logbook:next — Pull from Queue

Pick the highest-priority queued task and move it to active/.

## Steps

1. **Read `.logbook/queued/`.** If empty, reply: `📋 Queue is empty. Run /logbook:triage if you have inbox items, or /logbook:start <task> to add new work.` and stop.

2. **Sort the queued tasks** by:
   - Priority desc: `high` → `medium` → `low`. Tasks without a Priority field default to `medium`.
   - Date asc within same priority: oldest first (older items have been waiting longer).

3. **Pick the top.** If there are blocking-priority ties (multiple `high` from the same date), pick the alphabetically-first by title — deterministic so the same `/logbook:next` call from two sessions can't pick different tasks.

4. **Delegate to the worker subagent** via Task tool with `subagent_type="logbook:worker"`. Pass:

   > Move `.logbook/queued/<file>.md` to `.logbook/active/<file>.md`. Update its `Status:` field to `active`. Update its row in `.logbook/index.md` (status column from `queued` to `active`, path prefix from `queued/` to `active/`). Touch the `Last updated:` line.

5. **Reply concisely:** `📋 Started: <title>` — and one extra line if there's useful context:
   - If the task has a `Source:` from plan mode, mention it: `(from plan mode capture)`
   - If the task has tags, show them: `Tags: #frontend #ux`
   - If the task has notes, mention they exist: `(see ## Notes for context)`

   Keep it under 3 lines total. The user (or execution tool) reads the file from there.

## Rules

- **One file moved per call.** Don't pull multiple tasks. The user can call `/logbook:next` again when they finish.
- **Deterministic selection.** Same queue state = same pick, regardless of session. Important for multi-session/multi-developer scenarios.
- **No execution orchestration.** You move the file, announce, stop. The actual work is somebody else's job.
- **Never write files yourself** — always delegate to the worker subagent.
