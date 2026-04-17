---
name: abandon
description: >
  Move a task to .logbook/abandoned/ — the "decided not to do this"
  state. Use when the user invokes /logbook:abandon OR says "drop
  X" / "we're not doing this anymore" / "skip <task>" / "abandon
  the auth refresh task" — they want to mark work as deliberately-
  not-done while keeping the audit trail. Different from /delete,
  which removes the file entirely (use that for mistakes). Different
  from /done, which marks work complete.
disable-model-invocation: true
allowed-tools: Read, Glob, Task
argument-hint: <task name> [optional reason — added to Notes as audit trail]
---

# /logbook:abandon — Decided Not to Do

Move a task from any active state (queued/active/paused) to `.logbook/abandoned/`. Optionally annotate with a reason.

## Steps

1. **Resolve which task.** Fuzzy-match `$ARGUMENTS` (or the leading words of it) against filenames + titles in `queued/`, `active/`, `paused/`. If no match, list candidates and ask. If multiple matches, ask which one.

2. **Extract optional reason.** If `$ARGUMENTS` contains text after the task identifier (commonly after a comma, dash, "because", or "—"), that's the reason. Examples:
   - `/logbook:abandon auth-refresh` → no reason
   - `/logbook:abandon auth-refresh — superseded by oauth migration` → reason: "superseded by oauth migration"
   - `/logbook:abandon dashboard, scope changed` → reason: "scope changed"

3. **Delegate to the worker** via Task with `subagent_type="logbook:worker"`. Pass:

   > Move `.logbook/<source-folder>/<file>.md` to `.logbook/abandoned/<file>.md`.
   > Update the file's `Status:` field to `abandoned`.
   > Prepend a one-liner to the `## Notes` section: `Abandoned <YYYY-MM-DD>: <reason if given, else "no reason given">`.
   > Update its row in `.logbook/index.md` (status column to `abandoned`, path prefix to `abandoned/`).
   > Touch the `Last updated:` line.

4. **Reply with one line:**

   ```
   📋 Abandoned: <title>
   ```

   If a reason was given, append it on the same line: `📋 Abandoned: <title> (<reason>)`.

## Why it's different from delete and done

- **Done** = work completed normally. Goes to `done/`.
- **Abandoned** = decided not to do. Goes to `abandoned/`. **Audit trail preserved** in the file (when, why).
- **Delete** = mistake / shouldn't have existed. Removes the file entirely. No record kept.

The `abandoned/` folder is gitignored by default (per `.logbook/.gitignore`), so abandons stay local unless the user changes their gitignore. Effectively this means abandon = soft delete with one-machine recovery, until the next `git clean -dfx` cycle.

## Rules

- **Single task per call.** Bulk abandons are confusing — do them one at a time.
- **Always annotate `## Notes`** with the abandonment date + reason. The whole point of abandoned/ vs delete is the audit trail; if we don't capture context, we lose the reason this state exists.
- **Never write files yourself** — always delegate to the worker.
- **Don't ask for confirmation.** Abandon is reversible (move from abandoned/ back to queued/active/paused with a manual `mv`, or `/logbook:edit` if we add that path later). Confirmation would be friction. Delete is the one that needs confirmation, not abandon.
