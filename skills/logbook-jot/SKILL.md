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
argument-hint: [your note here]
---

# /jot — Quick Capture

Append `$ARGUMENTS` to `.logbook/inbox.md` as a single dated line, then return immediately. The whole point of `/jot` is **zero context switch** — the user is mid-thought and just wants the note recorded.

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
3. Append a single line to `.logbook/inbox.md`:

   ```
   - YYYY-MM-DD — $ARGUMENTS
   ```

4. Reply with one line and nothing else: `📝 Logged to inbox`.

## Rules

- **Do not read other logbook files** (index.md, task files, etc.). Don't even glance. The whole point is no context switch.
- **Do not triage, classify, or interpret the note.** It goes in raw. The user can `/triage` later.
- **Preserve any tags** the user wrote (`#bug`, `#frontend`, etc.). Don't add or remove them.
- **Preserve URL-like content, code snippets, file paths.** Pass through verbatim.
- If `$ARGUMENTS` is empty or whitespace, ask once for the note content, then proceed.
- Never create task files. That's the main skill's job.
