---
name: logbook-triage
description: >
  Triage the logbook inbox: read raw captures from `.logbook/inbox.md`, build a
  full triage plan (splits + groupings + discards + tags), present it in one
  message, accept bulk approval or targeted edits, then delegate the file ops
  to the logbook-worker subagent. Use when the user invokes /triage or asks to
  clean up, organize, prioritize, or process the inbox.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Task
---

# /triage — Inbox to Backlog

Process the logbook inbox into structured queued tasks. The flow is **plan once, present once, confirm in bulk, delegate the writes**. Per-item interrogation is exhausting; real users have judgment about whole plans, not just slices.

## Steps

### 1. Read state (no writes yet)

Read `.logbook/inbox.md` (raw captures) and `.logbook/index.md` (existing tasks, so you don't duplicate). If `inbox.md` has no `- ` lines, reply `📋 Inbox is empty — nothing to triage.` and stop.

### 2. Build the full plan (in your head, not on disk)

Produce a single integrated plan covering all of:

**Split detection** — for each inbox line, decide if it's actually multiple items in a trench coat. Look for `;`, `, also`, `, and then`, distinct sentences with their own verbs, multi-line content. Bias toward proposing splits — false positives are reversible during the confirm step. Don't split bundled noun phrases (`rewrite the auth, refresh, and login flow`) or single observations with qualifiers.

**Discard candidates** — flag lines that look like test debris, accidental captures, or obvious noise (`test capture`, `asdf`, `foo`, single words with no context, lines that look like commands typed by mistake). Bias toward suggesting — the user can always say "keep N" if you're wrong.

**Dedup against index** — for each candidate group, check if a similar task already exists in `queued/`, `active/`, or `paused/`. If so, suggest "merge into existing task X" rather than creating a duplicate. Use loose semantic match, not just exact title — `auth refresh broken` should match an existing `Fix auth token refresh logic`.

**Grouping** — bundle related items by theme: same component, same file area, same bug-vs-feature shape. A single item is a fine group on its own — don't force bundles. When in doubt, prefer fewer groups (over-grouping is reversible during confirm; under-grouping means more files to manage).

**Tag inference** — apply tags per group. Starting vocabulary: `#bug #feature #refactor #ux #perf #docs #test #security #data #system #frontend #backend #debt #chore`. Custom tags are encouraged when they describe the work better than starter vocab — preserve them.

**Priority** — default `medium`. Bump to `high` if the original inbox text contains urgency words (urgent, broken, prod, asap, breaking, critical, blocker, regression). Drop to `low` for polish, nice-to-haves, or things explicitly framed as "someday".

### 3. Present the plan in one message

Render a single scannable summary. Number every item so the user can reference them in feedback:

```
📋 Triage plan ({M} items → {N} tasks, {K} discards, {D} possible duplicates)

Splits proposed:
  Item 2 ("main dashboard up next is too flat...") → would split into:
    a. Up Next section needs data richness, iconography, time
    b. Daily brief section needs better styling

New tasks (would create in queued/):

  1. Add data richness to dashboard "Up Next" section
     Tags: #frontend #ux    Priority: medium
     Source: items 2a, 4
     Plan: 4 steps

  2. Add pagination to messages and flags
     Tags: #frontend #ux #debt    Priority: medium
     Source: item 3
     Plan: 4 steps

Discards (would remove from inbox):

  D1. "test capture" — looks like test debris

Possible duplicates:

  X1. Proposed group "auth refresh" overlaps with
      active/2026-04-15_auth-token-refresh.md — merge?

Approve all? Or pick a targeted edit:
  - change 1                   rename, retag, or rewrite a specific task
  - discard 3                  drop another inbox line
  - keep D1                    don't discard the suggested item
  - merge X1                   fold into existing task instead of creating new
  - regroup                    rebuild groupings from scratch
  - cancel                     abort, no changes written
```

**If `AskUserQuestion` is available in your tool set, prefer it** for the final approve/edit prompt — render the choices as a clickable list. The popup pattern is faster to answer than typing free-form. The inline prompt is the fallback.

### 4. Accept the response — bulk or targeted

The user replies in natural language. Interpret intent — don't expect literal keywords:

| User says | What to do |
|---|---|
| "yes" / "approve" / "looks good" / "go ahead" / "all good" / "ship it" | Apply the entire plan as proposed |
| "change 2: rename to X" / "make 2 about Y" / "2 should be tagged debt not ux" | Modify the named task per the change, leave rest |
| "discard 3" / "drop 3 too" / "and 3 is noise" | Add inbox line 3 to discards |
| "keep D1" / "don't discard the test one" / "leave the test capture" | Remove from discards, leave in inbox |
| "merge X1" / "yeah merge with auth task" | Fold the proposed group into the existing task instead of creating new |
| "regroup" / "those don't belong together" / "split 1 and 2" | Rebuild groupings, present an updated plan |
| "cancel" / "nevermind" / "abort" | Stop — make no changes |

For multiple edits in one message ("change 2 to be about Y, discard 3 and 4"), apply all the changes, then **re-present the updated plan and re-ask for approval**. Don't loop more than 2-3 rounds — if the user is still iterating, ask: "want me to create what you've described and we can fix specifics later?"

### 5. Delegate the file ops to logbook-worker

**Once the plan is locked, you do not write any files yourself.** Hand the entire batch to the `logbook-worker` subagent via the Task tool with `subagent_type="logbook:logbook-worker"`. The worker runs in a forked context — its file I/O chatter doesn't eat your main token budget. On a triage of ~10 items into ~5 tasks, that's the difference between a clean conversation and a wall of Write/Edit calls.

**Construct the worker prompt as a precise instruction list.** Template:

> Execute this triage batch on `.logbook/`:
>
> **Create these queued task files** (full content provided below):
>
> Path: `.logbook/queued/2026-04-16_dashboard-up-next-data.md`
> Content:
> ```
> # Add data richness to dashboard "Up Next" section
> Created: 2026-04-16
> Status: queued
> Tags: #frontend #ux
> Source:
>   - 2026-04-16 — main dashboard section "up next" is too flat, needs to be more data rich, ...
> Priority: medium
>
> ## Context
> ...
>
> ## Plan
> - [ ] Audit current data shape feeding the Up Next section
> - [ ] Add iconography per item type (task / meeting / cal event)
> - [ ] Add time/due indicator
> - [ ] Add color treatment + subtitle
>
> ## Log
> ```
>
> Path: `.logbook/queued/2026-04-16_messages-flags-pagination.md`
> Content: ...
>
> **Add rows to `.logbook/index.md`** (insert into the queued block, date desc):
>
> ```
> | queued | 2026-04-16 | Add data richness to dashboard "Up Next" section | #frontend #ux | queued/2026-04-16_dashboard-up-next-data.md |
> | queued | 2026-04-16 | Add pagination to messages and flags | #frontend #ux #debt | queued/2026-04-16_messages-flags-pagination.md |
> ```
>
> Touch the `Last updated:` line.
>
> **Discard these inbox lines** (append each to `.logbook/abandoned/inbox-discards.md` — create the file with header `# Discarded inbox items\n\n` if it doesn't exist, create the `abandoned/` directory if missing):
>
> ```
> - 2026-04-16 — discarded: test capture
> ```
>
> **Rewrite `.logbook/inbox.md`** keeping the `# Logbook Inbox` header and these unprocessed lines (none in this case — remove all that were either turned into tasks or discarded):
>
> ```
> (no remaining lines)
> ```
>
> Reply with a per-file summary when done.

The worker handles all the file I/O. When it returns, render its summary to the user as a single block (see step 6) and stop.

### 6. Final summary to the user

After the worker reports back, show:

```
✓ Triaged 5 items → 3 queued tasks (1 discarded, 0 remaining in inbox)

Created:
  → queued/2026-04-16_dashboard-up-next-data.md
  → queued/2026-04-16_dashboard-styling.md
  → queued/2026-04-16_messages-flags-pagination.md

Discarded: 1 line archived to .logbook/abandoned/inbox-discards.md
```

If the worker reported any errors (file already existed, index out of sync, etc.), surface those too — short, no pretending things worked when they didn't.

## Rules

- **Never write files yourself.** Delegate all file ops to logbook-worker. The only file you read directly is `inbox.md` and `index.md` in step 1.
- **One presentation, one ask.** No per-group ping-pong unless the user explicitly wants to iterate. Real users approve whole plans, not slices.
- **Bias toward proposing splits and discards.** False positives are cheap (user says "keep D1" or "leave 3 as one"). False negatives are expensive (items buried inside conflated tasks, or noise that lives forever in inbox).
- **Preserve original timestamps in `Source:`** of every queued task. Provenance matters when picking up a task three weeks later.
- **One inbox item ≠ always one task.** Single items can become single tasks. Don't force them into bundles.
- **Discards go to `.logbook/abandoned/inbox-discards.md`** as `- YYYY-MM-DD — discarded: {original}` lines. Single rolling file, not one file per discard. The `abandoned/` folder is gitignored by default, so discards stay local unless the user edits their `.logbook/.gitignore`.
- **If the user cancels, write nothing.** Including no partial state. Triage is atomic — either the worker runs the whole batch or nothing happens.
