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
argument-hint: [note] (multi-item is fine — auto-splits, or use `;` to force)
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
3. **Split into items.** Decide whether `$ARGUMENTS` is one thought or several. Two paths:

   **Fast path — explicit `;`.** If the input contains `;` characters, split on them. Each non-empty trimmed segment is one item. The user typed `;` deliberately, so don't second-guess.

   **Smart path — no `;`.** Read the input and decide if it describes one thing or multiple distinct things. Split when distinct, leave whole when bundled. **Bias toward splitting** — the cost of being wrong is one extra "merge these" decision during `/triage`, while the cost of NOT splitting when you should have is items getting buried inside a conflated task that the user discovers later.

   Heuristics that suggest splitting:
   - Multiple complete clauses with their own verbs joined by "also", "and then", "plus", "; and": `fix dashboard flash, also auth refresh is brittle, and we should add skeletons` → 3 items.
   - Distinct sentences: `Settings page flashes white. Auth refresh feels brittle.` → 2 items.
   - Newline-separated lines in pasted multi-line input → one item per non-empty line.

   Heuristics that suggest leaving as one item:
   - A single bundled noun phrase even with commas: `rewrite the auth, refresh, and login flow` → one item (one verb, one bundled object).
   - A single observation with qualifiers: `the deploy is red because the migration timed out and rolled back` → one item (one event with explanation).
   - Code snippets, URLs, or quoted text containing punctuation that looks like delimiters → one item.

   When uncertain, lean toward splitting. Triage can always re-group; un-splitting from a buried task is harder.

   **Strip leading connectives** when smart-splitting. After splitting, items 2+ may begin with sentence-connecting words that were meaningful in the original input but read awkwardly standalone. Strip leading `Also,` / `And,` / `Plus,` / `Then,` / `Then also,` (case-insensitive, with the trailing comma+space) from items 2+. The first item never gets stripped — it didn't have a connector to begin with.

   Example: `/jot fix the dashboard. Also auth refresh is brittle` → items become `["fix the dashboard", "auth refresh is brittle"]`, not `["fix the dashboard", "Also auth refresh is brittle"]`.

   Caveat: if a note contains real semicolons that aren't list separators (code snippets, URLs with `?foo=bar;baz`), the explicit fast path will over-split. Acceptable trade-off — the user can re-jot or edit `inbox.md` directly.

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

5. Reply with a short confirmation that **shows what was logged** so the user has a glance-able record without opening `inbox.md`:

   - One item:
     ```
     📝 Logged to inbox: {item, truncated to ~80 chars with … if longer}
     ```

   - Multiple items:
     ```
     📝 Logged {N} items to inbox:
       1. {item 1, truncated to ~80 chars}
       2. {item 2, truncated to ~80 chars}
       ...
     ```

   Truncate any item longer than ~80 chars with a trailing `…`. The point is confirmation that the right things landed — not a paragraph back. Keep it tight.

   If after splitting and trimming there are zero items (e.g., the user typed `/jot ;;`), ask once for the note content and proceed.

## Rules

- **Do not read other logbook files** (index.md, task files, etc.). Don't even glance. The whole point is no context switch.
- **Do not triage, classify, or interpret the note.** It goes in raw. The user can `/triage` later.
- **Preserve any tags** the user wrote (`#bug`, `#frontend`, etc.). Don't add or remove them.
- **Preserve URL-like content, code snippets, file paths.** Pass through verbatim.
- If `$ARGUMENTS` is empty or whitespace, ask once for the note content, then proceed.
- Never create task files. That's the main skill's job.
