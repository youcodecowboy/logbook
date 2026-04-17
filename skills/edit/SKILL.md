---
name: edit
description: >
  Edit a task — rename, retag, change priority, set/clear the Blocked
  field, pause/resume, or add notes. Use when the user invokes
  /logbook:edit OR says natural-language change requests like "rename
  X to Y" / "tag X with #foo" / "bump X to high priority" / "block X
  on Z" / "unblock X" / "pause X" / "resume X" / "add a note to X". For
  marking complete or abandoning, use /logbook:done and
  /logbook:abandon (those are dedicated verbs). For removing a file
  entirely, use /logbook:delete.
disable-model-invocation: true
allowed-tools: Read, Glob, Task
argument-hint: <task name> <change> (e.g. "rename to X", "tag with #foo", "pause", "block on Y", "add note: Z")
---

# /logbook:edit — Modify a Task

Apply a single change to a task file. Interprets the user's natural-language change request and dispatches a precise instruction to the worker.

## Steps

1. **Resolve which task.** Fuzzy-match the leading words of `$ARGUMENTS` against filenames + titles in `queued/`, `active/`, `paused/`. If no match, list candidates and ask. If the user also specified a state (e.g., "edit the done auth task"), match in that folder.

2. **Parse the change.** Identify which sub-case the user wants:

   | Pattern | Sub-case |
   |---|---|
   | `rename to "X"` / `rename X` / `change title to X` | **Rename** — change the `# Heading` and the index row Title |
   | `tag with #foo #bar` / `add tag #foo` | **Add tags** to the Tags: field (preserve existing) |
   | `untag #foo` / `remove tag #foo` | **Remove tag** from Tags: field |
   | `priority high` / `bump to high` / `set priority low` | **Change Priority:** field |
   | `block on/waiting for/because <reason>` | **Set Blocked:** field with timestamp + reason |
   | `unblock` / `clear blocked` | **Remove Blocked:** field |
   | `pause` | Move file `active/` → `paused/`, update Status |
   | `resume` | Move file `paused/` → `active/`, update Status |
   | `add note: <text>` / `note <text>` / `append <text>` | **Append to `## Notes`** section |
   | `set source: <text>` | Replace the `Source:` field (rare; use sparingly) |

   If the change is ambiguous (multiple sub-cases match), pick the most specific and proceed; surface what you did so the user can correct.

3. **Delegate to the worker** with one precise instruction (not a free-form description). Use `subagent_type="logbook:worker"`. Examples:

   - **Rename:** "In `.logbook/active/2026-04-16_auth.md`, change line 1 from `# Auth refresh` to `# Fix auth token refresh logic`. Then update the index.md row's Title column from `Auth refresh` to `Fix auth token refresh logic` (escape `|` as `\|`)."

   - **Add tag:** "In `.logbook/active/2026-04-16_auth.md`, change the `Tags:` line by appending ` #high-impact` (preserving existing tags). Then update the index.md row's Tags column to match."

   - **Set priority:** "In `.logbook/active/2026-04-16_auth.md`, change the `Priority:` line value to `high`."

   - **Set Blocked:** "In `.logbook/active/2026-04-16_auth.md`, insert this line directly below the `Status:` line: `Blocked: 2026-04-16 17:42 — waiting on design review from Sam`."

   - **Unblock:** "In `.logbook/active/2026-04-16_auth.md`, remove the `Blocked:` line entirely (the line that starts with `Blocked:`)."

   - **Pause:** "Move `.logbook/active/2026-04-16_auth.md` to `.logbook/paused/2026-04-16_auth.md`. Update the file's Status: field to `paused`. Update the index.md row's status column to `paused` and path prefix to `paused/`."

   - **Resume:** "Move `.logbook/paused/2026-04-16_auth.md` to `.logbook/active/2026-04-16_auth.md`. Update Status: to `active`. Update the index.md row."

   - **Add note:** "In `.logbook/active/2026-04-16_auth.md`, append this content to the `## Notes` section (preserving any existing Notes content): `2026-04-16: Found that mobile web uses uppy v3, RN is on uppy v2.`"

   The instruction always includes the full file path, the specific section/field, and the exact change. Never ask the worker to "edit the task" — that's too vague.

4. **Reply with one line** describing what changed:

   ```
   📋 Edited: <title> — <short description of change>
   ```

   Examples:
   - `📋 Edited: Auth refresh — renamed to "Fix auth token refresh logic"`
   - `📋 Edited: Dashboard — tagged #high-impact`
   - `📋 Edited: Settings — paused (moved to paused/)`
   - `📋 Edited: Settings — blocked: waiting on design review from Sam`

## Rules

- **One change per call.** The user can chain (`/logbook:edit auth pause; tag #blocker`) but the skill processes them as separate dispatches to the worker. Don't try to bundle.
- **Worker gets a precise instruction**, not a free-form change description. The skill is the parser; the worker is the executor.
- **Preserve existing content.** When adding tags, preserve existing tags. When adding notes, preserve existing notes. Never overwrite without a `set` keyword.
- **Never write files yourself** — always delegate to the worker.
- **Surface what you did** so the user can correct ambiguous parses immediately.
