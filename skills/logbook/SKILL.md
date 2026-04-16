---
name: logbook
description: >
  Use when the user's request involves multi-step implementation, file modifications,
  feature work, bug fixes, refactoring, or any work that benefits from a written plan.
  Also use when the user references the logbook, backlog, tasks, or asks what to work
  on next. The logbook is a flight recorder of work in `.logbook/` that survives
  compaction, context switches, and new sessions. Do NOT use for simple questions,
  one-line tweaks, explanations, or conversational messages — those don't need
  tracking and the bookkeeping overhead would be noise.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(cat:*), Bash(mv:*), Bash(mkdir:*), Bash(date:*), Bash(ls:*), Task
---

# Logbook

You are managing a backlog stored as plain markdown in `.logbook/` inside the user's repo. The filesystem IS the database. A task's status is encoded by which folder it lives in. Each task is one file with a plan and a log. The job here is twofold: keep a useful written record of work in progress, and stay out of the way while the actual work happens.

## On every activation — read state first

Before doing anything else:

1. **Read `.logbook/index.md`** — this is the source of truth for what tasks exist and their status.
2. **Read `.logbook/inbox.md`** — check for raw captures that might be relevant to the current request.
3. **If `.logbook/` doesn't exist**, initialize it (see Initialization below) and continue.
4. **Print one status line** to the user, e.g.: `📋 Logbook: 2 active, 4 queued, 6 inbox items`. Then proceed with the actual work — the logbook is the flight recorder, not the cockpit.

## Decide what kind of work this is

After reading state, classify the request:

- **Continuation of existing work** — the request relates to a task already in `active/` or `paused/`. Find that task file. If it's in `paused/`, move it to `active/` and update its `Status:` field plus the `index.md` row. Resume from the last incomplete Plan step.

- **A queued task being picked up** — the request matches something in `queued/`. Move that file to `active/`, update `Status:` and `index.md`, then start.

- **New work** — no matching task exists. Create a new task file in `active/`. If there are inbox items relevant to this request, absorb them: paste them into the Source/Context, then remove them from `inbox.md`. Mention what you auto-triaged in your status line so the user can correct course. Auto-triage only happens when you're already actively working — never silently in the background.

## Creating a task file

Filename pattern: `YYYY-MM-DD_kebab-title.md`. The date is when the task was created — don't change it later. Place the file in the appropriate status folder.

Use this template (mirrors `templates/task.md`):

```
# {Title}

Created: YYYY-MM-DD HH:MM
Status: {state}
Tags: #tag1 #tag2
Source: {inbox lines, user request summary, etc.}
Priority: {low|medium|high}

## Context

{1-3 paragraphs explaining what and why. Include relevant file paths,
prior commits, related tasks. This is what future-you needs to pick this
back up cold after a week away.}

## Plan

- [ ] Step 1 (verifiable, action-oriented)
- [ ] Step 2
- [ ] Step 3

## Log

```

**On plan size:** if a task is heading past ~8 steps, it's probably more than one task. Stop and ask the user whether to split. Cross-reference the splits in each Context.

**On tags:** infer from content. Starting vocabulary: `#bug #feature #refactor #ux #perf #docs #test #security #data #system #frontend #backend #debt #chore`. Custom tags are fine — preserve them. Don't force a category that doesn't fit just to use a known tag.

## Logging during work

Before starting a Plan step, append to the `## Log` section:

```
### [N] {Step description}
Status: active
Started: HH:MM
```

After completing the step, append:

```
Completed: HH:MM | Duration: Xm
Summary: {1-3 sentences — what changed and why}
Files touched: path/one.ts, path/two.tsx
Commit: {short hash if applicable, otherwise —}
```

Then check the box in the Plan: `- [x]`. Move on.

**Never delete or rewrite log entries.** They're the audit trail. The Log section is append-only.

## On task completion

When all Plan steps are checked:

1. `mv` the file from `active/` to `done/`.
2. Update its `Status:` field to `done`.
3. Update its row in `index.md` (status column + path).
4. Print a one-line completion summary to the user.

## Updating index.md

Whenever you create a task, move it between folders, or change its status:

- Add or update its row in `index.md`.
- Touch the `Last updated:` line at the top.
- Sort rows by status (active → queued → paused → done → abandoned), then date desc within each block.

Index row format:

```
| {status} | {YYYY-MM-DD} | {Title} | {tags} | {relative/path/to/file.md} |
```

## Delegating bookkeeping to the worker

For multi-step file operations (creating a task and updating index, moving a file plus updating both files, batch-rewriting the index), invoke the `logbook-worker` subagent via the Task tool. The worker runs in a forked context so its `mv` and `Edit` chatter doesn't eat your token budget. Pass it a precise instruction, for example:

> Move `.logbook/active/2026-04-16_fix-settings-flash.md` to `.logbook/done/`.
> Update its `Status:` field to `done`. Update the matching row in `.logbook/index.md`
> (status column from `active` to `done`, path from `active/...` to `done/...`).
> Touch the `Last updated:` line.

For trivial single-file ops (one inbox append, one log entry), do them inline — the worker round-trip isn't worth it.

## Initialization

If `.logbook/` doesn't exist when you activate, create the full structure:

```
.logbook/
├── .gitignore       (see contents below)
├── inbox.md         (header: "# Logbook Inbox\n")
├── index.md         (header + empty table — see below)
├── queued/
├── active/
├── paused/
├── done/
└── abandoned/
```

`.logbook/.gitignore`:

```
# Logbook defaults — edit to taste
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

After initializing, tell the user one line: `📋 Logbook initialized at .logbook/. Run /status anytime.`

Initialization is **idempotent**: if `.logbook/` partially exists, fill in missing pieces without overwriting existing files.

## Critical rules

- **Never delete or overwrite log entries.** Append-only. The audit trail is the point.
- **Always update index.md when files move between folders.** A stale index is worse than no index — it lies to `/status`.
- **Keep the main conversation focused on the actual work.** One status line on activation, one completion line at the end. Logbook bookkeeping that isn't surfaced to the user (file ops, log entries) lives in the worker subagent's context.
- **Get user confirmation before splitting or merging tasks.** Those are structuring decisions, not bookkeeping.
- **Auto-triage from inbox is fine, but always mention it.** Format: `Pulled in 2 inbox items: "settings flash" (10:45), "loading skeletons" (11:15)`.

## Why this design (so you can adapt edge cases)

**Status folders, not date folders** — a task that starts Monday and finishes Thursday shouldn't live in a "Monday" folder. The filesystem answers "what state?"; file contents and git answer "when?". Don't encode time in the filesystem when timestamps already live in the files.

**One file per task** — each has its own lifecycle. Greppable, diffable, movable with `mv`, readable independently. Monolithic logs become unmanageable.

**Tags, not folders-per-domain** — tasks are multi-faceted. `#frontend #perf #bug` simultaneously beats forcing a single classification.

**Auto-triage only inside this skill** — moving from inbox to queued is a structuring decision. The user should know what was triaged and have a chance to correct it. Silent background triage erodes trust in the system fast.

**The `queued/` state exists** because "structured and planned but not started" is genuinely different from "raw note" or "currently being worked." `queued/` IS the backlog. When the user asks "what's next?" the answer is the top of that folder.
