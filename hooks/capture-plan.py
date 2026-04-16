#!/usr/bin/env python3
"""Logbook PostToolUse hook for ExitPlanMode.

Fires after Claude exits plan mode (which happens after the user
accepts a plan). Captures the plan content and decomposes it into
queued task files in .logbook/queued/ inside the project.

Plan content lookup tries (in order):
  1. payload.tool_input.plan        — most likely (model passes plan as a string)
  2. payload.tool_input.markdown    — alternate field name
  3. payload.tool_input.content     — another alternate
  4. ~/.claude/plans/<latest>.md    — fallback (Claude Code persists plans here)

Project dir comes from $CLAUDE_PROJECT_DIR (set by Claude Code per-hook),
falling back to payload.cwd if needed.

Output: writes one line to stdout, which appears as a system message in
the conversation:
  📋 Captured plan: 5 task(s) → .logbook/queued/

Always exits 0. Never blocks user flow. Never raises.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# Headers that look like task headers but are really meta-sections.
META_SECTION_TITLES = {
    "plan", "overview", "goals", "context", "summary", "approach",
    "background", "rationale", "scope", "non-goals", "out of scope",
    "assumptions", "risks", "open questions", "references", "appendix",
    "file structure", "tech stack", "architecture",
}


def get_plan_content(payload: dict) -> str | None:
    """Return the plan content as a markdown string, or None."""
    tool_input = payload.get("tool_input") or {}

    # Path 1-3: direct field in tool_input
    for field in ("plan", "markdown", "content"):
        value = tool_input.get(field)
        if isinstance(value, str) and value.strip():
            return value

    # Path 4: most-recent file in ~/.claude/plans/
    plans_dir = Path.home() / ".claude" / "plans"
    if plans_dir.is_dir():
        try:
            plan_files = sorted(
                plans_dir.glob("*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            plan_files = []

        for plan_file in plan_files[:3]:
            try:
                content = plan_file.read_text(encoding="utf-8")
                if content.strip():
                    return content
            except OSError:
                continue

    return None


def normalize_title(title: str) -> set[str]:
    """Return a set of words for fuzzy matching."""
    cleaned = re.sub(r"[^\w\s]", "", title.lower())
    return set(cleaned.split())


def parse_tasks(plan_content: str) -> list[dict]:
    """Parse plan markdown into discrete tasks.

    Strategy:
      1. If there are H3 headers (### ...) that look like tasks, use them.
      2. Else if there are H2 headers (## ...) that look like tasks, use those.
      3. Else fall back to top-level checkbox lines (- [ ] ...) as standalone tasks.
    """
    lines = plan_content.split("\n")

    # Try H3 sections first (Superpowers uses ### Task N: ...)
    tasks = _parse_by_header_level(lines, level=3)
    if tasks:
        return tasks

    # Then H2
    tasks = _parse_by_header_level(lines, level=2)
    if tasks:
        return tasks

    # Fallback: each top-level checkbox is a task
    tasks = []
    checkbox_re = re.compile(r"^\s*-\s*\[\s*\]\s+(.+?)$")
    for line in lines:
        m = checkbox_re.match(line)
        if not m:
            continue
        title = m.group(1).strip()
        # Strip bold markers like **Step 1: ...**
        title = re.sub(r"^\*\*(.+?)\*\*\s*:?\s*", r"\1: ", title).rstrip(": ")
        # Strip "Step N:" prefix if present
        title = re.sub(r"^(?:Step\s+\d+\s*:?\s*)", "", title, flags=re.IGNORECASE)
        title = title.strip()
        if title and title.lower() not in META_SECTION_TITLES:
            tasks.append({"title": title, "body": ""})
    return tasks


def _parse_by_header_level(lines: list[str], level: int) -> list[dict]:
    header_prefix = "#" * level
    header_re = re.compile(
        rf"^{header_prefix}\s+(?:Task\s+\d+\s*:?\s*)?(.+?)\s*$"
    )
    higher_header_re = re.compile(rf"^#{{{1},{level - 1}}}\s+")

    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []

    for line in lines:
        # Reset on a header at a higher level (encloses our scope)
        if level > 1 and higher_header_re.match(line):
            if current_title is not None:
                sections.append((current_title, current_body))
                current_title = None
                current_body = []
            continue

        h = header_re.match(line)
        if h:
            if current_title is not None:
                sections.append((current_title, current_body))
            current_title = h.group(1).strip()
            current_body = []
        elif current_title is not None:
            current_body.append(line)

    if current_title is not None:
        sections.append((current_title, current_body))

    tasks: list[dict] = []
    for title, body_lines in sections:
        if title.lower() in META_SECTION_TITLES:
            continue
        body = "\n".join(body_lines).strip()
        tasks.append({"title": title, "body": body})

    return tasks


def slugify(text: str, max_length: int = 60) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:max_length] or "untitled"


def find_existing_task(logbook_dir: Path, title: str) -> Path | None:
    """Fuzzy-match a title against existing tasks in queued/active/paused."""
    title_words = normalize_title(title)
    if not title_words:
        return None

    best_match: Path | None = None
    best_score = 0.0

    for folder in ("queued", "active", "paused"):
        folder_path = logbook_dir / folder
        if not folder_path.is_dir():
            continue
        for task_file in folder_path.glob("*.md"):
            try:
                first_line = task_file.read_text(encoding="utf-8").split("\n", 1)[0]
            except OSError:
                continue
            if not first_line.startswith("# "):
                continue
            existing_title = first_line[2:].strip()
            existing_words = normalize_title(existing_title)
            if not existing_words:
                continue
            overlap = len(title_words & existing_words)
            smaller = min(len(title_words), len(existing_words))
            if smaller == 0:
                continue
            score = overlap / smaller
            if score >= 0.7 and score > best_score:
                best_match = task_file
                best_score = score

    return best_match


def write_task(logbook_dir: Path, task: dict, source_note: str) -> Path | None:
    """Create a queued task file. Returns the file path, or None on failure."""
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(task["title"])

    queued_dir = logbook_dir / "queued"
    try:
        queued_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    target = queued_dir / f"{today}_{slug}.md"
    counter = 1
    while target.exists():
        target = queued_dir / f"{today}_{slug}-{counter}.md"
        counter += 1

    body_block = ""
    if task.get("body"):
        body_block = task["body"].strip()

    content = (
        f"# {task['title']}\n\n"
        f"Created: {today}\n"
        f"Status: queued\n"
        f"Tags:\n"
        f"Source: {source_note}\n"
        f"Priority: medium\n\n"
        f"## Notes\n\n"
        f"{body_block}\n"
    )

    try:
        target.write_text(content, encoding="utf-8")
        return target
    except OSError:
        return None


def update_index(logbook_dir: Path, new_files: list[Path]) -> None:
    if not new_files:
        return

    index_path = logbook_dir / "index.md"
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")

    if not index_path.exists():
        try:
            index_path.write_text(
                "# Logbook Index\n\n"
                f"Last updated: {now_iso}\n\n"
                "| Status | Date | Title | Tags | File |\n"
                "|--------|------|-------|------|------|\n",
                encoding="utf-8",
            )
        except OSError:
            return

    try:
        existing = index_path.read_text(encoding="utf-8")
    except OSError:
        return

    existing = re.sub(
        r"Last updated:.*",
        f"Last updated: {now_iso}",
        existing,
        count=1,
    )

    new_rows: list[str] = []
    for path in new_files:
        try:
            first_line = path.read_text(encoding="utf-8").split("\n", 1)[0]
        except OSError:
            continue
        title = first_line[2:].strip() if first_line.startswith("# ") else path.stem
        title_escaped = title.replace("|", "\\|")
        rel_path = f"queued/{path.name}"
        new_rows.append(
            f"| queued | {today} | {title_escaped} |  | {rel_path} |"
        )

    if new_rows:
        existing = existing.rstrip() + "\n" + "\n".join(new_rows) + "\n"

    try:
        index_path.write_text(existing, encoding="utf-8")
    except OSError:
        pass


def find_logbook_dir(start: Path, max_levels: int = 6) -> Path | None:
    for parent in [start, *start.parents][:max_levels]:
        candidate = parent / ".logbook"
        if candidate.is_dir():
            return candidate
    return None


def main() -> int:
    try:
        try:
            payload_str = sys.stdin.read()
        except Exception:
            return 0

        if not payload_str.strip():
            return 0

        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            return 0

        if payload.get("tool_name") != "ExitPlanMode":
            return 0

        # Project root: prefer env var, fallback to payload cwd
        project_dir_str = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
        if not project_dir_str:
            return 0

        project_dir = Path(project_dir_str)
        logbook_dir = find_logbook_dir(project_dir) if project_dir.exists() else None
        if logbook_dir is None:
            # No logbook in this project — silently skip
            return 0

        plan_content = get_plan_content(payload)
        if not plan_content:
            return 0

        tasks = parse_tasks(plan_content)
        if not tasks:
            return 0

        source_note = "captured from plan mode"
        new_files: list[Path] = []
        skipped = 0

        for task in tasks:
            if find_existing_task(logbook_dir, task["title"]):
                skipped += 1
                continue
            written = write_task(logbook_dir, task, source_note)
            if written:
                new_files.append(written)

        if new_files:
            update_index(logbook_dir, new_files)
            msg = f"📋 Captured plan: {len(new_files)} task(s) → .logbook/queued/"
            if skipped:
                msg += f" ({skipped} duplicate(s) skipped)"
            print(msg)
        elif skipped:
            print(f"📋 Plan items already in backlog ({skipped} skipped as duplicates)")

        return 0

    except Exception:
        # Never raise. Exit silently on any unexpected failure.
        return 0


if __name__ == "__main__":
    sys.exit(main())
