---
name: review
description: >
  Reconcile open logbook items (tasks AND inbox lines) against recent
  git history. Use when the user invokes /logbook:review OR asks "what
  have I actually done" / "did I forget to mark anything done" / "scan
  recent commits for completed tasks" / "reconcile my backlog with
  git" — they want evidence-based detection of items that have been
  completed in the code but not marked done in logbook. Scans both
  open tasks (queued/active/paused) AND inbox lines. Surfaces
  candidates with evidence + confidence; never moves files without
  user confirmation.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(git log:*), Bash(git diff:*), Bash(git show:*), Bash(git rev-parse:*), Task
argument-hint: [time window like "7d", "1w", "since:HEAD~10" — defaults to "7d"]
---

# /logbook:review — Reconcile Backlog ↔ Git History

Scan recent commits to find logbook items (tasks AND inbox lines) that are *actually* completed (or in-progress) in the codebase but not yet reflected in the backlog. This is the catch-up loop for everything that didn't go through TodoWrite or `/done` — manual coding, work by other developers, multi-session workflows, and especially inbox lines that got addressed quickly without ever being triaged.

## Steps

### 1. Verify environment

- Check we're in a git repo: `git rev-parse --git-dir` (silently). If not, reply: `📋 No git repo here — /review needs git history to scan against. Use /logbook:status to see open tasks instead.` and stop.
- Check `.logbook/` exists. If not, suggest creating tasks first.

### 2. Determine the time window

- If `$ARGUMENTS` is empty: default to **7 days**.
- If `$ARGUMENTS` is `Nd` or `Nw` (e.g., "1d", "30d", "2w"): use that as `--since`.
- If `$ARGUMENTS` starts with `since:` (e.g., "since:HEAD~10"): pass directly as `git log <ref>..HEAD`.
- If unclear: ask once.

### 3. Pull git history

Get recent commits with messages and changed files:

```bash
git log --since="<window>" --pretty=format:'%h %s' --name-only
```

Or for `since:HEAD~N`:

```bash
git log HEAD~N..HEAD --pretty=format:'%h %s' --name-only
```

If the window has zero commits, reply: `📋 No commits in the last <window> — nothing to review against.` and stop.

For commits with messages that look obviously interesting (longer than a stub, contain action verbs), optionally `git show --stat <hash>` to get a fuller picture. Don't pull full diffs unless needed for ambiguous matches — they're expensive in tokens.

### 4. Read open tasks AND inbox

**Tasks** — read every task in `.logbook/queued/`, `.logbook/active/`, `.logbook/paused/`. For each, capture:
- Title
- Tags
- Source (often contains file paths or feature names)
- Notes (may have additional context)

Skip done/ and abandoned/ — those are already terminal.

**Inbox** — read `.logbook/inbox.md` and parse each `- YYYY-MM-DD — <text>` line. Inbox items are raw and unstructured, so the only signal you have is the line text itself + the date. Inbox lines are *especially* worth reviewing because they capture quick reactions ("fix the dashboard flash") that often get addressed casually without being triaged into formal tasks — they're the highest-volume source of "silent completion" drift.

### 5. Match commits to items (tasks AND inbox)

For each open task AND each inbox line, look for evidence in the commits. Same matching heuristics for both, but track them separately for the output.

**HIGH confidence signals (suggest move):**
- Commit message contains the task's title (or strongly synonymous phrasing)
- Commit message contains keywords from the task that aren't generic (`auth refresh` → high; `fix bug` → low because too generic)
- Commit message uses standard completion verbs ("implement", "add", "fix", "complete") + matches task scope
- Files in commit overlap with files mentioned in task's Source or Notes
- Multiple commits collectively cover the task's scope

**MEDIUM confidence signals (mention, don't auto-suggest):**
- Partial keyword overlap, but commit message says "wip", "draft", "partial"
- Commit touches files that *might* be related but no scope match
- Task mentions a feature area that has commits but no specific implementation evidence

**LOW confidence / no signal:**
- No commit message keywords match
- No file paths overlap with task

Also flag — but separately — tasks that look **in-progress but not yet active**:
- Task is in `queued/` BUT recent commits show work has begun on its scope
- Suggest: move queued/ → active/

**For inbox lines specifically:** be slightly more cautious — inbox lines are short and matchable against many things by accident. Bump a HIGH match down to MEDIUM if the inbox text is under ~5 words AND there's no file-path corroboration. The cost of incorrectly removing an inbox line is small (user can re-jot) but accuracy still matters.

### 6. Present the findings

Render in this exact layout. Group by **source** (tasks vs inbox) and **confidence** so the user can scan + bulk-approve quickly:

```
📋 Reviewed <N> commits (last <window>) vs <M> open tasks + <K> inbox items

── TASKS ──

✓ HIGH confidence — looks completed:

  1. "<task title>" [<current state>]
     Evidence: commit <hash> "<message>"
              touched <file/path> (matches Source)
     → Suggest: move <state>/ → done/

  2. "<task title>" [<current state>]
     Evidence: <commit> + <commit>
     → Suggest: move <state>/ → done/

⚠ MEDIUM confidence — possibly in flight:

  3. "<task title>" [queued]
     Evidence: commit <hash> "<message>" — partial signal
     → Suggest: move queued/ → active/ (work has begun)

? NO signal — still open:

  (4 tasks left as-is)

── INBOX ──

✓ HIGH confidence — looks addressed:

  4. "fix the dashboard flash"  (jotted 2026-04-15)
     Evidence: commit <hash> "fix(dashboard): initial render flash on theme load"
              touched src/components/Dashboard.tsx
     → Suggest: remove from inbox (archive to abandoned/inbox-discards.md)

  5. "auth token refresh feels brittle"  (jotted 2026-04-14)
     Evidence: commit <hash> "fix: handle concurrent auth token refresh"
     → Suggest: remove from inbox (archive)

⚠ MEDIUM confidence:

  (1 inbox item with partial signal — left in inbox)

? NO signal:

  (3 inbox items left as-is)

Apply HIGH suggestions for tasks (1, 2) and inbox (4, 5)? Or:
  - "yes" / "all" — apply all HIGH
  - "tasks only" / "inbox only" — apply HIGH from one section
  - "include medium" — apply HIGH + MEDIUM (both sections)
  - "1, 3, 5" — apply specific candidates by number
  - "no" / "cancel" — make no changes
```

If there are zero candidates at any confidence level: `📋 No state changes suggested — your backlog and inbox match recent git activity.` Stop.

If a section is empty (e.g., no inbox items, or no inbox matches), omit that section's header rather than printing an empty block.

### 7. Accept response

Interpret natural language:

| User says | Action |
|---|---|
| "yes" / "all" / "approve" / "go ahead" | Apply HIGH-confidence suggestions across both sections |
| "tasks only" / "just tasks" | Apply HIGH from tasks section only; leave inbox untouched |
| "inbox only" / "just inbox" | Apply HIGH from inbox section only; leave tasks untouched |
| "include medium" / "yes all including medium" | Apply HIGH + MEDIUM (both sections) |
| "1, 3, 5" / "just 1 and 2" | Apply specific candidates by number |
| "skip 4" / "all except 4" | Apply suggested minus exclusions |
| "no" / "cancel" / "nevermind" | Stop with no changes |

### 8. Delegate moves to the worker

For each approved candidate, dispatch a precise instruction to the worker via `Task` with `subagent_type="logbook:worker"`. Build them as a single batch covering both task moves AND inbox cleanups:

> Apply these state changes to `.logbook/`:
>
> **Task moves:**
> - Move `.logbook/active/<file1>.md` to `.logbook/done/<file1>.md`. Update Status: to `done`. Update index.md row.
> - Move `.logbook/queued/<file2>.md` to `.logbook/done/<file2>.md`. Update Status: to `done`. Update index.md row.
> - Move `.logbook/queued/<file3>.md` to `.logbook/active/<file3>.md`. Update Status: to `active`. Update index.md row.
>
> For each moved task, append a one-liner to the file's `## Notes` section:
> `Reconciled <YYYY-MM-DD> via /logbook:review — <commit hash>: "<commit message>"`
>
> **Inbox cleanups:**
> - Remove these lines from `.logbook/inbox.md` (preserve all other lines and the header):
>   - `- 2026-04-15 — fix the dashboard flash`
>   - `- 2026-04-14 — auth token refresh feels brittle`
>
> - Append these lines to `.logbook/abandoned/inbox-discards.md` (create file with header `# Discarded inbox items\n\n` if missing, create abandoned/ directory if missing):
>   - `- 2026-04-17 — completed via abc123: "fix(dashboard): initial render flash on theme load" (was: "fix the dashboard flash")`
>   - `- 2026-04-17 — completed via def456: "fix: handle concurrent auth token refresh" (was: "auth token refresh feels brittle")`
>
> Touch the index.md `Last updated:` line.

The Notes annotation on tasks AND the discard line format on inbox both preserve *why* these were moved, so users (and future reviews) understand the provenance — and inbox-discards retains both the original capture and the completing commit for audit.

### 9. Show summary

After the worker reports back, render compact:

```
✓ Reviewed: 5 changes applied (3 task moves, 2 inbox cleanups)

Tasks:
  → done/    "<title>"   (commit 4e30398)
  → done/    "<title>"   (commit a7f2c1d)
  → active/  "<title>"   (commit 9b3e4f1)

Inbox:
  → discarded "fix the dashboard flash"   (commit abc123)
  → discarded "auth token refresh feels brittle"  (commit def456)

Run /logbook:status to see updated state.
```

Omit either section if it's empty.

## Heuristics for matching

The matching is the heart of this skill. Some practical guidance:

**Use the task's full content, not just its title.** A task titled "Add upload retry" with a Source mentioning `src/lib/upload-retry.ts` matches a commit touching that file very strongly, even if the message is just "fix bug."

**Be skeptical of generic commit messages.** "fix bug", "wip", "update", "cleanup" — these match too many things. Require additional file-path or keyword evidence before rating HIGH.

**Group related commits.** A feature often spans multiple commits. If commits A, B, C all touch the same files and cumulatively match a task, treat it as one signal not three.

**Respect the Blocked field.** If a task has a `Blocked:` field, be more conservative — the task was waiting on something. A commit might be partial work toward unblocking, not completion. Default to MEDIUM at most.

**Tags as secondary signal.** A task tagged `#frontend` shouldn't be marked done by a commit that only touched backend files. Use tags as a sanity-check filter.

**Inbox lines need extra skepticism.** They're shorter, less structured, and more matchable-by-accident than tasks. For an inbox line under ~5 words with no file-path corroboration, demote HIGH to MEDIUM. The cost of an over-eager inbox cleanup is recoverable (user can `/jot` it back) but accuracy still matters.

## Rules

- **Always confirm before moving files.** Even HIGH confidence requires explicit user yes (or "all" / "tasks only" / "inbox only"). The cost of a wrong move is bigger than the cost of an extra prompt.
- **Never run destructive git operations.** Only `git log`, `git show`, `git diff` (read-only). Never `git reset`, `git checkout`, anything that modifies state.
- **Annotate moved tasks AND inbox cleanups** with the reconciliation reason. Tasks get a Notes line; inbox items get a discard line in `abandoned/inbox-discards.md` that includes the original capture text + the completing commit. Provenance matters when someone later wonders "why did this move?"
- **Skip done/ and abandoned/ tasks** — those are terminal states. Don't try to reconcile them backward.
- **Inbox is in scope.** Lines in `.logbook/inbox.md` get reviewed alongside tasks. Completed inbox items are removed from `inbox.md` and archived to `abandoned/inbox-discards.md`.
- **Time-bounded scan.** Don't try to scan all of git history by default — 7d is the right balance of "catches recent work" without "thousands of commits to reason over."
- **Never write files yourself** — always delegate to the worker.
- **Read-only git access.** The Bash allowlist for this skill is `git log`, `git diff`, `git show`, `git rev-parse` only. No state-changing git commands.
