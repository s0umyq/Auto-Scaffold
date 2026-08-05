"""Tests for protected paths skill."""

import pytest
from pathlib import Path
from auto_scaffold.skills.protected_paths import assert_not_protected, ProtectedPathError


def test_assert_not_protected_allows_normal_path(tmp_path):
    """Normal paths should be allowed."""
    test_file = tmp_path / "src" / "main.py"
    test_file.parent.mkdir(parents=True)
    assert_not_protected(test_file)  # Should not raise


def test_assert_not_protected_blocks_clinerules(tmp_path):
    """Paths under .clinerules should be blocked."""
    protected = tmp_path / ".clinerules" / "GOVERNANCE.md"
    protected.parent.mkdir(parents=True)
    with pytest.raises(ProtectedPathError):
        assert_not_protected(protected)


def test_assert_not_protected_blocks_github(tmp_path):
    """Paths under .github should be blocked."""
    protected = tmp_path / ".github" / "workflows" / "ci.yml"
    protected.parent.mkdir(parents=True)
    with pytest.raises(ProtectedPathError):
        assert_not_protected(protected)


def test_assert_not_protected_blocks_pyproject_toml(tmp_path):
    """pyproject.toml should be blocked."""
    protected = tmp_path / "pyproject.toml"
    with pytest.raises(ProtectedPathError):
        assert_not_protected(protected)


def test_assert_not_protected_blocks_nested_protected(tmp_path):
    """Nested protected paths should be blocked."""
    protected = tmp_path / "src" / "pyproject.toml"
    protected.parent.mkdir(parents=True)
    with pytest.raises(ProtectedPathError):
        assert_not_protected(protected)


def test_assert_not_protected_allows_outside_cwd(tmp_path):
    """Paths outside cwd should be allowed (e.g., temp files)."""
    import tempfile
    with tempfile.NamedTemporaryFile() as f:
        assert_not_protected(Path(f.name))  # Should not raise