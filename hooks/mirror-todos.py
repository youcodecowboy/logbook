#!/usr/bin/env python3
"""Logbook PostToolUse hook for TodoWrite.

Mirrors the current TodoWrite state to .logbook/ folders. Status maps:
  pending      → queued/
  in_progress  → active/
  completed    → done/

For each todo, fuzzy-matches against existing logbook tasks (by title
similarity, ≥70% word overlap on the smaller title). If matched, moves
the file to the corresponding folder if status changed. If no match,
creates a new task file in the target folder.

The hook receives the FULL current todos array on every TodoWrite call
(not deltas). So we sync logbook to match the latest state.

Output: emits one-line `📋 Started: <title>` / `📋 Wrapped: <title>`
messages on actual file moves. Skips no-op syncs to avoid chat spam.
Caps at 3 announcements per call (prints `📋 +N more state change(s)`
if more).

Always exits 0. Never blocks. Never raises.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


STATUS_TO_FOLDER = {
    "pending": "queued",
    "in_progress": "active",
    "completed": "done",
}

ALL_FOLDERS = ("queued", "active", "paused", "done", "abandoned")


def slugify(text: str, max_length: int = 60) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:max_length] or "untitled"


def normalize_title(title: str) -> set[str]:
    cleaned = re.sub(r"[^\w\s]", "", title.lower())
    return set(cleaned.split())


def find_matching_task(logbook_dir: Path, todo_content: str) -> Path | None:
    """Find an existing task file whose title fuzzy-matches the todo."""
    todo_words = normalize_title(todo_content)
    if not todo_words:
        return None

    best_match: Path | None = None
    best_score = 0.0

    for folder in ALL_FOLDERS:
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
            overlap = len(todo_words & existing_words)
            smaller = min(len(todo_words), len(existing_words))
            if smaller == 0:
                continue
            score = overlap / smaller
            if score >= 0.7 and score > best_score:
                best_match = task_file
                best_score = score

    return best_match


def update_status_field(file_path: Path, new_status: str) -> None:
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return
    new_content = re.sub(
        r"^Status:\s*\w+",
        f"Status: {new_status}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if new_content != content:
        try:
            file_path.write_text(new_content, encoding="utf-8")
        except OSError:
            pass


def move_task(file_path: Path, target_folder: Path, new_status: str) -> Path | None:
    try:
        target_folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    new_path = target_folder / file_path.name
    if file_path.resolve() == new_path.resolve():
        return None
    if new_path.exists():
        # Filename collision in target folder — give it a suffix
        stem, ext = new_path.stem, new_path.suffix
        counter = 1
        while new_path.exists():
            new_path = target_folder / f"{stem}-{counter}{ext}"
            counter += 1
    try:
        file_path.rename(new_path)
    except OSError:
        return None
    update_status_field(new_path, new_status)
    return new_path


def create_task(logbook_dir: Path, todo: dict, target_folder_name: str) -> Path | None:
    title = (todo.get("content") or "").strip()
    if not title:
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    target_folder = logbook_dir / target_folder_name
    try:
        target_folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    target = target_folder / f"{today}_{slug}.md"
    counter = 1
    while target.exists():
        target = target_folder / f"{today}_{slug}-{counter}.md"
        counter += 1

    status_label = "queued" if target_folder_name == "queued" else target_folder_name

    content = (
        f"# {title}\n\n"
        f"Created: {today}\n"
        f"Status: {status_label}\n"
        f"Tags:\n"
        f"Source: captured from TodoWrite\n"
        f"Priority: medium\n\n"
        f"## Notes\n\n"
    )

    try:
        target.write_text(content, encoding="utf-8")
        return target
    except OSError:
        return None


def update_index_for_changes(
    logbook_dir: Path,
    moves: list[tuple[Path, Path, str]],
    creates: list[tuple[Path, str]],
) -> None:
    if not moves and not creates:
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

    # For moves: rewrite the matching row's status column and path column.
    for old_path, new_path, new_status in moves:
        old_rel = re.escape(f"{old_path.parent.name}/{old_path.name}")
        new_rel = f"{new_path.parent.name}/{new_path.name}"
        # Match: | <status> | <date> | <title> | <tags> | <old_rel> |
        row_re = re.compile(
            r"\|\s*\w+\s*\|([^|]+)\|([^|]+)\|([^|]+)\|\s*" + old_rel + r"\s*\|"
        )
        existing = row_re.sub(
            lambda m: f"| {new_status} |{m.group(1)}|{m.group(2)}|{m.group(3)}| {new_rel} |",
            existing,
        )

    # For creates: append rows.
    new_rows: list[str] = []
    for path, status in creates:
        try:
            first_line = path.read_text(encoding="utf-8").split("\n", 1)[0]
        except OSError:
            continue
        title = first_line[2:].strip() if first_line.startswith("# ") else path.stem
        title_escaped = title.replace("|", "\\|")
        rel_path = f"{path.parent.name}/{path.name}"
        new_rows.append(
            f"| {status} | {today} | {title_escaped} |  | {rel_path} |"
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

        if payload.get("tool_name") != "TodoWrite":
            return 0

        project_dir_str = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
        if not project_dir_str:
            return 0

        project_dir = Path(project_dir_str)
        logbook_dir = find_logbook_dir(project_dir) if project_dir.exists() else None
        if logbook_dir is None:
            return 0

        todos = (payload.get("tool_input") or {}).get("todos") or []
        if not todos:
            return 0

        moves: list[tuple[Path, Path, str]] = []
        creates: list[tuple[Path, str]] = []
        announcements: list[str] = []

        for todo in todos:
            content = (todo.get("content") or "").strip()
            if not content:
                continue

            status = todo.get("status", "pending")
            target_folder_name = STATUS_TO_FOLDER.get(status, "queued")
            target_status = (
                "queued" if target_folder_name == "queued" else target_folder_name
            )

            existing = find_matching_task(logbook_dir, content)

            if existing:
                current_folder = existing.parent.name
                if current_folder == target_folder_name:
                    continue  # No change needed
                target_folder = logbook_dir / target_folder_name
                new_path = move_task(existing, target_folder, target_status)
                if new_path:
                    moves.append((existing, new_path, target_status))
                    truncated = content[:60] + ("…" if len(content) > 60 else "")
                    if status == "in_progress":
                        announcements.append(f"📋 Started: {truncated}")
                    elif status == "completed":
                        announcements.append(f"📋 Wrapped: {truncated}")
            else:
                created = create_task(logbook_dir, todo, target_folder_name)
                if created:
                    creates.append((created, target_status))

        update_index_for_changes(logbook_dir, moves, creates)

        for msg in announcements[:3]:
            print(msg)
        if len(announcements) > 3:
            print(f"📋 +{len(announcements) - 3} more state change(s)")

        return 0

    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
