---
name: triage
description: >
  Process accumulated inbox items into structured queued tasks. Use when
  the user invokes /logbook:triage or asks to clean up, organize,
  prioritize, or process the inbox. The job is grouping, dedup, and
  discard — NOT planning. Tasks created here are minimal: title +
  source + tags. Plans are produced later by plan mode or whatever
  execution tool picks up the work.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Task
---

# /logbook:triage — Inbox to Backlog

Sort accumulated inbox items into structured queued tasks. **This skill does not generate Plans.** Tasks created here have an empty `## Notes` section; if the user wants planning, that happens later via plan mode or another tool when work is actually picked up.

## Steps

### 1. Read state

Read `.logbook/inbox.md` and `.logbook/index.md`. If inbox has no `- ` lines (just the header), reply `📋 Inbox is empty — nothing to triage.` and stop.

### 2. Build the plan in your head (no writes yet)

For each inbox line, decide:

**Split detection** — does this line contain multiple distinct items? Look for `;`, `, also`, `, and then`, distinct sentences with their own verbs. Bias toward proposing splits — false positives reverse during the confirm step. Don't split bundled noun phrases (`rewrite the auth, refresh, and login flow`) or single observations with qualifiers.

**Discard candidates** — flag obvious noise: `test capture`, `asdf`, `foo`, single words without context, lines that look like commands typed by accident.

**Dedup against existing tasks** — for each candidate, fuzzy-match against tasks in `queued/`, `active/`, `paused/` (use loose semantic match, not just exact title — `auth refresh broken` should match an existing `Fix auth token refresh logic`). If a match exists, suggest "merge into existing task X" rather than creating a duplicate.

**Grouping** — bundle related items by theme (same component, same file area, same bug-vs-feature shape). A single item is a fine group on its own. Lean toward fewer groups — over-grouping is reversible during confirm; under-grouping leaves more files to manage.

**Tag inference** — apply tags per group. Starting vocabulary: `#bug #feature #refactor #ux #perf #docs #test #security #data #system #frontend #backend #debt #chore`. Custom tags are encouraged when they describe the work better.

**Priority** — default `medium`. Bump to `high` if the original inbox text contains urgency words (urgent, broken, prod, asap, breaking, blocker, critical, regression). Drop to `low` for nice-to-haves, polish, or "someday" framing.

### 3. Present the plan in one message

Single scannable summary, ≤80 words. Number everything for reference:

```
📋 Triage: {N} items → {M} tasks ({K} discards, {D} dupes)

Splits proposed:
  Item 2 → would split into 2a, 2b

New tasks (queued/):
  A. {Title}                    items 1, 2a    #frontend #ux
  B. {Title}                    items 2b, 4    #frontend
  C. {Title}                    item 5         #debt    merge into existing 'auth-refresh'?

Discards (remove from inbox → archive):
  ~ items 3, 6 (noise)

Approve all, or call out a change.
```

**If `AskUserQuestion` is in your tool set**, prefer it for the approve/edit prompt (clickable list is faster than typing). Otherwise the inline prompt is fine.

### 4. Accept the response

Interpret intent in natural language — don't expect literal keywords:

| User says | What to do |
|---|---|
| "yes" / "approve" / "looks good" / "go ahead" / "all good" | Apply the entire plan as proposed |
| "change A: rename to X" / "make A about Y" | Modify the named task, leave rest |
| "discard 7" / "drop 7 too" | Add inbox line 7 to discards |
| "keep 6" / "don't discard the test one" | Remove from discards |
| "merge C" / "yeah merge with auth task" | Fold into existing task instead of creating new |
| "regroup" / "those don't belong together" | Rebuild groupings, present updated plan |
| "cancel" / "nevermind" | Stop, write nothing |

For multiple edits in one message, apply them all and re-present the updated plan. Don't loop more than 2-3 rounds — if the user is still iterating, ask: "want me to ship what you've described and we can fix specifics later?"

### 5. Delegate the writes to logbook-worker

**Once the plan is locked, you write nothing yourself.** Hand the entire batch to the `worker` subagent via the `Task` tool with `subagent_type="logbook:worker"`. Pass a precise instruction list — what to create, what to move, what to discard, what to merge.

**Task file content** for new queued tasks (note: NO `## Plan`, NO structured `## Log`):

```
# {Title}

Created: YYYY-MM-DD
Status: queued
Tags: {tags}
Source:
  - {original inbox line 1}
  - {original inbox line 2}
Priority: {priority}

## Notes

```

**Discards** go to `.logbook/abandoned/inbox-discards.md` (single rolling file, gitignored by default). Format: `- YYYY-MM-DD — discarded: {original line}`. Worker creates the file with header `# Discarded inbox items\n\n` if missing.

**Merges** append the merged inbox lines to the existing task's `Source:` section rather than creating a new file.

**Inbox rewrite** at the end: keep the header and any unprocessed lines. Atomic — either the worker runs the whole batch or nothing happens.

### 6. Show the worker's summary

After the worker reports back, render a compact summary:

```
✓ Triaged 8 items → 3 queued, 1 merge, 2 discards
  → queued/2026-04-16_dashboard-up-next.md
  → queued/2026-04-16_pagination-msg-flags.md
  → queued/2026-04-16_haptics.md
  Merged into queued/2026-04-15_auth-refresh.md
  Discarded 2 to abandoned/inbox-discards.md
```

If the worker reported any errors (collision, index out of sync), surface those too — short, no pretending.

## Rules

- **Never generate Plans.** Tasks get `## Notes` (empty). Plans happen at execution time via plan mode or whatever the user uses.
- **Never write files yourself** — always delegate to the worker subagent.
- **One presentation, one ask.** No per-group ping-pong unless the user wants to iterate.
- **Bias toward proposing splits, dedups, discards.** Cheap to override with "keep N", expensive to miss.
- **Preserve original timestamps** in `Source:` for provenance.
- **If the user cancels, write nothing.** Triage is atomic.
