---
name: show
description: >
  Display a task's full content — title, frontmatter, source, notes,
  blocked field if any. Use when the user invokes /logbook:show OR
  asks "show me <task>" / "what's in the auth task" / "let me see
  the dashboard task" — they want to inspect a specific task without
  opening the file manually. Read-only, never modifies anything.
disable-model-invocation: true
allowed-tools: Read, Glob, Grep
argument-hint: <task name>
---

# /logbook:show — View a Task

Render a task's full content in a readable format. Read-only.

## Steps

1. **Resolve which task.** Fuzzy-match `$ARGUMENTS` against filenames + titles in **all folders** (queued/active/paused/done/abandoned). Show should reach anywhere. If the match is ambiguous, list candidates and ask.

2. **Read the file.**

3. **Render with light formatting.** Use this layout:

   ```
   📋 <Title>                           [<status>]
   ─────────────────────────────────────────
   File:     <relative path>
   Created:  <YYYY-MM-DD>
   Tags:     <tags or "(none)">
   Source:   <source line>
   Priority: <priority>

   ⏸ Blocked since <date>: <reason>     ← only if Blocked field present

   Notes:
   <Notes content, or "(empty)" if blank>
   ```

   - Use the same `[<status>]` annotation in the title bar so the user can see at a glance what state it's in.
   - If Notes is empty (just whitespace), show `(empty)` rather than blank space — clearer signal.
   - For long Notes (>~500 chars), show the first ~30 lines and append `(<N> more lines — see file)`.

4. **Suggest related actions** as a one-liner footer (only when relevant):

   - If the task is in `queued/`: `Suggest: /logbook:next (start now), /logbook:edit (modify), /logbook:abandon (drop)`
   - If in `active/` and not blocked: `Suggest: /logbook:done (complete), /logbook:edit block on <reason> (mark blocked)`
   - If in `active/` and blocked: `Suggest: /logbook:edit unblock (clear) or /logbook:edit pause`
   - If in `paused/`: `Suggest: /logbook:edit resume (back to active), /logbook:abandon (drop)`
   - If in `done/` or `abandoned/`: no suggestions — terminal state.

## Rules

- **Read-only.** No file writes, moves, or edits.
- **Reach into all folders.** Unlike /logbook:next or /logbook:on-deck (queued only), /show works across the whole `.logbook/` tree.
- **Don't dump the raw file.** Render with the layout above so it's scannable. The point is to be a better experience than `cat .logbook/active/<file>.md`.
- **Truncate long Notes** to keep the response compact.
- **Footer suggestions are optional** — skip if the user just wanted to see the content. Include when the state implies an obvious next action.
