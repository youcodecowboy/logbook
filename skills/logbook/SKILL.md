---
name: logbook
description: >
  Track substantive work in `.logbook/` as plain markdown files. Use when the
  user is starting actual work that benefits from a written plan: multi-step
  implementation, feature work, bug fixes, refactoring, or when they explicitly
  ask to start a tracked task or pick up something from the backlog. Also use
  when they ask what to work on next or want to review work in flight. Do NOT
  use for simple questions, one-line tweaks, explanations, or conversational
  messages — those don't need tracking. Do NOT use when the user message is an
  instruction to invoke `logbook-jot`, `logbook-status`, or `logbook-triage` —
  those are dedicated sibling skills and don't need orchestration. If a sibling
  skill is being invoked, stay out of it.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(cat:*), Bash(mv:*), Bash(mkdir:*), Bash(date:*), Bash(ls:*), Task
---

# Logbook

You are managing a backlog stored as plain markdown in `.logbook/` inside the user's repo. The filesystem IS the database. A task's status is encoded by which folder it lives in. Each task is one file with a plan and a log. The job here is twofold: keep a useful written record of work in progress, and stay out of the way while the actual work happens.

## On every activation — read state first

Before doing anything else:

1. **Read `.logbook/index.md`** — this is the source of truth for what tasks exist and their status.
2. **Read `.logbook/inbox.md`** — check for raw captures that might be relevant to the current request.
3. **Read `.logbook/.last-session-state` if it exists** — this is a JSON snapshot left by the PreCompact hook before the prior session was compacted. It lists active task paths at the moment of compaction. If the user is resuming work, mention which tasks were in flight: `📋 Last session was compacted while working on: <task title>. Want me to resume?`
4. **If `.logbook/` doesn't exist**, initialize it (see Initialization below) and continue.
5. **Print one status line** to the user, e.g.: `📋 Logbook: 2 active, 4 queued, 6 inbox items`. Then proceed with the actual work — the logbook is the flight recorder, not the cockpit.

### Reading task files: how to interpret `[compaction checkpoint]` entries

The PreCompact hook may have appended log entries that look like:

```
### [compaction checkpoint] 2026-04-16 14:32
Status: context was about to be compacted.
Note: resume from the last unchecked Plan step. ...
```

These are **not Plan steps**. They're hook-written markers noting that the conversation context was compacted at that point and the most recent normal log entry above may be incomplete. When you see one, treat it as a "work was happening here, then context was wiped" signal: trust the Plan checkboxes, resume from the first unchecked one, and don't try to re-do what may have already been done — check the codebase for evidence first.

## Decide what kind of work this is

After reading state, classify the request:

- **Continuation of existing work** — the request relates to a task already in `active/` or `paused/`. Find that task file. If it's in `paused/`, move it to `active/` and update its `Status:` field plus the `index.md` row. Resume from the last incomplete Plan step.

- **A queued task being picked up** — the request matches something in `queued/`. Move that file to `active/`, update `Status:` and `index.md`, then start.

- **"Pick the next queued task"** — the user invoked `/logbook:next` or asked something like "what should I work on" / "give me the next thing" without naming a specific task. Sort `queued/` by:
  1. Priority desc (high → medium → low)
  2. Date asc (oldest first within the same priority — older items have been waiting longer)

  Pick the top of that sort, move it to `active/`, update `Status:` and the `index.md` row, then start. If `queued/` is empty, say so and offer to start a new task or run `/logbook:triage` if there are inbox items waiting.

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

## When work hits a blocker (waiting on user input)

If during execution you discover the task can't proceed without user input, a decision, or a dependency that doesn't exist yet, **don't move the file** — the work is still active, just paused on a specific input. Use the structured `Blocked:` field instead:

1. **Add a `Blocked:` field to the task file** (just below `Status:`):

   ```
   Status: active
   Blocked: YYYY-MM-DD HH:MM — short description of what's needed (1-3 sentences; longer context goes in the Log)
   ```

2. **Log the full context** in the `## Log` section so a future session can pick it up cold:

   ```
   ### [N] {Step that hit the blocker}
   Status: blocked
   Started: HH:MM | Blocked: HH:MM
   Summary: {what was tried, what was found, why it can't proceed}
   Question for user: {explicit ask, ideally with concrete options}
   ```

3. **Surface the question to the user** clearly. Don't bury it: "I'm blocked on `{task title}` — {short reason}. Options: (1) X, (2) Y, (3) Z. Which way?"

4. **Do NOT move the file to `paused/`.** Transient input-waiting belongs in active/. Moving to paused/ implies indefinite parking and is heavy for a question that might be answered in 30 seconds.

When the user responds and the blocker clears:

1. **Remove the `Blocked:` field** from the task file.
2. Append a log entry capturing the resolution.
3. Continue with the next Plan step (or re-scope the Plan if the answer changed the task's shape).

**Heuristic for promotion to `paused/`:** if `Blocked:` is older than ~7 days, suggest moving the task to `paused/`. A week without resolution usually means the work has actually stopped — better to tell `/status` the truth than pretend it's still active. Always ask before moving; never auto-promote.

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

**Escape `|` characters in titles** as `\|` when writing the row, so a title like `Add |> operator support` doesn't break the table. The original task file keeps the title unescaped — only the index row needs escaping.

## Delegating bookkeeping to the worker

For multi-step file operations (creating a task and updating index, moving a file plus updating both files, batch-rewriting the index), invoke the `logbook-worker` subagent via the Task tool. The worker runs in a forked context so its `mv` and `Edit` chatter doesn't eat your token budget.

**Exact invocation:** Use the Task tool with `subagent_type="logbook:logbook-worker"` (the plugin name `logbook` plus the agent name `logbook-worker`, separated by a colon — that's how Claude Code namespaces plugin-provided subagents). Pass a precise instruction in the `prompt` field, for example:

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
- **Don't move blocked tasks out of `active/` for short waits.** Use the `Blocked:` field for transient input-waiting; reserve `paused/` for explicit parking or stale blocks (>7 days).
- **Keep the main conversation focused on the actual work.** One status line on activation, one completion line at the end. Logbook bookkeeping that isn't surfaced to the user (file ops, log entries) lives in the worker subagent's context.
- **Get user confirmation before splitting or merging tasks.** Those are structuring decisions, not bookkeeping.
- **Auto-triage from inbox is fine, but always mention it.** Format: `Pulled in 2 inbox items: "settings flash" (10:45), "loading skeletons" (11:15)`.

## Why this design (so you can adapt edge cases)

**Status folders, not date folders** — a task that starts Monday and finishes Thursday shouldn't live in a "Monday" folder. The filesystem answers "what state?"; file contents and git answer "when?". Don't encode time in the filesystem when timestamps already live in the files.

**One file per task** — each has its own lifecycle. Greppable, diffable, movable with `mv`, readable independently. Monolithic logs become unmanageable.

**Tags, not folders-per-domain** — tasks are multi-faceted. `#frontend #perf #bug` simultaneously beats forcing a single classification.

**Auto-triage only inside this skill** — moving from inbox to queued is a structuring decision. The user should know what was triaged and have a chance to correct it. Silent background triage erodes trust in the system fast.

**The `queued/` state exists** because "structured and planned but not started" is genuinely different from "raw note" or "currently being worked." `queued/` IS the backlog. When the user asks "what's next?" the answer is the top of that folder.
