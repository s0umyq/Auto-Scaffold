"""
Shared data models for the Auto-Scaffold CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class LanguageDetectionResult:
    primary_language: str
    package_manager: str
    test_framework: str
    confidence: float


@dataclass
class FunctionInfo:
    name: str
    args: list[str]
    returns: str | None
    docstring: str | None
    start_line: int
    end_line: int


@dataclass
class ClassInfo:
    name: str
    methods: list[FunctionInfo]
    bases: list[str]
    start_line: int
    end_line: int


@dataclass
class FileSummary:
    path: str
    functions: list[FunctionInfo]
    classes: list[ClassInfo]
    imports: list[str]
    syntax_errors: list[str]


@dataclass
class CodebaseSummary:
    language: str
    package_manager: str
    test_framework: str
    files: list[FileSummary]


@dataclass
class TestResult:
    test_id: str
    file: str
    passed: bool
    error_type: str | None
    message: str | None
    traceback: str | None


@dataclass
class FixProposal:
    id: str
    target_file: str
    original_code: str
    proposed_code: str
    diff: str
    test_failures_addressed: list[str]
    status: Literal["pending", "approved", "rejected", "applied"] = "pending"
