---
name: tools
description: >
  Show all available logbook commands grouped by purpose, plus the
  background auto-capture mechanisms. Use when the user invokes
  /logbook:tools OR asks "what commands does logbook have" / "show me
  the logbook commands" / "what can logbook do" / "list logbook
  options" / "logbook help" / "logbook cheat sheet" — they want a
  cheat-sheet of the full surface area without reading the README.
  Read-only; never modifies anything.
disable-model-invocation: true
allowed-tools: Read
---

# /logbook:tools — Command Cheat Sheet

Print the full list of logbook commands grouped by purpose, plus the background auto-capture hooks that run without explicit commands. This is the "what can logbook do?" reference.

## Steps

1. Render the cheat sheet below verbatim (with the version pulled dynamically from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` if convenient, else just print "logbook" without a version).
2. Stop. Don't suggest next actions or ask questions — the user is browsing.

## Output (render exactly this)

```
📋 Logbook commands

QUERY — read-only
  /logbook:status              Dashboard: counts per state, active tasks, blocked,
                               queue. Auto-triggers on backlog state questions.
  /logbook:on-deck             Peek at the next 3 queued tasks without starting.
  /logbook:show <task>         View a specific task's full content.
  /logbook:tools               This cheat sheet.

LIFECYCLE — write
  /logbook:start <task>        Start a new tracked task (goes to active/).
  /logbook:next                Pull the highest-priority queued task to active/.
  /logbook:done [task]         Mark active task complete → done/. Defaults to
                               the currently-active task if exactly one.
  /logbook:abandon <task>      Move task to abandoned/ (audit trail preserved).
  /logbook:delete <task>       Permanently remove a task file (asks confirmation).
  /logbook:edit <task> <chg>   Modify a task — rename, retag, change priority,
                               set/clear Blocked, pause, resume, add notes.

CAPTURE — intake
  /logbook:jot <note>          Quick capture to inbox. Auto-splits multi-item input.
                               Use ; to force a split.
  /logbook:triage              Process inbox into queued tasks (group, dedup, discard).
  /logbook:capture             Manual fallback for plan-like content from
                               conversation that didn't go through plan mode.

RECONCILE — catch up
  /logbook:review [window]     Scan recent git history vs open tasks AND inbox
                               lines. Surfaces items that look completed but
                               aren't marked done yet. Default window: 7d.

AUTO — runs in background, no command needed
  Plan mode capture            When Claude exits plan mode (after user accepts),
                               the plan is parsed into queued task files.
  TodoWrite mirror             When any tool calls TodoWrite, status changes
                               (pending/in_progress/completed) are mirrored to
                               queued/active/done. Update-only — never creates
                               new tasks from TodoWrite (avoids tactical
                               sub-step pollution).
  PreCompact snapshot          Before Claude Code compacts conversation context,
                               active task paths are snapshotted to
                               .logbook/.last-session-state for resumption.

QUICK START
  1. /logbook:jot <quick capture>          → inbox.md
  2. /logbook:triage                       → inbox → queued/
  3. /logbook:next                         → queued → active/
  4. (do the work in conversation)         → TodoWrite mirror moves to done/
  5. /logbook:status                       → see what's left
  6. /logbook:review                       → catch up anything missed in git

Files live in .logbook/ at your project root.
Full docs: https://github.com/youcodecowboy/logbook
```

## Rules

- **Render verbatim** — don't editorialize, don't reorder, don't add personal recommendations. The cheat sheet is supposed to be predictable.
- **Read-only.** No file writes, no state changes.
- **Don't follow up with prompts.** The user is browsing the surface area, not starting a workflow. End after the listing.
- **If the user asks for a specific command's details** ("how does /edit work?"), point them at `/logbook:show` (no — that's for tasks). Just say: "Run the command — its skill description has the details. Or see the README at https://github.com/youcodecowboy/logbook"
