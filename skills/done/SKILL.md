---
name: done
description: >
  Mark an active task complete and move it to done/. Use when the user
  invokes /logbook:done OR says "I'm done with that" / "mark X as
  complete" / "that's finished" / "wrapped <task>" — they want to
  close out an active task without going through TodoWrite. Useful
  for execution tools that don't use TodoWrite, or for explicit
  user-driven completion. With no argument, defaults to the
  currently-active task (if exactly one); otherwise asks which one.
disable-model-invocation: true
allowed-tools: Read, Glob, Task
argument-hint: [task name, optional — defaults to the currently active task]
---

# /logbook:done — Mark Task Complete

Move an active task from `.logbook/active/` to `.logbook/done/` and offer to pull the next from the queue.

## Steps

1. **Resolve which task** to mark done:
   - If `$ARGUMENTS` is non-empty: fuzzy-match against `.logbook/active/` filenames and titles (lowercase + strip punctuation + word-overlap ≥0.5 on smaller). Pick the best match.
   - If `$ARGUMENTS` is empty:
     - Read `.logbook/active/`. If exactly **1 file**, that's the target.
     - If **0 files**, reply `📋 No active tasks. Run /logbook:next to start one from the queue.` and stop.
     - If **>1 file**, list them and ask which one.

2. **Delegate to the worker** via `Task` with `subagent_type="logbook:worker"`. Pass:

   > Move `.logbook/active/<file>.md` to `.logbook/done/<file>.md`.
   > Update the file's `Status:` field to `done`.
   > Update its row in `.logbook/index.md` (status column from `active` to `done`, path prefix from `active/` to `done/`).
   > Touch the `Last updated:` line.

3. **Reply with two lines.** One announcement + one next-step suggestion:

   ```
   📋 Wrapped: <title>
   Run /logbook:next to start the next queued task, or /logbook:status for the dashboard.
   ```

   If the queue is empty, swap the suggestion: `Queue is empty — run /logbook:on-deck to peek when something's there, or /logbook:start <task> to add new work.`

## Rules

- **Single file moved per call.** If the user wants to mark several tasks done at once, they invoke /logbook:done once per task. Don't try to do bulk completion (causes ambiguity around "which next").
- **No content changes during done.** This skill only moves the file and updates Status. It doesn't add a "completed at" timestamp or modify Notes — git history captures completion time.
- **Never write files yourself** — always delegate to the worker subagent.
- **One-line announcement** (plus one-line next-step suggestion). Don't editorialize.
