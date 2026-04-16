---
name: logbook-status
description: >
  Show the logbook dashboard — counts of tasks per state, active task progress,
  inbox size, and the next-up queue. Use when the user invokes /status or asks
  for a backlog overview, "what's going on", "what am I working on", or
  similar. Read-only; never modifies files.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob
---

# /status — Logbook Dashboard

Render a quick overview of the logbook state. Pure read.

## Steps

1. **If `.logbook/` doesn't exist**, reply: `📋 No logbook in this project yet. Run /logbook:jot <note> or start a tracked task and one will be created.` and stop.
2. Read `.logbook/index.md` and count tasks per status.
3. Read `.logbook/inbox.md` and count untriaged items (lines starting with `- `).
4. For each task in `.logbook/active/`, read the file and:
   - Count Plan checkboxes (`- [x]` done vs `- [ ]` total).
   - Check for a `Blocked:` field. If present, capture its date and reason for the dashboard annotation (see Output template below).
5. For `.logbook/done/`, count files modified in the last 7 days for the "this week" stat. (Use `Glob` and check mtime; if that's awkward, fall back to listing names and matching the date prefix.)
6. List up to the top 5 tasks in `.logbook/queued/`, sorted by date desc.
7. Render the dashboard.

## Output template

Use this exact layout:

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
  → {Title} ({tags}) — {done}/{total} steps done
    ⏸ Blocked since {YYYY-MM-DD HH:MM}: {reason}        ← only if Blocked field present

Queued (next up):
  1. {Title} ({tags})
  2. {Title} ({tags})
```

**Active line annotation:** if any active task has a `Blocked:` field, add ` ({K} blocked, awaiting input)` after the count. Example: `Active:     2 tasks (1 blocked, awaiting input)`.

**Blocked task indent:** for each active task with a `Blocked:` field, render a sub-line with the `⏸` icon, the block date, and the block reason (truncate the reason to ~100 chars with `…` if needed). The sub-line goes immediately under the task's normal line.

**Stale-block hint:** if any `Blocked:` field is older than 7 days, append after the listing:
```
⚠️  {N} task(s) blocked >7 days — consider moving to paused/
```

If a section would be empty, omit it rather than printing an empty header. So if there are zero active tasks, drop the `Active tasks:` block entirely.

## Optional tag filter

If the user passes a tag like `/status #frontend`, filter the *displayed task lists* to ones with that tag. The top counts block stays global (so the user still sees overall scale). If tag filtering is awkward to implement against `index.md`, do best-effort grep across task files and note: `(filtered to #frontend)` next to the section headers.

## Index sync warning

If `.logbook/index.md` is out of sync with the filesystem (e.g., a file in `active/` isn't in the index, or the index references a file that doesn't exist), append:

```
⚠️  index.md is out of sync — N file(s) missing from index, M ghost row(s)
```

Don't try to fix it here — that's a future `/logbook repair` command. Just surface the drift.

## Rules

- Read-only. No file writes, no moves, no edits.
- Don't triage, don't suggest changes — just report what's there.
- Keep output compact. The user wants a glance, not a wall of text.
