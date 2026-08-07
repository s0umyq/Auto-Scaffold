"""
Diff Engine Skill — Generates unified diffs for proposed fixes.
"""

from __future__ import annotations

import difflib


def generate_diff(original: str, proposed: str, file_path: str) -> str:
    """Generate a unified diff between original and proposed code."""
    original_lines = original.splitlines(keepends=True)
    proposed_lines = proposed.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        original_lines,
        proposed_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    ))
    # Always include headers even if no changes
    if not diff:
        return f"--- a/{file_path}\n+++ b/{file_path}"
    return "\n".join(diff)
