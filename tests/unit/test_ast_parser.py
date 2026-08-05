"""Tests for AST parser skill."""

import pytest
from pathlib import Path
from auto_scaffold.skills.ast_parser import parse_codebase


def test_parse_python_file(tmp_path):
    """Python files should be parsed correctly."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "example.py").write_text("""
def hello(name: str) -> str:
    \"\"\"Say hello.\"\"\"
    return f"Hello, {name}"

class Greeter:
    def greet(self, name: str) -> str:
        return hello(name)
""")
    
    summary = parse_codebase(tmp_path)
    
    assert summary.language == "python"
    assert summary.package_manager == "pip"
    assert summary.test_framework == "pytest"
    assert len(summary.files) == 1
    
    file_summary = summary.files[0]
    assert file_summary.path == "src/example.py"
    assert len(file_summary.functions) == 1
    assert file_summary.functions[0].name == "hello"
    assert file_summary.functions[0].args == ["name"]
    assert file_summary.functions[0].returns == "str"
    assert len(file_summary.classes) == 1
    assert file_summary.classes[0].name == "Greeter"
    assert len(file_summary.classes[0].methods) == 1


def test_parse_detects_javascript(tmp_path):
    """JavaScript projects should be detected."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.js").write_text("""
function add(a, b) {
    return a + b;
}
""")
    (tmp_path / "package.json").write_text("{}")
    
    summary = parse_codebase(tmp_path)
    
    assert summary.language == "javascript"
    assert summary.package_manager == "npm"
    assert summary.test_framework == "vitest"


def test_parse_detects_typescript(tmp_path):
    """TypeScript projects should be detected."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.ts").write_text("""
function add(a: number, b: number): number {
    return a + b;
}
""")
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "tsconfig.json").write_text("{}")
    
    summary = parse_codebase(tmp_path)
    
    assert summary.language == "typescript"
    assert summary.package_manager == "npm"
    assert summary.test_framework == "vitest"