"""Tests for approval gate skill."""

from auto_scaffold.models import FixProposal
from auto_scaffold.skills.approval_gate import ApprovalGate


def test_approval_gate_auto_approve():
    """Auto-approve should approve all pending proposals."""
    proposals = [
        FixProposal(id="1", target_file="a.py", original_code="", proposed_code="", diff="", test_failures_addressed=[], status="pending"),
        FixProposal(id="2", target_file="b.py", original_code="", proposed_code="", diff="", test_failures_addressed=[], status="pending"),
    ]

    gate = ApprovalGate(auto_approve=True)
    reviewed = gate.review(proposals)

    assert all(p.status == "approved" for p in reviewed)


def test_approval_gate_preserves_non_pending():
    """Non-pending proposals should keep their status."""
    proposals = [
        FixProposal(id="1", target_file="a.py", original_code="", proposed_code="", diff="", test_failures_addressed=[], status="approved"),
        FixProposal(id="2", target_file="b.py", original_code="", proposed_code="", diff="", test_failures_addressed=[], status="rejected"),
    ]

    gate = ApprovalGate(auto_approve=True)
    reviewed = gate.review(proposals)

    assert reviewed[0].status == "approved"
    assert reviewed[1].status == "rejected"
