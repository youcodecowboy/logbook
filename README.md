# logbook

> A lightweight backlog directory for Claude Code. Captures plans automatically from plan mode and TodoWrite, mirrors state to plain markdown files in your repo, and gives you a durable cross-session view of what's in flight — without trying to plan or execute anything itself.

**Audience:** Vibecoders, solo devs, and small teams running multiple Claude Code sessions / sub-agents who lose track of what's done vs. what's still in flight.

**Philosophy:** Logbook is the memory layer underneath the tools you actually use. Plan mode plans the work. Superpowers / vanilla Claude / your own skills do the work. Logbook just remembers what's been planned and what's been done — across sessions, across agents, across developers pulling from the same repo.

> ⚠️ **Status: v0.2.0 — fundamental architectural rewrite.** v0.1.x tried to be a self-sufficient planner-orchestrator and competed with better-purpose tools. v0.2.0 strips that out and becomes a thin persistence layer that hooks into Claude Code's native plan mode + TodoWrite. If you used v0.1.x, the file layout is the same but the behavior is meaningfully different. See [CHANGELOG-style notes](#changes-from-v01x) below.

---

## How it works

```
┌──────────────────────────────────────────────────────────┐
│  You make a substantive request to Claude Code           │
└────────────────────────────┬─────────────────────────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
┌─────────────┐       ┌──────────────┐       ┌──────────┐
│  Plan mode  │       │  TodoWrite   │       │  /jot    │
│  (auto)     │       │  (auto)      │       │  (manual)│
└──────┬──────┘       └──────┬───────┘       └─────┬────┘
       │                     │                     │
       │  ExitPlanMode hook  │  TodoWrite hook     │
       │  capture-plan.py    │  mirror-todos.py    │
       │                     │                     │
       └─────────────────────┴─────────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   .logbook/         │
                  │     queued/         │
                  │     active/         │
                  │     paused/         │
                  │     done/           │
                  │     abandoned/      │
                  │     index.md        │
                  └─────────────────────┘
                             ▲
       ┌─────────────────────┼─────────────────────┐
       │                     │                     │
  /logbook:status     /logbook:next        /logbook:triage
  /logbook:start      /logbook:capture
```

**Three capture paths feed the same `.logbook/` directory.** Most of the time you don't notice logbook is there — it just keeps state in sync. When you want to query what's going on, the slash commands are your read interface.

---

## What it does

| Command | What it does |
|---|---|
| _(automatic)_ | When Claude exits plan mode, the captured plan is decomposed into queued task files. When TodoWrite is used (by any tool — vanilla Claude, Superpowers, etc.), todo state is mirrored to `.logbook/` folders: `pending → queued/`, `in_progress → active/`, `completed → done/`. Fuzzy-matched against existing tasks to avoid duplicates. |
| `/logbook:jot <note>` | Manual quick-capture to `.logbook/inbox.md`. Auto-splits multi-item input. |
| `/logbook:status` | Read-only dashboard: counts per state, active task progress, blocked tasks, queued items. |
| `/logbook:triage` | Process inbox items into queued tasks. Smart at grouping/dedup/discard. Does NOT generate Plans. |
| `/logbook:capture` | Manual fallback for plan-like content from conversation that didn't go through plan mode. |
| `/logbook:start <task>` | Start a new tracked task explicitly with a description. |
| `/logbook:next` | Pick up the highest-priority queued task and move it to `active/`. |

---

## What it does NOT do

- **Doesn't generate Plans.** Task files have a free-form `## Notes` section, never auto-filled. When you pick up a queued task, plan mode (or whatever execution tool you use) does the planning.
- **Doesn't orchestrate execution.** Logbook moves files in response to TodoWrite signals or explicit commands. The actual implementation work happens in whatever tool you reach for.
- **Doesn't compete with Superpowers, brainstorming, or other planning skills.** It runs underneath them and captures their output for durability.

The core problem it solves: when you're running multiple Claude Code sessions or sub-agents, plans live in conversation context and TODOs live in session state — both gone when the session ends. Logbook makes them survive on disk and queryable across sessions.

---

## Install

**Marketplace install (recommended):**

```
/plugin marketplace add youcodecowboy/logbook
/plugin install logbook@logbook
```

**Local install:**

```bash
git clone https://github.com/youcodecowboy/logbook.git ~/code/logbook
```

```
/plugin install ~/code/logbook
```

The first time logbook activates in a project (auto-trigger from a hook, or manual command), `.logbook/` is initialized in the project root.

> **Command namespacing:** Claude Code namespaces plugin commands as `/<plugin>:<command>`, so the canonical form is `/logbook:jot`, `/logbook:status`, etc. Bare forms (`/jot`) may work as shorthand depending on your Claude Code setup, but the namespaced form always works.

---

## Quick start

```
# 1. You ask Claude something substantive.
"work on the upload flow — it's missing what the mobile web has"

# 2. Claude enters plan mode, investigates, produces a plan.
#    You accept the plan.
#    capture-plan.py hook fires → 8 tasks land in .logbook/queued/
#    📋 Captured plan: 8 task(s) → .logbook/queued/

# 3. Claude (or Superpowers, or whatever) starts work.
#    It uses TodoWrite to track progress.
#    mirror-todos.py hook fires on each call:
#    📋 Started: Add multi-file selection
#    📋 Wrapped: Add multi-file selection
#    📋 Started: Add chunked upload retry

# 4. Sometime later, you check what's in flight:
/logbook:status
# 📋 Logbook Status
# ─────────────────
# Active:    1 task
# Queued:    6 tasks
# Done:      1 task

# 5. You go to bed. Next day:
/logbook:status
# Logbook still knows where you left off.
# .logbook/active/<task>.md and queued/ files are durable.

# 6. Quick informal capture during testing:
/logbook:jot the modal doesn't close on escape
# 📝 Logged to inbox: the modal doesn't close on escape
```

---

## Filesystem layout (in your repo)

```
.logbook/
├── .gitignore                # ignores inbox.md, done/, abandoned/ by default
├── inbox.md                  # raw captures from /jot
├── index.md                  # master table of all tasks + statuses
├── .last-session-state       # snapshot from PreCompact hook (gitignored)
├── queued/                   # the actual backlog
├── active/                   # currently being worked
├── paused/                   # parked indefinitely
├── done/                     # completed
└── abandoned/                # decided against (kept for context)
```

By default, `inbox.md`, `done/`, `abandoned/` are gitignored — they're scratch + archive, and git is your history tool. `queued/`, `active/`, `paused/` are tracked because they're living documentation of what's in flight. Edit `.logbook/.gitignore` to taste.

---

## Sample task file (v0.2.0 — minimal)

```markdown
# Add multi-file selection to upload

Created: 2026-04-16
Status: active
Tags: #frontend #ux
Source: captured from plan mode
Priority: medium

## Notes

```

That's the whole file. No `## Plan` checklist — plans come from plan mode or other execution tools at the moment work is picked up. No structured `## Log` — git history + the conversation transcript already capture what happened. The `## Notes` section is free-form, optional, and never auto-filled — it's there for the user or the execution tool to add context as needed.

If a task is `active` and waiting on user input, a `Blocked:` field appears below `Status:`:

```markdown
Status: active
Blocked: 2026-04-16 15:32 — waiting on scope clarification (close as obsolete? re-scope to icons only?)
```

`/logbook:status` surfaces blocked tasks separately. Blocks older than ~7 days hint at promoting the task to `paused/`.

---

## Behavior notes

**Within-day ordering is by file position, not timestamp.** Inbox items are dated `YYYY-MM-DD` only. If you capture 10 things in a day, they appear in capture order — file position is the order signal. If you need precise time, type it in the note: `/jot 14:30 — deploy went red`.

**`/triage` writes through the worker subagent.** When you confirm a triage plan, the file operations happen in a forked subagent context to keep your main conversation clean. You'll see a one-line summary when it finishes.

**Discards live at `.logbook/abandoned/inbox-discards.md`** — single rolling file rather than one file per discard. The `abandoned/` folder is gitignored by default, so discards stay local.

**Blocked active tasks stay in `active/`.** When a task can't proceed without user input, the `Blocked:` field captures it but the file doesn't move. Moving to `paused/` is for indefinite parking, not transient input-waiting. Heuristic: blocks older than ~7 days hint at promotion.

**One-line announcements.** Hooks emit single-line `📋` messages on actual state changes (capturing a plan, starting a todo, wrapping a todo). No-op syncs are silent. Cap of ~3 announcements per call to avoid chat spam.

---

## Tagging

Tags are inferred by the model from task content. Starting vocabulary:

```
#bug #feature #refactor #ux #perf #docs #test #security
#data #system #frontend #backend #debt #chore
```

Custom tags are encouraged — write them in `/jot` notes (`/jot #urgent the deploy is broken`) and they'll be preserved.

---

## How the pieces fit

- **`hooks/capture-plan.py`** — `PostToolUse` on `ExitPlanMode`. Parses plan content (from `tool_input.plan` or `~/.claude/plans/*.md`), creates queued task files, dedups against existing tasks.
- **`hooks/mirror-todos.py`** — `PostToolUse` on `TodoWrite`. Mirrors todos to logbook folders by status. Fuzzy-matches existing tasks to avoid duplicates.
- **`hooks/pre-compact.py`** — `PreCompact`. Snapshots active task paths to `.logbook/.last-session-state` so the main skill can offer resumption next session.
- **`logbook` skill** — Auto-activates when the user asks about backlog state. Read/query interface; doesn't drive work.
- **`logbook-jot` / `logbook-triage` / `logbook-capture` / `logbook-status` skills** — Manual entry points. Triage and capture delegate writes to logbook-worker.
- **`logbook-worker` agent** — All file writes happen here, in a forked context, so the main conversation stays focused on actual work.

---

## Changes from v0.1.x

If you were running v0.1.x, here's what changed:

| What | v0.1.x | v0.2.0 |
|---|---|---|
| **Decomposition** | Main skill did its own multi-step planning, generated `## Plan` checklists per task | Plan mode does it; capture-plan.py hook ingests the result |
| **Task files** | Frontmatter + `## Context` + `## Plan` checklist + structured `## Log` per step | Frontmatter + `Source:` + free-form `## Notes`. No Plan, no structured Log. |
| **Execution** | Main skill orchestrated step-by-step, logged each step | No execution orchestration. Other tools do the work; logbook just observes state changes |
| **State updates** | Main skill manually `mv`d files between folders | `mirror-todos.py` hook does it automatically based on TodoWrite state |
| **Triage** | Generated `## Plan` for each new queued task | Doesn't generate Plans. Tasks get empty `## Notes`. |
| **Compaction handling** | Wrote `[compaction checkpoint]` log entries | Just snapshots state to `.last-session-state` (no log entries to write into) |
| **Visibility** | Long status messages, multi-step prompts | Single-line `📋` announcements; mostly silent |

Existing `.logbook/` directories from v0.1.x continue to work — old task files with `## Plan` and `## Log` sections are read fine, just no new ones get those sections going forward.

---

## Roadmap

- **Loop-mode execution** — after queued tasks are picked up, optionally auto-pull the next on completion (vs. asking each time)
- **`/logbook:repair`** — reconcile `index.md` with the actual filesystem
- **Tag filtering in `/status`** — `/logbook:status #frontend`
- **Cross-project view** — query state across multiple `.logbook/` directories on the machine
- **Smarter triage** — repo-aware grouping (Grep/Glob the codebase to infer file overlap, group by file area)
- **Multi-session conflict handling** — right now, two parallel Claude Code sessions writing to the same `.logbook/` is undefined behavior

---

## Contributing

Right now this is dogfood. The fastest way to help is to **use it and tell me what's broken or annoying.** File an issue with:
- What you tried to do
- What logbook did instead
- Relevant `.logbook/` file or hook output

PRs welcome — please ping in an issue first; the design is still settling.

---

## License

MIT. See [LICENSE](LICENSE).
