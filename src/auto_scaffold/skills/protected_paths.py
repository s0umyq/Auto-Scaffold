"""
Protected Paths — Hard-coded governance enforcement.

Raises if a path (or any parent) is in the protected set.
Called by FixProposer and ApprovalGate before any write.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Final


class ProtectedPathError(RuntimeError):
    """Raised when attempting to modify a protected path."""


PROTECTED_PATHS: Final[set[str]] = {
    ".clinerules",
    ".github",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "AGENTS_AND_SKILLS.md",
    "ARCHITECTURE.md",
    "PRD.md",
}


def _is_system_temp(path: Path) -> bool:
    """Check if path is a system temp file (not a test temp directory)."""
    try:
        temp_dir = Path(tempfile.gettempdir()).resolve()
        resolved = path.resolve()
        rel = resolved.relative_to(temp_dir)
        # Only allow files directly in temp dir, not subdirectories
        # (test temp dirs like pytest's tmp_path are subdirectories)
        return len(rel.parts) == 1 and resolved.is_file()
    except ValueError:
        return False


def assert_not_protected(path: Path) -> None:
    """Raise ProtectedPathError if path or any parent is protected."""
    # Allow system temp files
    if _is_system_temp(path):
        return

    # Check each path component for protected names
    resolved = path.resolve()
    for part in [resolved, *list(resolved.parents)]:
        if part.name in PROTECTED_PATHS:
            raise ProtectedPathError(f"Protected path: {part}")
