---
name: delete
description: >
  Permanently remove a task file from .logbook/. Use when the user
  invokes /logbook:delete OR says "delete <task>" / "remove <task>" /
  "wipe <task>" / "that was a mistake, get rid of it" — they want
  the file gone, no audit trail. For "decided not to do this," use
  /logbook:abandon instead (preserves history). Always confirms
  before deleting because the operation is destructive.
disable-model-invocation: true
allowed-tools: Read, Glob, Task
argument-hint: <task name>
---

# /logbook:delete — Permanently Remove a Task

Hard-remove a task file and its index row. Always confirms first because there's no undo.

## Steps

1. **Resolve which task.** Fuzzy-match `$ARGUMENTS` against filenames + titles in **all folders** (`queued/`, `active/`, `paused/`, `done/`, `abandoned/`). Delete should reach into any state, including done/abandoned for cleanup of historical noise.

2. **Show the candidate and ask for confirmation.** Always:

   ```
   📋 Will delete:
     <folder>/<filename>
     Title: <title>
     Source: <source line>
     Status: <status>

   This removes the file entirely. There's no undo. For a soft alternative that keeps an audit trail, use /logbook:abandon instead.

   Confirm? (yes / cancel)
   ```

   Wait for confirmation. Interpret loosely: "yes", "y", "delete it", "go ahead", "confirm" → proceed. "no", "cancel", "abort", "wait" → stop with `📋 Cancelled. No changes made.`

3. **On confirmation, delegate to the worker** via Task with `subagent_type="logbook:worker"`. Pass:

   > Delete `.logbook/<folder>/<file>.md` (use `rm`, not `mv`).
   > Remove its row from `.logbook/index.md`.
   > Touch the `Last updated:` line.

4. **Reply with one line:**

   ```
   📋 Deleted: <title>
   ```

## When to use this vs `/logbook:abandon`

| Scenario | Use |
|---|---|
| Task was a typo or accidental capture | `/logbook:delete` |
| Old TodoWrite-pollution leftovers (the v0.2.0 issue, in case any slipped through) | `/logbook:delete` |
| Decided not to do this (real work item, but no longer relevant) | `/logbook:abandon` |
| Done with this task | `/logbook:done` |

Rule of thumb: **if the task represented real intent at any point, use `/abandon`** (preserves the why-not-anymore). **If the task should never have existed, use `/delete`** (no record needed).

## Rules

- **Always confirm.** Never delete without explicit user yes. The cost of one extra prompt is much smaller than the cost of an undo-less deletion.
- **Single file per call.** Bulk deletion is too risky — one task at a time.
- **Reach into ALL folders.** Unlike most other commands, delete should match against `done/` and `abandoned/` too — those are common sources of cleanup work.
- **Never write/delete files yourself** — always delegate to the worker.
- **One-line reply** after confirmation.
