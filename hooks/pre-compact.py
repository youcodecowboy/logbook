#!/usr/bin/env python3
"""Logbook PreCompact hook.

Runs before Claude Code compacts the conversation context. Writes
.logbook/.last-session-state with a snapshot of active task paths so
the main logbook skill can offer resumption on the next session start.

The previous version (v0.1.x) also appended `[compaction checkpoint]`
log entries to active task files. v0.2.0 dropped that — task files no
longer have structured `## Log` sections, so there's nothing to write
into. The state snapshot is the useful part.

Project root: prefer $CLAUDE_PROJECT_DIR env var. Fall back to walking
up from CWD looking for a `.logbook/` directory (in case CWD is a
subdir of the project root).

Always exits 0. Never blocks compaction. Never raises.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def find_logbook_dir(start: Path, max_levels: int = 6) -> Path | None:
    for parent in [start, *start.parents][:max_levels]:
        candidate = parent / ".logbook"
        if candidate.is_dir():
            return candidate
    return None


def main() -> int:
    try:
        # Drain stdin defensively (Claude Code may send a JSON payload).
        try:
            if not sys.stdin.isatty():
                sys.stdin.read()
        except Exception:
            pass

        # Project root from env var, fallback to CWD walk-up.
        project_dir_str = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        try:
            start = Path(project_dir_str)
        except Exception:
            return 0

        logbook = (start / ".logbook") if (start / ".logbook").is_dir() else None
        if logbook is None:
            logbook = find_logbook_dir(start)
        if logbook is None:
            return 0

        active_dir = logbook / "active"
        if not active_dir.is_dir():
            return 0

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        active_paths: list[str] = []
        for task_file in sorted(active_dir.glob("*.md")):
            try:
                rel = str(task_file.relative_to(logbook.parent))
            except ValueError:
                rel = str(task_file)
            active_paths.append(rel)

        state = {
            "timestamp": timestamp,
            "active_tasks": active_paths,
            "note": (
                "Snapshot written by the logbook PreCompact hook. "
                "Use to offer session resumption."
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
        # Never raise. A non-zero exit would block compaction.
        return 0


if __name__ == "__main__":
    sys.exit(main())
