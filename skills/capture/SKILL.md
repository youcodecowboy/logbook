---
name: capture
description: >
  Capture a plan-like structure from the recent conversation into the
  logbook backlog. Use when the user invokes /logbook:capture or asks
  to "save this as tasks", "log these as backlog items", "capture this
  plan", or similar. This is the manual fallback for cases where plan
  mode wasn't formally entered (so the auto-capture hook didn't fire)
  but a list of tasks exists in the conversation.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Task
---

# /logbook:capture — Manual Plan Capture

Fallback for capturing plan-like content from conversation when the auto-capture hooks didn't fire. Common cases:
- A planning discussion didn't formally use plan mode (no `ExitPlanMode` → no hook fire)
- The user pasted a list of tasks
- Another agent (or this conversation) produced a list without using TodoWrite

## Steps

### 1. Find the plan content

Look at the most recent conversation context for plan-like structures:
- Numbered lists (`1. Foo / 2. Bar / ...`)
- Markdown checkboxes (`- [ ] Foo / - [ ] Bar`)
- Headers like `## Tasks`, `## Plan`, `## Backlog`, `## Steps`
- Bulleted lists with action verbs at the start of each item

If nothing plan-like is in recent context, ask once: "What should I capture? Paste the list or describe the items."

### 2. Extract task titles

For each item found, extract a concise title (one line, action-verb-led if possible):
- Strip leading symbols (`-`, `*`, `1.`, `[ ]`)
- Strip leading bold markers (`**...**`)
- Strip prefixes like `Step N:` or `Task N:`
- Skip meta-section headers (Plan, Overview, Goals, Context, Summary, Approach, Background)

### 3. Present what you found

```
📋 Found {N} items to capture:

  1. {Title 1}
  2. {Title 2}
  ...

Push all to queued/? Or:
  - "drop N" — exclude an item
  - "rename N to X" — change a title
  - "cancel" — abort
```

### 4. Accept the response

Same response interpretation as triage (natural language, not literal keywords). On approval, proceed.

### 5. Delegate writes to logbook-worker

**Do not write files yourself.** Hand the batch to the `worker` subagent via Task tool with `subagent_type="logbook:worker"`. Pass a precise instruction: create N task files in `.logbook/queued/`.

Each task file content:

```
# {Title}

Created: YYYY-MM-DD
Status: queued
Tags:
Source: captured from conversation
Priority: medium

## Notes

```

Worker also adds rows to `index.md` and touches the `Last updated:` line.

### 6. Show the summary

```
✓ Captured {N} task(s) → .logbook/queued/
  → queued/2026-04-16_<slug>.md
  → ...
```

## Rules

- **No Plan generation.** Tasks have `## Notes` (empty). Plans happen at execution time elsewhere.
- **Never write files yourself** — delegate to the worker subagent.
- **Don't capture conversational text.** Only capture explicit plan-like structures (lists, checkboxes, headers + items). If the conversation is just discussion without a list, ask the user to paste or describe.
- **Dedup against existing backlog.** Before creating a task, check `.logbook/queued/`, `active/`, `paused/` for fuzzy title matches. If one exists, skip and note it.
