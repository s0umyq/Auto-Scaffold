"""
Approval Gate Skill — Enforces user approval before applying fixes.

CLI interactive and GUI-compatible approval flow.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from auto_scaffold.models import FixProposal
from auto_scaffold.skills.protected_paths import ProtectedPathError, assert_not_protected

logger = logging.getLogger(__name__)


class ApprovalGate:
    def __init__(self, auto_approve: bool = False) -> None:
        self.auto_approve = auto_approve

    def review(self, proposals: list[FixProposal]) -> list[FixProposal]:
        """Present proposals for approval. Returns updated proposals with status."""
        for proposal in proposals:
            if proposal.status != "pending":
                continue

            if self.auto_approve:
                proposal.status = "approved"
                logger.info("Auto-approved: %s", proposal.id)
                continue

            decision = self._prompt_user(proposal)
            if decision == "approve":
                proposal.status = "approved"
            elif decision == "reject":
                proposal.status = "rejected"
            else:
                proposal.status = "pending"

        return proposals

    def _prompt_user(self, proposal: FixProposal) -> Literal["approve", "reject", "skip"]:
        print(f"\n{'='*60}")  # noqa: T201
        print(f"Proposal: {proposal.id}")  # noqa: T201
        print(f"File: {proposal.target_file}")  # noqa: T201
        print(f"Tests addressed: {', '.join(proposal.test_failures_addressed) or 'none'}")  # noqa: T201
        print(f"{'='*60}")  # noqa: T201
        print(proposal.diff)  # noqa: T201
        print(f"{'='*60}")  # noqa: T201

        while True:
            choice = input("Approve (a), Reject (r), Skip (s)? ").strip().lower()
            if choice in ("a", "approve"):
                return "approve"
            if choice in ("r", "reject"):
                return "reject"
            if choice in ("s", "skip"):
                return "skip"
            print("Invalid choice. Enter a, r, or s.")  # noqa: T201

    def apply_approved(self, proposals: list[FixProposal]) -> list[FixProposal]:
        """Apply approved proposals to their target files."""
        for proposal in proposals:
            if proposal.status != "approved":
                continue

            target = Path(proposal.target_file).resolve()
            try:
                assert_not_protected(target)
            except ProtectedPathError as e:
                logger.error("Cannot apply to protected path: %s", e)
                proposal.status = "rejected"
                continue

            try:
                target.write_text(proposal.proposed_code, encoding="utf-8")
                proposal.status = "applied"
                logger.info("Applied fix: %s", proposal.id)
            except Exception as e:
                logger.error("Failed to apply fix %s: %s", proposal.id, e)
                proposal.status = "rejected"

        return proposals
