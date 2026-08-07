"""Tests for diff engine skill."""

from auto_scaffold.skills.diff_engine import generate_diff


def test_generate_diff_simple_change():
    """Diff should show added and removed lines."""
    original = "def foo():\n    return 1\n"
    proposed = "def foo():\n    return 2\n"
    diff = generate_diff(original, proposed, "test.py")

    assert "--- a/test.py" in diff
    assert "+++ b/test.py" in diff
    assert "-    return 1" in diff
    assert "+    return 2" in diff


def test_generate_diff_no_change():
    """Identical code should produce empty diff."""
    original = "def foo():\n    return 1\n"
    proposed = "def foo():\n    return 1\n"
    diff = generate_diff(original, proposed, "test.py")

    # Should have headers but no changes
    assert "--- a/test.py" in diff
    assert "+++ b/test.py" in diff


def test_generate_diff_multiline():
    """Diff should handle multi-line changes."""
    original = "def foo():\n    a = 1\n    b = 2\n    return a + b\n"
    proposed = "def foo():\n    x = 10\n    y = 20\n    return x + y\n"
    diff = generate_diff(original, proposed, "test.py")

    assert "-    a = 1" in diff
    assert "-    b = 2" in diff
    assert "+    x = 10" in diff
    assert "+    y = 20" in diff
