"""Tests for test runner skill."""

from pathlib import Path

from auto_scaffold.skills.test_runner import TestRunner, TestRunResult

# Constant for number of test cases in test data
NUM_TEST_CASES = 2


def test_run_unknown_framework(tmp_path):
    """Unknown framework should return empty results."""
    runner = TestRunner(tmp_path)
    result = runner.run("unknown-framework")

    assert isinstance(result, TestRunResult)
    assert result.results == []
    assert result.exit_code == 0


def test_parse_pytest_output():
    """Pytest JSON output should be parsed correctly."""
    runner = TestRunner(Path())

    pytest_json = """
    {
        "tests": [
            {
                "nodeid": "test_example.py::test_pass",
                "file": "test_example.py",
                "outcome": "passed"
            },
            {
                "nodeid": "test_example.py::test_fail",
                "file": "test_example.py",
                "outcome": "failed",
                "call": {
                    "crash": {
                        "type": "AssertionError",
                        "message": "assert 1 == 2",
                        "traceback": "Traceback..."
                    }
                }
            }
        ]
    }
    """

    results = runner._parse_pytest(pytest_json)

    assert len(results) == NUM_TEST_CASES
    assert results[0].test_id == "test_example.py::test_pass"
    assert results[0].passed is True
    assert results[1].test_id == "test_example.py::test_fail"
    assert results[1].passed is False
    assert results[1].error_type == "AssertionError"
    assert results[1].message == "assert 1 == 2"


def test_parse_vitest_output():
    """Vitest JSON output should be parsed correctly."""
    runner = TestRunner(Path())

    vitest_json = """
    {
        "testSuites": [
            {
                "file": "test.ts",
                "tests": [
                    {"name": "test pass", "state": "pass"},
                    {"name": "test fail", "state": "fail", "errors": [{"name": "Error", "message": "failed", "stack": "stack"}]}
                ]
            }
        ]
    }
    """

    results = runner._parse_vitest(vitest_json)

    assert len(results) == NUM_TEST_CASES
    assert results[0].test_id == "test pass"
    assert results[0].passed is True
    assert results[1].test_id == "test fail"
    assert results[1].passed is False
    assert results[1].error_type == "Error"
