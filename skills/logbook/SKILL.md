---
name: logbook
description: >
  The logbook plugin tracks work-in-progress as plain markdown files in
  `.logbook/` inside the user's repo. Use this skill when the user asks
  about logbook state, what's in the backlog, what they're working on,
  what's next, what's blocked, what was active before context was
  compacted, or wants to resume a session. The plugin captures plans
  automatically (via plan mode + TodoWrite hooks) — decomposition and
  execution are NOT this skill's job. Do NOT activate for general
  multi-step asks where the user just wants help getting work done —
  the plan-mode and TodoWrite capture hooks handle backlog tracking
  automatically in the background.
allowed-tools: Read, Grep, Glob, Bash(ls:*), Bash(cat:*), Task
---

# Logbook

A thin persistence layer on top of Claude Code's plan mode + TodoWrite. The files in `.logbook/` are the source of truth. Most state changes happen automatically via hooks. This skill exists to answer questions about that state and to coordinate the manual entry points (`/logbook:jot`, `/logbook:triage`, `/logbook:capture`, etc.).

## When to use this skill

Activate when the user asks about backlog state:
- "what's in the backlog" / "what should I work on next" / "what's next"
- "what was I working on" / "what's active" / "any blockers?"
- "show me logbook" / "logbook status"
- "I need to pick up where I left off"

**Do NOT activate** for substantive work requests like "fix the X bug" or "refactor module Y" — those go through plan mode (whose `ExitPlanMode` hook captures the resulting plan automatically) or stay in normal conversation. Logbook is the *observer*, not the orchestrator.

## On every activation — read state first

1. **Check `.logbook/.last-session-state`** — JSON snapshot the PreCompact hook left before the previous session was compacted. If it lists active tasks and the snapshot is recent (within a day), mention them: `📋 Last session was compacted while working on: <task>. Pick up?`
2. **Read `.logbook/index.md`** — source of truth for which tasks exist and where.
3. **Read `.logbook/inbox.md`** if there are untriaged items.
4. **Print one status line**, then answer the user's question:
   ```
   📋 Logbook: 2 active, 4 queued, 6 inbox items
   ```
5. **If `.logbook/` doesn't exist**, initialize it (see Initialization below) and tell the user once.

## Architecture (so you understand the system you're operating in)

Backlog enters from three sources:

| Source | Mechanism | When it fires |
|---|---|---|
| **Plan mode** | `hooks/capture-plan.py` (PostToolUse on `ExitPlanMode`) | Automatic after user accepts a plan from plan mode. Plan is parsed into queued tasks. |
| **TodoWrite mirror** | `hooks/mirror-todos.py` (PostToolUse on `TodoWrite`) | Automatic on every TodoWrite call. Mirrors `pending → queued/`, `in_progress → active/`, `completed → done/`. Fuzzy-matches against existing tasks to avoid duplicates. |
| **Manual** | `/logbook:jot` for quick captures, `/logbook:capture` for in-conversation plans the auto-hooks didn't catch | When the user invokes them. |

State changes from `pending → in_progress → completed` (in TodoWrite) automatically move task files between folders. **You do not need to drive any of this.** The hooks do it. Your job is to be the read/query interface.

## What this skill does NOT do

- **No Plan generation.** Tasks have a `## Notes` section (free-form, optional, never auto-filled). Plans are produced by plan mode or whatever execution tool the user picks up.
- **No execution orchestration.** Logbook moves files based on TodoWrite signals or explicit user commands. The actual implementation work is done by Superpowers, vanilla Claude continuing the conversation, the user themselves, or any other tool — not by this skill.
- **No per-step logging ceremony.** Tasks don't have a structured `## Log` section. Git history + the conversation transcript already capture what happened during execution.

## File operations

For any file write (creating, moving, updating index, archiving discards), invoke the `logbook-worker` subagent via the `Task` tool with `subagent_type="logbook:logbook-worker"`. The worker handles writes in a forked context so this skill stays a clean read/query interface. For trivial single-line reads, do them inline.

## Task file format

Minimal. Frontmatter + `Source` + free-form `Notes`:

```
# {Title}

Created: YYYY-MM-DD
Status: {queued|active|paused|done|abandoned}
Tags: #tag1 #tag2
Source: {plan mode | TodoWrite | inbox: {original line} | manual | captured from conversation}
Priority: {low|medium|high}

## Notes

{Free-form. Empty by default. The execution tool can add context/decisions/blockers here.}
```

If a task is `active` but waiting on user input, it gets a `Blocked:` field:

```
Status: active
Blocked: YYYY-MM-DD HH:MM — short reason; question for user
```

`/logbook:status` surfaces blocked tasks separately. `Blocked:` older than ~7 days hints at promotion to `paused/`.

## Picking up the next queued task

When the user invokes `/logbook:next` or asks something like "what should I work on" / "give me the next thing" without naming a specific task, sort `queued/` by:

1. Priority desc (`high → medium → low`)
2. Date asc (oldest first within same priority — older items have been waiting longer)

Pick the top, move it to `active/` (delegate the move to logbook-worker), update the row in `index.md`. One-liner: `📋 Started '<title>'.` Then get out of the way — the user's actual execution tool takes it from there.

If `queued/` is empty, say so and offer either to start a new task with `/logbook:start` or to run `/logbook:triage` if there are inbox items waiting.

## Initialization

If `.logbook/` doesn't exist, create the structure:

```
.logbook/
├── .gitignore       (defaults below)
├── inbox.md         "# Logbook Inbox\n"
├── index.md         (header + empty table)
├── queued/, active/, paused/, done/, abandoned/
```

`.logbook/.gitignore`:
```
inbox.md
done/
abandoned/
```

`.logbook/index.md`:
```
# Logbook Index

Last updated: YYYY-MM-DD HH:MM

| Status | Date | Title | Tags | File |
|--------|------|-------|------|------|
```

Idempotent — fill in missing pieces, never overwrite.

## Critical rules

- **Stay invisible by default.** One status line on activation, one-line announcements when you actually do something. No walls of text. Hooks emit their own one-line announcements on state changes.
- **Never generate Plans.** Tasks have `## Notes` only. If a user asks for help planning, point them at plan mode or whatever planning tool they prefer — don't try to plan inside this skill.
- **Never drive execution.** Move files in response to TodoWrite signals or explicit user instructions. Don't tell the user (or any sub-agent) what to do or how to do it.
- **Always update index.md** when files move. Worker handles this when delegated; if you're doing inline ops, do it yourself.
- **Escape `|` in titles** as `\|` when writing index rows.
- **Don't touch `Status:` directly during conversation** — let the TodoWrite mirror hook do it. If you must (because the user explicitly said "mark X done"), do it but also surface that the next TodoWrite call may overwrite based on whatever the source tool thinks.

## Why this design

**Logbook is a durability layer, not a planner.** Every iteration of the spec that tried to make logbook smarter at planning ended up duplicating what plan mode, Superpowers, brainstorming, or other purpose-built tools already do better. The defensible value is being the only thing that makes plans and todos *survive* across sessions, agents, and developers — by living on disk in a queryable structure, in any project, with no per-tool integration required.

**Hooks > model judgment for state machines.** The "this todo went from in_progress to completed → move file to done/" decision is deterministic. A hook does it correctly every time. A model heuristic would be slower, more expensive, and occasionally wrong. The hooks own the state machine; this skill owns reads, queries, and the manual entry points.
