"""
Test Generator Agent — Generates runnable test files from codebase summary.

Uses core tier (NVIDIA -> OpenRouter) for test logic, planning tier for framework idioms.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from auto_scaffold.models import CodebaseSummary, FileSummary, FunctionInfo, ClassInfo
from auto_scaffold.provider_router import call_llm

logger = logging.getLogger(__name__)


TEST_GEN_PROMPT = """Generate runnable test code for the following codebase.

Language: {language}
Test Framework: {test_framework}
Package Manager: {package_manager}

Codebase Summary:
{summary}

Requirements:
- Generate REAL, RUNNABLE test files (not scenarios)
- Use {test_framework} conventions and best practices
- Test public functions and classes
- Include edge cases and error conditions
- Follow the project's existing test patterns if any exist
- Output ONLY the test file content, no explanations

Target file: {target_file}
Functions to test:
{functions}

Classes to test:
{classes}

Generate the complete test file content:"""


FRAMEWORK_IDIOM_PROMPT = """Provide {test_framework} specific testing patterns and conventions for {language}.

Include:
- Import statements
- Test function naming conventions
- Assertion styles
- Fixture/setup patterns
- Mocking approaches
- Async testing patterns (if applicable)

Respond with concise JSON only."""


class TestGenerator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def generate(self, summary: CodebaseSummary) -> list[Path]:
        generated_files: list[Path] = []

        for file_summary in summary.files:
            if not file_summary.functions and not file_summary.classes:
                continue

            test_content = await self._generate_for_file(summary, file_summary)
            if test_content:
                test_path = self._get_test_path(file_summary, summary.test_framework)
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text(test_content, encoding="utf-8")
                generated_files.append(test_path)
                logger.info("Generated test file: %s", test_path)

        return generated_files

    async def _generate_for_file(self, summary: CodebaseSummary, file_summary: FileSummary) -> str | None:
        functions_desc = self._format_functions(file_summary.functions)
        classes_desc = self._format_classes(file_summary.classes)

        # Get framework-specific idioms from planning tier
        idioms = await self._get_framework_idioms(summary.language, summary.test_framework)

        prompt = TEST_GEN_PROMPT.format(
            language=summary.language,
            test_framework=summary.test_framework,
            package_manager=summary.package_manager,
            summary=self._format_summary(summary),
            target_file=file_summary.path,
            functions=functions_desc,
            classes=classes_desc,
        )

        try:
            return await call_llm(prompt, "core")
        except Exception as e:
            logger.error("Test generation failed for %s: %s", file_summary.path, e)
            return None

    async def _get_framework_idioms(self, language: str, test_framework: str) -> str:
        prompt = FRAMEWORK_IDIOM_PROMPT.format(
            language=language,
            test_framework=test_framework,
        )
        try:
            return await call_llm(prompt, "planning")
        except Exception:
            return ""

    def _format_summary(self, summary: CodebaseSummary) -> str:
        return f"Language: {summary.language}, Framework: {summary.test_framework}, Files: {len(summary.files)}"

    def _format_functions(self, functions: list[FunctionInfo]) -> str:
        if not functions:
            return "None"
        lines = []
        for f in functions:
            args = ", ".join(f.args)
            ret = f" -> {f.returns}" if f.returns else ""
            lines.append(f"  def {f.name}({args}){ret}")
        return "\n".join(lines)

    def _format_classes(self, classes: list[ClassInfo]) -> str:
        if not classes:
            return "None"
        lines = []
        for c in classes:
            methods = ", ".join(m.name for m in c.methods)
            lines.append(f"  class {c.name}: [{methods}]")
        return "\n".join(lines)

    def _get_test_path(self, file_summary: FileSummary, test_framework: str) -> Path:
        rel_path = Path(file_summary.path)
        stem = rel_path.stem
        suffix = rel_path.suffix

        if test_framework == "pytest":
            return self.root / "tests" / f"test_{stem}{suffix}"
        if test_framework in ("vitest", "jest"):
            return self.root / "__tests__" / f"{stem}.test{suffix}"
        if test_framework == "go test":
            return self.root / f"{stem}_test.go"
        if test_framework == "cargo test":
            return self.root / "tests" / f"{stem}_test.rs"
        return self.root / "tests" / f"test_{stem}{suffix}"


async def generate_tests(root: Path, summary: CodebaseSummary) -> list[Path]:
    return await TestGenerator(root).generate(summary)