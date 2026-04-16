#!/usr/bin/env python3
"""Logbook PreCompact hook.

Runs before Claude Code compacts the conversation context. Walks
.logbook/active/ in the user's working directory and:

  1. Appends a [compaction checkpoint] entry to any active task file
     that's been worked on recently (mtime within the last hour). This
     gives the post-compaction agent a visible marker that earlier log
     entries may be incomplete and to resume from the last unchecked
     Plan step.
  2. Writes .logbook/.last-session-state with a JSON snapshot of active
     task paths and the timestamp, for the main logbook skill to read
     on the next session start.

Design notes
------------
- The hook is a separate process. It cannot read conversation context.
  It works only with file state. The actual progress logging during
  work is the skill's job; this hook is a safety net that marks
  potential gaps.
- The hook MUST NOT block compaction. It exits 0 on every error path.
- The hook walks upward from CWD a few levels in case Claude was
  invoked from a subdirectory of the project root.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def find_logbook_dir(start: Path, max_levels: int = 6) -> Path | None:
    """Walk up from `start` looking for a `.logbook/` directory."""
    for parent in [start, *start.parents][:max_levels]:
        candidate = parent / ".logbook"
        if candidate.is_dir():
            return candidate
    return None


def main() -> int:
    try:
        # Drain stdin so Claude Code's hook IPC doesn't error if it
        # tried to send us a payload. We don't need the contents.
        try:
            if not sys.stdin.isatty():
                sys.stdin.read()
        except Exception:
            pass

        logbook = find_logbook_dir(Path.cwd())
        if logbook is None:
            return 0  # No logbook in this project — nothing to checkpoint.

        active_dir = logbook / "active"
        if not active_dir.is_dir():
            return 0

        now = datetime.now()
        recent_threshold = now - timedelta(hours=1)
        timestamp = now.strftime("%Y-%m-%d %H:%M")

        active_paths: list[str] = []
        for task_file in sorted(active_dir.glob("*.md")):
            try:
                rel = str(task_file.relative_to(logbook.parent))
            except ValueError:
                rel = str(task_file)
            active_paths.append(rel)

            try:
                mtime = datetime.fromtimestamp(task_file.stat().st_mtime)
            except OSError:
                continue

            if mtime < recent_threshold:
                continue  # Stale — skip; it wasn't being actively worked.

            # Append a visible checkpoint marker so the post-compaction
            # agent sees that something happened and the previous log
            # entry may be incomplete.
            try:
                with task_file.open("a", encoding="utf-8") as f:
                    f.write(
                        f"\n### [compaction checkpoint] {timestamp}\n"
                        "Status: context was about to be compacted.\n"
                        "Note: resume from the last unchecked Plan step. "
                        "The most recent log entry above may be incomplete.\n"
                    )
            except OSError:
                # Skip this file but keep going. Never break compaction.
                pass

        # Snapshot session state for the next logbook skill activation.
        state = {
            "timestamp": timestamp,
            "active_tasks": active_paths,
            "note": (
                "Written by the logbook PreCompact hook just before "
                "Claude Code compacted the conversation context."
            ),
        }
        try:
            (logbook / ".last-session-state").write_text(
                json.dumps(state, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

        return 0

    except Exception:
        # Truly never raise. A non-zero exit would block compaction
        # and that's a much worse failure than missing a checkpoint.
        return 0


if __name__ == "__main__":
    sys.exit(main())
