"""Agents package."""

from auto_scaffold.agents.fix_proposer import FixProposer, propose_fixes
from auto_scaffold.agents.language_detector import LanguageDetector, detect_language
from auto_scaffold.agents.test_generator import TestGenerator, generate_tests

__all__ = [
    "FixProposer",
    "propose_fixes",
    "LanguageDetector",
    "detect_language",
    "TestGenerator",
    "generate_tests",
]