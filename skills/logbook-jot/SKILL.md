---
name: logbook-jot
description: >
  Append a quick note, thought, bug, or idea to the logbook inbox at
  `.logbook/inbox.md`. This is zero-friction capture — no triage, no
  classification, no thinking. Use only when the user explicitly invokes
  /jot or asks to "jot down" something. Do not auto-trigger on general
  conversation or ambient observations.
disable-model-invocation: true
allowed-tools: Read, Write, Bash(mkdir:*)
argument-hint: [note] (or for multi-item: [item; item; item])
---

# /jot — Quick Capture

Append `$ARGUMENTS` to `.logbook/inbox.md` as one or more dated lines, then return immediately. The whole point of `/jot` is **zero context switch** — the user is mid-thought and just wants the note recorded.

## Steps

1. Use today's date in `YYYY-MM-DD` form. You already have it from the system reminder context — no shell call needed. Date-level precision is enough for raw inbox lines; if the user wants exact times for things, they can write them in the note (`/jot 11:42 — deploy went red`).
2. If `.logbook/` doesn't exist, **fully initialize it** (don't leave half a structure behind):
   - `mkdir -p .logbook/queued .logbook/active .logbook/paused .logbook/done .logbook/abandoned`
   - Write `.logbook/inbox.md` with header `# Logbook Inbox\n\n`
   - Write `.logbook/index.md` with:
     ```
     # Logbook Index

     Last updated: YYYY-MM-DD

     | Status | Date | Title | Tags | File |
     |--------|------|-------|------|------|
     ```
   - Write `.logbook/.gitignore` with:
     ```
     # Logbook defaults — edit to taste
     inbox.md
     done/
     abandoned/
     ```
   Initialization is idempotent: only create files/dirs that don't exist, never overwrite.
3. **Split on `;` if present.** If `$ARGUMENTS` contains one or more `;` characters, split on them and treat each non-empty trimmed segment as a separate item. Otherwise, treat the whole input as one item.

   Don't try to be smart about commas, "and", "also", or sentence breaks — that's `/triage`'s job. The semicolon splitter is opt-in: if the user typed `;`, they meant it.

   Caveat: if the note contains semicolons that aren't list separators (code snippets, URLs with `?foo=bar;baz`), it'll over-split. Acceptable trade-off for v0.1 — the user can re-jot or fix in inbox.md directly.

4. For each item (one or many), append a line to `.logbook/inbox.md`:

   ```
   - YYYY-MM-DD — {item}
   ```

   Single-item example:
   ```
   - 2026-04-16 — fix the deploy
   ```

   Multi-item example (`/jot fix dashboard flash; auth refresh is brittle; add loading skeletons`):
   ```
   - 2026-04-16 — fix dashboard flash
   - 2026-04-16 — auth refresh is brittle
   - 2026-04-16 — add loading skeletons
   ```

5. Reply with one line and nothing else:
   - One item: `📝 Logged to inbox`
   - N items: `📝 Logged {N} items to inbox`

   If after splitting and trimming there are zero items (e.g., the user typed `/jot ;;`), ask once for the note content and proceed.

## Rules

- **Do not read other logbook files** (index.md, task files, etc.). Don't even glance. The whole point is no context switch.
- **Do not triage, classify, or interpret the note.** It goes in raw. The user can `/triage` later.
- **Preserve any tags** the user wrote (`#bug`, `#frontend`, etc.). Don't add or remove them.
- **Preserve URL-like content, code snippets, file paths.** Pass through verbatim.
- If `$ARGUMENTS` is empty or whitespace, ask once for the note content, then proceed.
- Never create task files. That's the main skill's job.
