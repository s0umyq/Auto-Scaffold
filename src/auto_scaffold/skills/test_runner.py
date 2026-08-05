"""
Test Runner Skill — Executes tests and parses failures into structured records.

No LLM calls. Supports pytest, vitest/jest, go test, cargo test.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from auto_scaffold.models import TestResult

logger = logging.getLogger(__name__)


@dataclass
class TestRunResult:
    results: list[TestResult]
    raw_output: str
    exit_code: int


class TestRunner:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def run(self, test_framework: str) -> TestRunResult:
        runner = getattr(self, f"_run_{test_framework}", self._run_unknown)
        return runner()

    def _run_pytest(self) -> TestRunResult:
        cmd = ["python", "-m", "pytest", "--json-report", "--json-report-file=-", "-v"]
        return self._run_command(cmd, "pytest")

    def _run_vitest(self) -> TestRunResult:
        cmd = ["npx", "vitest", "run", "--reporter=json"]
        return self._run_command(cmd, "vitest")

    def _run_jest(self) -> TestRunResult:
        cmd = ["npx", "jest", "--json", "--outputFile=-"]
        return self._run_command(cmd, "jest")

    def _run_go_test(self) -> TestRunResult:
        cmd = ["go", "test", "-json", "./..."]
        return self._run_command(cmd, "go test")

    def _run_cargo_test(self) -> TestRunResult:
        cmd = ["cargo", "test", "--message-format=json"]
        return self._run_command(cmd, "cargo test")

    def _run_unknown(self) -> TestRunResult:
        logger.warning("Unknown test framework, skipping")
        return TestRunResult(results=[], raw_output="", exit_code=0)

    def _run_command(self, cmd: list[str], framework: str) -> TestRunResult:
        try:
            result = subprocess.run(
                cmd,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            logger.error("Test command timed out: %s", cmd)
            return TestRunResult(results=[], raw_output="timeout", exit_code=-1)
        except FileNotFoundError:
            logger.warning("Test command not found: %s", cmd[0])
            return TestRunResult(results=[], raw_output=f"command not found: {cmd[0]}", exit_code=-1)

        parser = getattr(self, f"_parse_{framework.replace(' ', '_').replace('-', '_')}", self._parse_generic)
        test_results = parser(result.stdout)

        return TestRunResult(
            results=test_results,
            raw_output=result.stdout,
            exit_code=result.returncode,
        )

    def _parse_pytest(self, output: str) -> list[TestResult]:
        results: list[TestResult] = []
        try:
            data = json.loads(output)
            for test in data.get("tests", []):
                results.append(TestResult(
                    test_id=test.get("nodeid", ""),
                    file=test.get("file", ""),
                    passed=test.get("outcome") == "passed",
                    error_type=test.get("call", {}).get("crash", {}).get("type"),
                    message=test.get("call", {}).get("crash", {}).get("message"),
                    traceback=test.get("call", {}).get("crash", {}).get("traceback"),
                ))
        except Exception as e:
            logger.warning("Failed to parse pytest output: %s", e)
        return results

    def _parse_vitest(self, output: str) -> list[TestResult]:
        results: list[TestResult] = []
        try:
            data = json.loads(output)
            for suite in data.get("testSuites", []):
                for test in suite.get("tests", []):
                    results.append(TestResult(
                        test_id=test.get("name", ""),
                        file=suite.get("file", ""),
                        passed=test.get("state") == "pass",
                        error_type=test.get("errors", [{}])[0].get("name") if test.get("errors") else None,
                        message=test.get("errors", [{}])[0].get("message") if test.get("errors") else None,
                        traceback=test.get("errors", [{}])[0].get("stack") if test.get("errors") else None,
                    ))
        except Exception as e:
            logger.warning("Failed to parse vitest output: %s", e)
        return results

    def _parse_jest(self, output: str) -> list[TestResult]:
        results: list[TestResult] = []
        try:
            data = json.loads(output)
            for suite in data.get("testResults", []):
                for test in suite.get("assertionResults", []):
                    results.append(TestResult(
                        test_id=test.get("fullName", ""),
                        file=suite.get("testFilePath", ""),
                        passed=test.get("status") == "passed",
                        error_type=test.get("failureMessages", [None])[0],
                        message=test.get("failureMessages", [None])[0],
                        traceback=test.get("traceback"),
                    ))
        except Exception as e:
            logger.warning("Failed to parse jest output: %s", e)
        return results

    def _parse_go_test(self, output: str) -> list[TestResult]:
        results: list[TestResult] = []
        for line in output.strip().split("\n"):
            try:
                event = json.loads(line)
                if event.get("Action") in ("fail", "pass"):
                    results.append(TestResult(
                        test_id=event.get("Test", ""),
                        file=event.get("Package", ""),
                        passed=event.get("Action") == "pass",
                        error_type="failure" if event.get("Action") == "fail" else None,
                        message=event.get("Output"),
                        traceback=None,
                    ))
            except Exception:
                continue
        return results

    def _parse_cargo_test(self, output: str) -> list[TestResult]:
        results: list[TestResult] = []
        for line in output.strip().split("\n"):
            try:
                event = json.loads(line)
                if event.get("reason") == "test-result":
                    results.append(TestResult(
                        test_id=event.get("test", ""),
                        file=event.get("package_id", ""),
                        passed=event.get("status") == "passed",
                        error_type="failure" if event.get("status") != "passed" else None,
                        message=event.get("stdout"),
                        traceback=event.get("stderr"),
                    ))
            except Exception:
                continue
        return results

    def _parse_generic(self, output: str) -> list[TestResult]:
        return []


def run_tests(root: Path, test_framework: str) -> TestRunResult:
    return TestRunner(root).run(test_framework)