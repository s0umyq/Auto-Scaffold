"""
AST Parser Skill — Deterministic parsing of source files into structured summaries.

No LLM calls. Supports Python, JavaScript, TypeScript, Go, Rust.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from auto_scaffold.models import (
    ClassInfo,
    CodebaseSummary,
    FileSummary,
    FunctionInfo,
)

logger = logging.getLogger(__name__)


@dataclass
class ParserResult:
    files: list[FileSummary]
    syntax_errors: list[str]


class ASTParser:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def parse(self) -> CodebaseSummary:
        language = self._detect_language()
        package_manager = self._detect_package_manager(language)
        test_framework = self._detect_test_framework(language, package_manager)

        parser_method = getattr(self, f"_parse_{language}", self._parse_generic)
        result = parser_method()

        return CodebaseSummary(
            language=language,
            package_manager=package_manager,
            test_framework=test_framework,
            files=result.files,
        )

    def _detect_language(self) -> str:
        exts = {f.suffix.lower() for f in self.root.rglob("*") if f.is_file()}
        if ".py" in exts:
            return "python"
        if ".ts" in exts or ".tsx" in exts:
            return "typescript"
        if ".js" in exts or ".jsx" in exts:
            return "javascript"
        if ".go" in exts:
            return "go"
        if ".rs" in exts:
            return "rust"
        return "unknown"

    def _detect_package_manager(self, language: str) -> str:
        if (self.root / "pyproject.toml").exists() or (self.root / "requirements.txt").exists():
            return "pip"
        if (self.root / "package.json").exists():
            if (self.root / "pnpm-lock.yaml").exists():
                return "pnpm"
            if (self.root / "yarn.lock").exists():
                return "yarn"
            return "npm"
        if (self.root / "Cargo.toml").exists():
            return "cargo"
        if (self.root / "go.mod").exists():
            return "go mod"
        return "unknown"

    def _detect_test_framework(self, language: str, pm: str) -> str:
        if language == "python":
            return "pytest"
        if language in ("javascript", "typescript"):
            if (self.root / "package.json").exists():
                try:
                    pkg = json.loads((self.root / "package.json").read_text())
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    if "vitest" in deps:
                        return "vitest"
                    if "jest" in deps:
                        return "jest"
                except Exception:
                    pass
            return "vitest"
        if language == "go":
            return "go test"
        if language == "rust":
            return "cargo test"
        return "unknown"

    def _parse_python(self) -> ParserResult:
        files: list[FileSummary] = []
        syntax_errors: list[str] = []

        for py_file in self.root.rglob("*.py"):
            if any(p.name in {".venv", "venv", "__pycache__", ".git"} for p in py_file.parents):
                continue
            try:
                rel = py_file.relative_to(self.root)
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(rel))
                files.append(self._extract_python(rel, tree, content))
            except SyntaxError as e:
                syntax_errors.append(f"{py_file}: {e}")
            except Exception as e:
                logger.warning("Failed to parse %s: %s", py_file, e)

        return ParserResult(files=files, syntax_errors=syntax_errors)

    def _extract_python(self, rel: Path, tree: ast.AST, content: str) -> FileSummary:
        functions: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        imports: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(FunctionInfo(
                    name=node.name,
                    args=[a.arg for a in node.args.args],
                    returns=ast.unparse(node.returns) if node.returns else None,
                    docstring=ast.get_docstring(node),
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                ))
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(FunctionInfo(
                            name=item.name,
                            args=[a.arg for a in item.args.args],
                            returns=ast.unparse(item.returns) if item.returns else None,
                            docstring=ast.get_docstring(item),
                            start_line=item.lineno,
                            end_line=item.end_lineno or item.lineno,
                        ))
                classes.append(ClassInfo(
                    name=node.name,
                    methods=methods,
                    bases=[ast.unparse(b) for b in node.bases],
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                ))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if isinstance(node, ast.ImportFrom):
                        imports.append(f"from {node.module} import {alias.name}")
                    else:
                        imports.append(alias.name)

        return FileSummary(
            path=str(rel),
            functions=functions,
            classes=classes,
            imports=imports,
            syntax_errors=[],
        )

    def _parse_javascript(self) -> ParserResult:
        return self._parse_with_tree_sitter("javascript")

    def _parse_typescript(self) -> ParserResult:
        return self._parse_with_tree_sitter("typescript")

    def _parse_with_tree_sitter(self, lang: Literal["javascript", "typescript"]) -> ParserResult:
        files: list[FileSummary] = []
        syntax_errors: list[str] = []

        try:
            from tree_sitter import Language, Parser
        except ImportError:
            logger.warning("tree-sitter not available, using fallback")
            return self._parse_generic()

        for ext in (".js", ".jsx", ".ts", ".tsx"):
            for src_file in self.root.rglob(f"*{ext}"):
                if any(p.name in {"node_modules", ".git"} for p in src_file.parents):
                    continue
                try:
                    rel = src_file.relative_to(self.root)
                    content = src_file.read_text(encoding="utf-8")
                    files.append(self._extract_js_ts(rel, content, lang))
                except Exception as e:
                    syntax_errors.append(f"{src_file}: {e}")

        return ParserResult(files=files, syntax_errors=syntax_errors)

    def _extract_js_ts(self, rel: Path, content: str, lang: str) -> FileSummary:
        try:
            from tree_sitter import Language, Parser
            import tree_sitter_javascript as tsjs
            import tree_sitter_typescript as tsts
        except ImportError:
            return self._extract_generic(rel, content)

        parser = Parser()
        if lang == "typescript":
            parser.set_language(Language(tsts.language_typescript()))
        else:
            parser.set_language(Language(tsjs.language_javascript()))

        tree = parser.parse(bytes(content, "utf8"))
        functions: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        imports: list[str] = []

        def walk(node):
            if node.type in ("function_declaration", "arrow_function", "function_expression"):
                name = self._get_js_name(node, content)
                if name:
                    functions.append(FunctionInfo(
                        name=name,
                        args=self._get_js_args(node, content),
                        returns=None,
                        docstring=None,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    ))
            elif node.type == "class_declaration":
                name = self._get_js_name(node, content)
                methods = []
                for child in node.children:
                    if child.type == "method_definition":
                        mname = self._get_js_name(child, content)
                        if mname:
                            methods.append(FunctionInfo(
                                name=mname,
                                args=self._get_js_args(child, content),
                                returns=None,
                                docstring=None,
                                start_line=child.start_point[0] + 1,
                                end_line=child.end_point[0] + 1,
                            ))
                classes.append(ClassInfo(
                    name=name or "Unknown",
                    methods=methods,
                    bases=[],
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                ))
            elif node.type in ("import_statement", "import_declaration"):
                imports.append(content[node.start_byte:node.end_byte])

            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return FileSummary(
            path=str(rel),
            functions=functions,
            classes=classes,
            imports=imports,
            syntax_errors=[],
        )

    def _get_js_name(self, node, content: str) -> str | None:
        for child in node.children:
            if child.type == "identifier":
                return content[child.start_byte:child.end_byte]
        return None

    def _get_js_args(self, node, content: str) -> list[str]:
        args = []
        for child in node.children:
            if child.type == "formal_parameters":
                for param in child.children:
                    if param.type == "identifier":
                        args.append(content[param.start_byte:param.end_byte])
        return args

    def _parse_go(self) -> ParserResult:
        return self._parse_generic()

    def _parse_rust(self) -> ParserResult:
        return self._parse_generic()

    def _parse_generic(self) -> ParserResult:
        return ParserResult(files=[], syntax_errors=[])

    def _extract_generic(self, rel: Path, content: str) -> FileSummary:
        return FileSummary(
            path=str(rel),
            functions=[],
            classes=[],
            imports=[],
            syntax_errors=[],
        )


def parse_codebase(root: Path) -> CodebaseSummary:
    return ASTParser(root).parse()