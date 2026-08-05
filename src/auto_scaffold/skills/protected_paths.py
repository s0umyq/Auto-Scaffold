"""
Protected Paths — Hard-coded governance enforcement.

Raises if a path (or any parent) is in the protected set.
Called by FixProposer and ApprovalGate before any write.
"""

from __future__ import annotations

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


def assert_not_protected(path: Path) -> None:
    """Raise ProtectedPathError if path or any parent is protected."""
    try:
        rel = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        # Path outside cwd - allow (e.g., temp files)
        return

    for part in rel.parents:
        if part.name in PROTECTED_PATHS:
            raise ProtectedPathError(f"Protected path: {part}")
    if rel.name in PROTECTED_PATHS:
        raise ProtectedPathError(f"Protected path: {rel}")