---
name: start
description: >
  Start a new tracked task in the logbook with an explicit description.
  Use when the user invokes /logbook:start <task description> or
  explicitly says "start a new task" / "track this work" / "begin tracking
  X" — they want to begin tracked work that isn't already in queued/.
  Creates a task file directly in active/. For pulling from the queue,
  use /logbook:next instead.
disable-model-invocation: true
allowed-tools: Read, Glob, Task
argument-hint: [task description]
---

# /logbook:start — Start a New Tracked Task

Create a new tracked task with the user's description and place it in `.logbook/active/` (since the user is starting work now, not queuing it).

## Steps

1. **If `$ARGUMENTS` is empty**, ask the user what they want to start tracking. One sentence is fine — they can refine later by editing the task's `## Notes` section.

2. **Check for an obvious duplicate** in `.logbook/queued/` and `.logbook/active/`. If a fuzzy-matching task exists in queued/, suggest moving it to active/ instead of creating a new one. If one already exists in active/, point at it and ask if they want a separate task or to continue that one. Don't be pedantic — only flag when the match is clear.

3. **Delegate to the worker subagent.** Use the `Task` tool with `subagent_type="logbook:worker"`. Pass an instruction like:

   > Initialize `.logbook/` if missing. Create a new task file at
   > `.logbook/active/<YYYY-MM-DD>_<kebab-slug>.md` with this content:
   >
   > ```
   > # <Title>
   >
   > Created: <YYYY-MM-DD>
   > Status: active
   > Tags: <inferred tags>
   > Source: started manually
   > Priority: medium
   >
   > ## Notes
   >
   > ```
   >
   > Add a row to `.logbook/index.md` (active block, top). Touch the `Last updated:` line.

4. **Reply with one line.** `📋 Started: <title>`. Then get out of the way — the user (or whatever execution tool they use) takes it from here.

## Tag inference

Use the same starter vocabulary as triage: `#bug #feature #refactor #ux #perf #docs #test #security #data #system #frontend #backend #debt #chore`. Infer 1-3 from the title. Custom tags fine. Leave the Tags field blank if you really can't tell — the user can edit later.

## Rules

- **Goes directly to active/, not queued/.** The semantic of /logbook:start is "I'm beginning this work now." If the user wants to queue something for later, that's `/logbook:jot` (raw) followed by `/logbook:triage` (structured), or letting plan mode capture do it.
- **No Plan generation.** Tasks have `## Notes` (empty). Plans happen at execution time elsewhere.
- **Never write files yourself** — always delegate to the worker subagent.
- **One-liner reply.** Don't editorialize about what to do next; the execution tool handles that.
