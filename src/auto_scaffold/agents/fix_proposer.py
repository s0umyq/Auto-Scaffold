"""
Fix Proposer Agent — Generates fix proposals from test failures.

Uses core tier (NVIDIA -> OpenRouter). Writes proposals as .proposed sibling files.
NEVER modifies original source.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from auto_scaffold.models import FixProposal, TestResult
from auto_scaffold.provider_router import call_llm
from auto_scaffold.skills.diff_engine import generate_diff
from auto_scaffold.skills.protected_paths import ProtectedPathError, assert_not_protected

logger = logging.getLogger(__name__)


FIX_PROPOSAL_PROMPT = """Analyze the failing test and source code, then propose a minimal fix.

FAILING TEST:
Test ID: {test_id}
File: {test_file}
Error Type: {error_type}
Message: {message}
Traceback:
{traceback}

SOURCE CODE (from {source_file}):
{source_code}

Requirements:
- Provide a MINIMAL fix that addresses the specific failure
- Do not change unrelated code
- Preserve existing functionality
- Follow the project's coding style
- Return ONLY the fixed source code, no explanations
- The fix must be syntactically correct and runnable"""


class FixProposer:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def propose(self, failures: list[TestResult], source_files: dict[str, str]) -> list[FixProposal]:
        proposals: list[FixProposal] = []

        for failure in failures:
            if failure.passed:
                continue

            source_file = failure.file
            if source_file not in source_files:
                logger.warning("Source file not found for failure: %s", source_file)
                continue

            source_code = source_files[source_file]
            proposal = await self._create_proposal(failure, source_file, source_code)
            if proposal:
                proposals.append(proposal)

        return proposals

    async def _create_proposal(self, failure: TestResult, source_file: str, source_code: str) -> FixProposal | None:
        prompt = FIX_PROPOSAL_PROMPT.format(
            test_id=failure.test_id,
            test_file=failure.file,
            error_type=failure.error_type or "unknown",
            message=failure.message or "no message",
            traceback=failure.traceback or "no traceback",
            source_file=source_file,
            source_code=source_code,
        )

        try:
            proposed_code = await call_llm(prompt, "core")
        except Exception as e:
            logger.error("Fix proposal failed for %s: %s", source_file, e)
            return None

        if not proposed_code or proposed_code.strip() == source_code.strip():
            logger.warning("No meaningful fix generated for %s", source_file)
            return None

        # Check protected paths before writing
        target_path = (self.root / source_file).resolve()
        try:
            assert_not_protected(target_path)
        except ProtectedPathError as e:
            logger.error("Cannot propose fix for protected path: %s", e)
            return None

        diff = generate_diff(source_code, proposed_code, source_file)
        proposal_id = str(uuid.uuid4())[:8]

        # Write .proposed sibling file
        proposed_path = target_path.with_suffix(target_path.suffix + ".proposed")
        proposed_path.write_text(proposed_code, encoding="utf-8")

        proposal = FixProposal(
            id=proposal_id,
            target_file=source_file,
            original_code=source_code,
            proposed_code=proposed_code,
            diff=diff,
            test_failures_addressed=[failure.test_id],
            status="pending",
        )

        logger.info("Created fix proposal: %s for %s", proposal_id, source_file)
        return proposal


async def propose_fixes(root: Path, failures: list[TestResult], source_files: dict[str, str]) -> list[FixProposal]:
    return await FixProposer(root).propose(failures, source_files)
