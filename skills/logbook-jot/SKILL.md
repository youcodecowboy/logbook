---
name: logbook-jot
description: >
  Append a quick note, thought, bug, or idea to the logbook inbox at
  `.logbook/inbox.md`. This is zero-friction capture — no triage, no
  classification, no thinking. Use only when the user explicitly invokes
  /jot or asks to "jot down" something. Do not auto-trigger on general
  conversation or ambient observations.
disable-model-invocation: true
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*)
argument-hint: [your note here]
---

# /jot — Quick Capture

Append `$ARGUMENTS` to `.logbook/inbox.md` as a single timestamped line, then return immediately. The whole point of `/jot` is **zero context switch** — the user is mid-thought and just wants the note recorded.

## Steps

1. Get the current local timestamp in `YYYY-MM-DD HH:MM` form. Use `date '+%Y-%m-%d %H:%M'` if you don't already know it.
2. If `.logbook/inbox.md` doesn't exist, create the minimum needed: `mkdir -p .logbook` and write `.logbook/inbox.md` with the header `# Logbook Inbox\n\n`. (Full directory structure can wait — the main `logbook` skill handles complete initialization the next time it activates.)
3. Append a single line to `.logbook/inbox.md`:

   ```
   - YYYY-MM-DD HH:MM — $ARGUMENTS
   ```

4. Reply with one line and nothing else: `📝 Logged to inbox`.

## Rules

- **Do not read other logbook files** (index.md, task files, etc.). Don't even glance. The whole point is no context switch.
- **Do not triage, classify, or interpret the note.** It goes in raw. The user can `/triage` later.
- **Preserve any tags** the user wrote (`#bug`, `#frontend`, etc.). Don't add or remove them.
- **Preserve URL-like content, code snippets, file paths.** Pass through verbatim.
- If `$ARGUMENTS` is empty or whitespace, ask once for the note content, then proceed.
- Never create task files. That's the main skill's job.
