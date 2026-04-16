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
3. **Split detection pass (do this before grouping).** Scan each inbox line for ones that look like they contain multiple distinct items — delimited by `;`, `, also `, `, and then `, comma followed by a clause that could stand alone, or distinct sentences. For each candidate, propose a split:

   ```
   This inbox line looks like multiple items:
     - 2026-04-16 — fix the dashboard flash, also the auth refresh logic feels brittle, and we should add loading skeletons

   I'd split it into:
     1. fix the dashboard flash
     2. the auth refresh logic feels brittle
     3. should add loading skeletons

   Sound right? (yes / adjust the splits / leave as one)
   ```

   On `yes` → treat the split items as separate virtual inbox items going into the grouping step.
   On `adjust` → let the user describe the splits they want.
   On `leave as one` → keep the line as a single item.

   **Be willing to propose splits** — false positives are cheap (the user just says "leave as one"). False negatives are expensive (one task ends up conflating three things and the user has to clean it up later). But don't auto-split without asking — bundled-concept lines like `rewrite the auth, refresh, and login flow` are real.

   Don't rewrite `inbox.md` yet — keep the split state in memory until the whole triage pass is done, then rewrite once at the end (step 7).

4. Look at all items (split + un-split) and propose groupings by theme — component (auth, dashboard, settings), feature area, file path, bug-vs-feature, etc. **A single item can be its own group.** Don't force-fit everything into multi-item bundles.
5. For each proposed group, present a short summary to the user:

   ```
   I'd group these {N} items into a task:

     Title: {proposed title}
     Tags:  #tag1 #tag2
     Items:
       - 2026-04-16 — {note}
       - 2026-04-16 — {note}

   Sound right? (you can say yes / rename it / change the grouping / skip it)
   ```

6. **Wait for the user's response before creating the file.** The user will reply in natural language — interpret intent, don't expect literal keywords:
   - **Affirmative** ("yes", "yeah", "sounds good", "go for it", "looks right") → create the task file in `.logbook/queued/`, update `.logbook/index.md`, mark these items as processed.
   - **Rename** ("call it 'auth cleanup' instead", "rename to X", "use 'fix dashboard' as the title") → create with the new title.
   - **Regroup** ("split that one out", "merge with the next group", "those don't belong together", "1 and 3 should be one task") → re-propose the grouping based on what they said.
   - **Skip** ("nope", "skip it", "leave that for later", "not now") → leave items in inbox, move to next group.
   - **Unclear** → ask one focused clarifying question, then proceed.
7. Repeat for each remaining group.
8. **Rewrite `.logbook/inbox.md` once at the end** — remove processed lines (including the originals of any lines that got split in step 3), keep unprocessed ones, keep the `# Logbook Inbox` header. If the user split a line but only some of the resulting sub-items got processed, write the unprocessed sub-items back as new inbox lines (with today's date prefix) so they're not lost.
9. Print final summary: `Triaged {N} items into {M} tasks. {K} item(s) remain in inbox.`

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
