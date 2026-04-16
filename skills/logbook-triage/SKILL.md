---
name: logbook-triage
description: >
  Triage the logbook inbox: read raw captures from `.logbook/inbox.md`, group
  related items, and (with user confirmation) promote them into structured
  task files in `.logbook/queued/`. Use when the user invokes /triage or asks
  to clean up, organize, prioritize, or process the inbox.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(mkdir:*), Bash(mv:*), Bash(date:*)
---

# /triage — Promote Inbox to Queued

Group raw inbox items into structured tasks the user can pick up later. This is the human-in-the-loop step — grouping is a structuring decision, and structuring decisions need user confirmation.

## Steps

1. Read `.logbook/inbox.md`. If there are no `- ` lines (just the header), reply `📋 Inbox is empty — nothing to triage.` and stop.
2. Read `.logbook/index.md` so you don't accidentally duplicate tasks already in `queued/`, `active/`, or `paused/`.
3. Look at the inbox items and propose groupings by theme — component (auth, dashboard, settings), feature area, file path, bug-vs-feature, etc. **A single item can be its own group.** Don't force-fit everything into multi-item bundles.
4. For each proposed group, present a short summary to the user:

   ```
   I'd group these {N} items into a task:

     Title: {proposed title}
     Tags:  #tag1 #tag2
     Items:
       - 2026-04-16 — {note}
       - 2026-04-16 — {note}

   Sound right? (you can say yes / rename it / change the grouping / skip it)
   ```

5. **Wait for the user's response before creating the file.** The user will reply in natural language — interpret intent, don't expect literal keywords:
   - **Affirmative** ("yes", "yeah", "sounds good", "go for it", "looks right") → create the task file in `.logbook/queued/`, update `.logbook/index.md`, mark these items as processed.
   - **Rename** ("call it 'auth cleanup' instead", "rename to X", "use 'fix dashboard' as the title") → create with the new title.
   - **Regroup** ("split that one out", "merge with the next group", "those don't belong together", "1 and 3 should be one task") → re-propose the grouping based on what they said.
   - **Skip** ("nope", "skip it", "leave that for later", "not now") → leave items in inbox, move to next group.
   - **Unclear** → ask one focused clarifying question, then proceed.
6. Repeat for each remaining group.
7. Rewrite `.logbook/inbox.md` to remove processed lines (keep unprocessed ones, keep the `# Logbook Inbox` header).
8. Print final summary: `Triaged {N} items into {M} tasks. {K} item(s) remain in inbox.`

## Task file format (for queued items)

Use the same template as the main `logbook` skill, with `Status: queued` and an empty `## Log` section. Critical: include the original inbox lines in the Source so provenance is preserved:

```
# {Title}

Created: YYYY-MM-DD HH:MM
Status: queued
Tags: #tag1 #tag2
Source:
  - 2026-04-16 10:45 — {original inbox line}
  - 2026-04-16 11:15 — {original inbox line}
Priority: medium

## Context

{2-3 sentences synthesizing what these items are about and why they belong together.}

## Plan

- [ ] {step 1 — best guess, the user can refine when they pick this up}
- [ ] {step 2}
- [ ] {step 3}

## Log

```

Filename: `YYYY-MM-DD_kebab-title.md`. Use today's date.

## Plan generation

Draft 2-5 tentative steps based on what the items describe. You're not committing to the implementation here — you're making the task actionable enough that someone (probably the user, possibly a future Claude session) can pick it up and start without having to think hard.

If you genuinely can't think of meaningful steps, write a single step like `- [ ] Investigate and define approach` and note in Context what's unclear.

## Batching when there are many items

If the inbox has more than ~15 items, process in batches of 5-7 groupings at a time. Show the user the first batch, get confirmations, create those files, then propose the next batch. Don't dump 20 yes/no prompts at once — that's exhausting.

## Rules

- **Never silently move items to queued.** Confirmation per task. Triage is not bookkeeping.
- **Preserve original timestamps in Source.** Provenance matters when you're trying to remember why something is in the backlog three weeks later.
- **One inbox item ≠ always one task.** It's also fine for one inbox item to become its own queued task. The grouping is judgment, not algorithm.
- **Don't delete the inbox header.** When rewriting `inbox.md`, keep `# Logbook Inbox\n\n` and any unprocessed items beneath it.
