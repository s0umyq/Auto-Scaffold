"""Skills package."""

from auto_scaffold.skills.approval_gate import ApprovalGate
from auto_scaffold.skills.ast_parser import ASTParser, parse_codebase
from auto_scaffold.skills.diff_engine import generate_diff
from auto_scaffold.skills.protected_paths import ProtectedPathError, assert_not_protected
from auto_scaffold.skills.test_runner import TestRunner, TestRunResult, run_tests

__all__ = [
    "ASTParser",
    "ApprovalGate",
    "ProtectedPathError",
    "TestRunResult",
    "TestRunner",
    "assert_not_protected",
    "generate_diff",
    "parse_codebase",
    "run_tests",
]
