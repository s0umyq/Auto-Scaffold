"""Skills package."""

from auto_scaffold.skills.approval_gate import ApprovalGate
from auto_scaffold.skills.ast_parser import ASTParser, parse_codebase
from auto_scaffold.skills.diff_engine import generate_diff
from auto_scaffold.skills.protected_paths import ProtectedPathError, assert_not_protected
from auto_scaffold.skills.test_runner import TestRunner, run_tests, TestRunResult

__all__ = [
    "ApprovalGate",
    "ASTParser",
    "parse_codebase",
    "generate_diff",
    "ProtectedPathError",
    "assert_not_protected",
    "TestRunner",
    "run_tests",
    "TestRunResult",
]