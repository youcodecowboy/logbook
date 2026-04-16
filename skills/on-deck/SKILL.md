---
name: on-deck
description: >
  Show what task is next in the queue without starting it. Use when
  the user invokes /logbook:on-deck or asks "what's on deck" / "what
  would be next" / "show me the queue" / "what's coming up" — they
  want to peek without committing. Read-only, never modifies files.
  To actually start the next task, use /logbook:next.
disable-model-invocation: true
allowed-tools: Read, Glob
---

# /logbook:on-deck — Peek at Queue

Show the next queued task(s) without moving anything. Helps the user decide whether to `/logbook:next` (pull and start), pick a different one, or do something else entirely.

## Steps

1. **If `.logbook/queued/` doesn't exist or is empty**, reply: `📋 Queue is empty. Run /logbook:triage if you have inbox items, or /logbook:start <task> to add new work.` and stop.

2. **Sort queued tasks** the same way `/logbook:next` does:
   - Priority desc: `high` → `medium` → `low` (default medium if missing)
   - Date asc within same priority

3. **Show the top 3** (or fewer if the queue is shorter). For each, show:
   - Title
   - Tags
   - Priority
   - First line of Source (truncated to ~80 chars) for context

4. **Suggest the next action:** `Run /logbook:next to start the top one, or specify another by name.`

## Output format

```
📋 On deck (queue: {N} tasks)

  1. <Title>                           priority: high
     Tags: #frontend #ux
     Source: <truncated source line>

  2. <Title>                           priority: medium
     Tags: #backend
     Source: <truncated source line>

  3. <Title>                           priority: medium
     Tags: #docs
     Source: <truncated source line>

Run /logbook:next to start the top one, or say which task to begin.
```

If the queue has more than 3 tasks, append `(+{N-3} more in queue)` after the listing.

## Rules

- **Read-only.** No file writes, no moves, no edits. Pure peek.
- **Deterministic listing.** Same queue state = same order, regardless of session.
- **Don't suggest plans or implementations.** Just show what's there. The user decides what to start.
- **Keep it tight.** Three tasks max in the listing. The user wants a glance.
