---
name: status
description: >
  Show the logbook dashboard — counts of tasks per state, active task
  state, blocked tasks, inbox size, the next-up queue, and any
  resumption hint from the previous session. Use when the user invokes
  /logbook:status OR asks general questions about backlog state ("what's
  going on", "what am I working on", "what's in the backlog", "what was
  I doing", "any blockers"). Read-only — never modifies files. This is
  the auto-trigger entry point for state queries; other entry points
  (jot, triage, start, next, on-deck, capture) are manual-only.
allowed-tools: Read, Grep, Glob
---

# /logbook:status — Logbook Dashboard

Render a quick overview of the logbook state. Pure read.

## Steps

1. **If `.logbook/` doesn't exist**, reply: `📋 No logbook in this project yet. Run /logbook:jot <note> to create one, or /logbook:start <task> to begin tracked work.` and stop.
2. **Read `.logbook/.last-session-state` if it exists** — JSON snapshot from the PreCompact hook. If the timestamp is recent (within ~1 day) and lists active tasks, mention them: `📋 Last session was compacted while working on: <task>. Pick up?` (a one-liner before the dashboard).
3. Read `.logbook/index.md` and count tasks per status.
4. Read `.logbook/inbox.md` and count untriaged items (lines starting with `- `).
5. For each task in `.logbook/active/`, read the file:
   - Capture its title and tags.
   - Check for a `Blocked:` field. If present, capture the date and reason for the dashboard annotation.
6. For `.logbook/done/`, count files modified in the last 7 days for the "this week" stat.
7. List up to the top 5 tasks in `.logbook/queued/`, sorted by date desc.
8. Render the dashboard.

## Output template

```
📋 Logbook Status
─────────────────────────
Inbox:      {N} items (untriaged)
Queued:     {N} tasks
Active:     {N} task(s){blocked annotation if any}
Paused:     {N} task(s)
Done:       {N} tasks ({K} this week)
Abandoned:  {N} tasks

Active tasks:
  → {Title} ({tags})
    ⏸ Blocked since {YYYY-MM-DD HH:MM}: {reason}        ← only if Blocked field present

Queued (next up):
  1. {Title} ({tags})
  2. {Title} ({tags})
```

**Active line annotation:** if any active task has a `Blocked:` field, add ` ({K} blocked, awaiting input)` after the count. Example: `Active:     2 tasks (1 blocked, awaiting input)`.

**Blocked sub-line:** for each active task with a `Blocked:` field, render an indented line with `⏸`, the block date, and the reason (truncate to ~100 chars with `…` if needed). Goes immediately under the task's title line.

**Stale-block hint:** if any `Blocked:` field is older than 7 days, append after the listing:
```
⚠️  {N} task(s) blocked >7 days — consider moving to paused/
```

If a section would be empty, omit it rather than printing an empty header. So if there are zero active tasks, drop the `Active tasks:` block entirely.

## Optional tag filter

If the user passes a tag like `/logbook:status #frontend`, filter the *displayed task lists* to ones with that tag. The top counts block stays global. If tag filtering is awkward, do best-effort grep across task files and note: `(filtered to #frontend)` next to the section headers.

## Index sync warning

If `.logbook/index.md` is out of sync with the filesystem (file in `active/` not in index, or row references a file that doesn't exist), append:

```
⚠️  index.md is out of sync — N file(s) missing from index, M ghost row(s)
```

Don't try to fix it here — that's a future `/logbook:repair` command. Just surface the drift.

## Rules

- **Read-only.** No file writes, no moves, no edits.
- **Don't triage, don't suggest changes** — just report what's there. The user runs `/logbook:triage`, `/logbook:next`, etc. when they want to act.
- **Keep output compact.** The user wants a glance, not a wall of text.
- **Don't reference `done/total steps`** for active tasks — task files in v0.2.0+ don't have structured Plan checklists. Show title + tags only.
