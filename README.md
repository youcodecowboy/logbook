# logbook

> A Claude Code plugin that gives every session a flight recorder. Automatic task capture, structured backlog, session-aware work tracking — all stored as plain markdown files in your repo.

**Audience:** Vibecoders, solo devs, and small teams who work fast and conversationally and need a backlog system that doesn't require a separate tool.

**Philosophy:** The backlog is files. Everything else is a view. No external dependencies, no auth, no subscriptions. Git tracks history for free.

> ⚠️ **Status: v0.1 — first-user dogfood.** The author is the first test subject. Expect rough edges and rapid iteration. Feedback and PRs welcome.

---

## What it does

| Command | What it does |
|---|---|
| `/jot <note>` | Append to `.logbook/inbox.md`. Auto-splits multi-item input into separate lines (`/jot fix dashboard flash, also auth is brittle, and add skeletons` → 3 lines). Use `;` to force a split when you want to be explicit. |
| `/status` | Dashboard: counts per state, active task progress, queued items. |
| `/triage` | Group raw inbox captures into structured tasks (queued backlog). Also detects when one inbox line is actually multiple items in a trench coat and offers to split. |
| `/logbook <task>` | Explicitly start a tracked task with a plan. |
| _(automatic)_ | When you ask Claude for something multi-step (a feature, a bug fix, a refactor), the main `logbook` skill auto-triggers and creates a task file with a plan. Progress is logged step-by-step. |

The plugin stores everything in `.logbook/` inside your repo. Tasks live in folders named after their state (`queued/`, `active/`, `paused/`, `done/`, `abandoned/`). An `index.md` at the top is the master table.

---

## Why files?

- **Greppable.** `rg "auth"` across `.logbook/` finds every task touching auth.
- **Diffable.** Git tracks every change to your backlog for free.
- **Movable.** A task that goes from active to done is just `mv`.
- **Portable.** No vendor lock-in. Open the files in any editor. Read them on a plane.
- **Survives compaction.** Your work plan is on disk, not in a context window.

---

## Install

**Marketplace install (recommended):**

```
/plugin marketplace add youcodecowboy/logbook
/plugin install logbook@logbook
```

**Local install (no marketplace):**

```bash
git clone https://github.com/youcodecowboy/logbook.git ~/code/logbook
```

```
/plugin install ~/code/logbook
```

The first time you run `/jot`, `/status`, or trigger a tracked task, logbook auto-initializes `.logbook/` in your project root.

> **If the marketplace install errors with "marketplace file not found"**, you're on a version older than v0.1.4 (which added `.claude-plugin/marketplace.json`). Either pull latest and retry, or use the local-install path above. If a stale marketplace cache is hanging around, run `/plugin marketplace remove logbook` (or `youcodecowboy-logbook`, depending on what got cached) before re-adding.

> **One-time permission prompt:** the main `logbook` skill, `/triage`, and the worker subagent use `date '+%Y-%m-%d %H:%M'` to timestamp log entries. Claude Code will ask for permission the first time — pick "always allow" and it goes silent. `/jot` does not need this — it uses the date already in context.

---

## Quick start

```
/jot the dashboard flashes white on first load

# (a few /jots later)
/triage
# → presents grouping suggestions, you confirm
# → creates queued/2026-04-16_fix-dashboard-flash.md

/status
# → shows the current state of your backlog

# (later, just talk to Claude)
"hey can you fix that dashboard flash thing"
# → main logbook skill triggers, picks up the queued task,
#   moves it to active/, executes the plan, logs each step,
#   moves to done/ on completion
```

---

## Task lifecycle

```
                    ┌─────────────┐
  /jot ──────────►  │   inbox.md  │  raw, unstructured one-liners
                    └──────┬──────┘
                           │ /triage
                    ┌──────▼──────┐
                    │   queued/   │  triaged, planned, ready to work
                    └──────┬──────┘
                           │ work begins
                    ┌──────▼──────┐
                    │   active/   │  agent is executing steps
                    └──────┬──────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌─────────┐  ┌───────────┐
         │  done/ │  │ paused/ │  │abandoned/ │
         └────────┘  └─────────┘  └───────────┘
```

| State | Meaning |
|---|---|
| **inbox** | Raw capture. Unstructured one-liners with timestamps. No plan, no tags. |
| **queued** | Triaged and structured. Has a plan with steps, tags, and context. Ready to be picked up. This IS the backlog. |
| **active** | Currently being worked. The agent is executing steps and logging progress. Realistically 1–2 at a time. |
| **paused** | Started but parked — waiting on something, context switched, deprioritized. |
| **done** | Completed. All steps finished, logged, summarized. |
| **abandoned** | Decided not to do. Kept for context (why we *didn't* do something is valuable). |

---

## Filesystem layout (in your repo)

```
.logbook/
├── .gitignore           # ignores inbox.md, done/, abandoned/ by default
├── inbox.md             # raw jots, timestamped
├── index.md             # master table of all tasks
├── queued/              # the actual backlog
├── active/              # currently being worked
├── paused/              # parked
├── done/                # completed
└── abandoned/           # decided against (kept for context)
```

By default, `inbox.md`, `done/`, and `abandoned/` are gitignored — they're scratch and archive, and git itself is your history tool. `queued/`, `active/`, `paused/` are tracked because they're living documentation of what's in flight.

You can toggle these in `.logbook/.gitignore` directly.

---

## Sample task file

```markdown
# Fix Settings Page Flash

Created: 2026-04-16 11:30
Status: active
Tags: #frontend #bug #ui
Source: inbox (2026-04-16 10:45 — settings page flashes white on load)
Priority: medium

## Context

The settings page shows a white flash on load because the theme context
isn't available on first render. The CSS defaults to light mode and then
switches when the context hydrates.

## Plan

- [x] Reproduce and identify root cause
- [ ] Fix the rendering pipeline to await theme context
- [ ] Add a minimal loading state / skeleton
- [ ] Verify on both light and dark mode

## Log

### [1] Reproduce and identify root cause
Status: done
Started: 11:32 | Completed: 11:38 | Duration: 6m
Summary: Confirmed — `useTheme()` returns `undefined` on first render
  because `ThemeProvider` is inside a lazy-loaded layout. The CSS
  transition from white → dark causes the flash.
Files touched: (investigation only, no changes)
Commit: —

### [2] Fix rendering pipeline
Status: active
Started: 11:40
```

---

## Tagging

Tags are inferred by the model from task content. Starting vocabulary:

```
#bug #feature #refactor #ux #perf #docs #test #security
#data #system #frontend #backend #debt #chore
```

Custom tags are encouraged — write them in your `/jot` notes (`/jot #urgent the deploy is broken`) and they'll be preserved.

---

## How the pieces fit

- **`logbook`** — main skill, auto-triggers on multi-step work. Reads state, decides what to do, logs progress.
- **`logbook-jot`** — `/jot`. Appends a line to `inbox.md` and returns. Zero context switch.
- **`logbook-status`** — `/status`. Read-only dashboard.
- **`logbook-triage`** — `/triage`. Promotes inbox items into structured queued tasks (with your confirmation).
- **`logbook-worker`** — subagent that handles file I/O in a forked context, so `mv` and `Edit` chatter doesn't eat your main token budget.
- **`pre-compact.py`** — PreCompact hook. Marks active task files with a checkpoint and snapshots session state before Claude Code compacts the conversation. So if compaction happens mid-step, you can pick up where you left off.

---

## Roadmap

v0.1 (this release) ships:

- ✅ Main `logbook` skill (auto-trigger + `/logbook`)
- ✅ `/jot`, `/status`, `/triage`
- ✅ `logbook-worker` subagent for file ops
- ✅ PreCompact hook (work survives context compaction)
- ✅ Auto-initialization of `.logbook/`

Planned for later versions:

**Smarter triage (v0.2 candidate).** Triage today groups by topic. Make it group by *code overlap*: Grep/Glob the user's repo to infer which files each inbox item likely touches, then group items whose file-sets overlap. That's the actual right metric for token efficiency — two items that touch the same file are a free combo even if they look unrelated; two "auth" items that touch totally different files waste a context load if combined. Add dedup detection (same idea jotted twice), subsumption detection (small item is a subset of a larger one → becomes a Plan step, not a separate task), and effort sensing (flag tasks that look like they're secretly 8 things). The repo-awareness piece is load-bearing; the rest is icing.

**Autonomous research subagents (v0.3 candidate).** After `/triage` confirms a queued task, optionally spawn a background `Task` subagent (`run_in_background=true`) that reads the relevant files and writes a real Context + Plan into the queued task file. By the time you pick up the task with `/logbook`, the spec is ready for review — you skim, refine, then execute. This turns triage into an async research stage running in parallel with whatever you're doing in the foreground. The token cost is amortized across separate sessions; the foreground context stays clean. This is the long-term shape: async preparation, synchronous execution.

**Smaller items:**
- PostToolUse auto-capture hook (opt-in; logs every file edit + commit to inbox as `[auto] …` lines)
- `/logbook config <key> <value>` command
- `/logbook repair` (reconcile `index.md` with the actual filesystem)
- Tag filtering in `/status`
- Priority sorting in `queued/`
- Multi-session conflict handling (right now, two parallel Claude Code sessions writing to the same `.logbook/` is undefined behavior)
- Stale-item awareness (tag inbox items that have sat for >N days)
- Auto-archival of old `done/` items into `done/archive/YYYY-MM/`

---

## Contributing

Right now this is dogfood. The fastest way to help is to **use it and tell me what's broken or annoying.** File an issue with:

- What you tried to do
- What logbook did instead
- The relevant `.logbook/` file or log entry, if useful

PRs welcome — but please ping in an issue first, since the design is still settling.

---

## Design rationale (the short version)

**Status folders, not date folders** — a task that starts Monday and finishes Thursday shouldn't live in a "Monday" folder. Filesystem answers "what state?"; file contents and git answer "when?".

**One file per task** — each has its own lifecycle. Greppable, diffable, movable. Monolithic logs become unmanageable fast.

**Tags, not folders-per-domain** — tasks are multi-faceted. `#frontend #perf #bug` simultaneously beats forcing a single classification.

**Auto-triage gated to the main skill** — moving from inbox to queued is a structuring decision. The user should know what was triaged and have a chance to correct it. Silent background triage erodes trust fast.

**A `queued/` state exists** because "structured and planned but not started" is genuinely different from "raw note" or "currently being worked." `queued/` IS the backlog. When the user asks "what's next?" the answer is the top of that folder.

**A worker subagent for file ops** — bookkeeping happens in a forked context so the main conversation isn't eaten by `mv` and `Edit` chatter. The overhead is invisible to the user.

---

## License

MIT. See [LICENSE](LICENSE).
