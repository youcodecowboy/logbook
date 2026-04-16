#!/usr/bin/env python3
"""Logbook PostToolUse hook for TodoWrite.

Mirrors TodoWrite STATE CHANGES into .logbook/ folders. Status maps:
  pending      → queued/
  in_progress  → active/
  completed    → done/

UPDATE-ONLY policy (since v0.2.1):
  For each todo, fuzzy-match against existing logbook tasks. If matched
  AND the status changed, move the task file to the corresponding
  folder. If no existing task matches, the todo is IGNORED — we do not
  create new task files from TodoWrite.

The reason: TodoWrite is used for two different things at the same
surface — top-level durable work ("Polish dashboard sections") AND
tactical within-execution breakdowns ("Task 1a: refactor inner loop").
Mirroring everything creates one logbook file per tactical sub-step,
which pollutes the backlog. Updating only what already exists keeps the
mirror useful (state stays in sync with execution) without polluting
(sub-steps that were never logbook tasks stay invisible).

If a user genuinely wants to add new top-level work mid-conversation,
the right primitive is `/logbook:jot` (manual capture) or plan mode
(structured capture). TodoWrite is for state updates on tracked work,
not for capturing new work.

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


def update_index_for_changes(
    logbook_dir: Path,
    moves: list[tuple[Path, Path, str]],
) -> None:
    """Rewrite affected rows in index.md after file moves."""
    if not moves:
        return

    index_path = logbook_dir / "index.md"
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not index_path.exists():
        # No index to update — and we don't create from TodoWrite.
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

    # Rewrite the matching row's status column and path column.
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

            # UPDATE-ONLY policy: no existing match → ignore.
            # Tactical TodoWrite sub-steps that aren't already tracked
            # in logbook should not pollute the backlog. The right way
            # to add new work is /logbook:jot or plan mode.
            if not existing:
                continue

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

        update_index_for_changes(logbook_dir, moves)

        for msg in announcements[:3]:
            print(msg)
        if len(announcements) > 3:
            print(f"📋 +{len(announcements) - 3} more state change(s)")

        return 0

    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
