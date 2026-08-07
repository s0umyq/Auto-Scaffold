"""
Language Detector Agent — Detects language, package manager, test framework.

Uses planning tier (Gemini Flash -> OpenRouter) for ambiguous cases.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from auto_scaffold.models import LanguageDetectionResult
from auto_scaffold.provider_router import call_llm

logger = logging.getLogger(__name__)


# Threshold for using deterministic detection vs LLM
DETECTION_CONFIDENCE_THRESHOLD = 0.8


DETECTION_PROMPT = """Analyze this project structure and detect:
1. Primary programming language
2. Package manager
3. Test framework

Project files:
{files}

Package.json content:
{package_json}

Pyproject.toml content:
{pyproject_toml}

Cargo.toml content:
{cargo_toml}

Go.mod content:
{go_mod}

Respond with JSON only:
{{"primary_language": "...", "package_manager": "...", "test_framework": "...", "confidence": 0.0-1.0}}"""


class LanguageDetector:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def detect(self) -> LanguageDetectionResult:
        # First, try deterministic detection
        det_result = self._deterministic_detect()
        if det_result.confidence >= DETECTION_CONFIDENCE_THRESHOLD:
            return det_result

        # Fall back to LLM for ambiguous cases
        return await self._llm_detect()

    def _deterministic_detect(self) -> LanguageDetectionResult:
        exts = {f.suffix.lower() for f in self.root.rglob("*") if f.is_file()}

        # Language detection
        if ".py" in exts:
            lang = "python"
            pm = "pip" if (self.root / "pyproject.toml").exists() or (self.root / "requirements.txt").exists() else "unknown"
            tf = "pytest"
        elif ".ts" in exts or ".tsx" in exts:
            lang = "typescript"
            pm = self._detect_js_pm()
            tf = self._detect_js_tf()
        elif ".js" in exts or ".jsx" in exts:
            lang = "javascript"
            pm = self._detect_js_pm()
            tf = self._detect_js_tf()
        elif ".go" in exts:
            lang = "go"
            pm = "go mod"
            tf = "go test"
        elif ".rs" in exts:
            lang = "rust"
            pm = "cargo"
            tf = "cargo test"
        else:
            return LanguageDetectionResult("unknown", "unknown", "unknown", 0.0)

        confidence = 0.9 if lang != "unknown" else 0.1
        return LanguageDetectionResult(lang, pm, tf, confidence)

    def _detect_js_pm(self) -> str:
        if (self.root / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (self.root / "yarn.lock").exists():
            return "yarn"
        if (self.root / "package-lock.json").exists():
            return "npm"
        return "npm"

    def _detect_js_tf(self) -> str:
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

    async def _llm_detect(self) -> LanguageDetectionResult:
        files = [str(f.relative_to(self.root)) for f in self.root.rglob("*") if f.is_file()][:50]
        package_json = self._read_if_exists("package.json")
        pyproject_toml = self._read_if_exists("pyproject.toml")
        cargo_toml = self._read_if_exists("Cargo.toml")
        go_mod = self._read_if_exists("go.mod")

        prompt = DETECTION_PROMPT.format(
            files="\n".join(files),
            package_json=package_json or "{}",
            pyproject_toml=pyproject_toml or "",
            cargo_toml=cargo_toml or "",
            go_mod=go_mod or "",
        )

        try:
            response = await call_llm(prompt, "planning")
            data = json.loads(response)
            return LanguageDetectionResult(
                primary_language=data.get("primary_language", "unknown"),
                package_manager=data.get("package_manager", "unknown"),
                test_framework=data.get("test_framework", "unknown"),
                confidence=data.get("confidence", 0.5),
            )
        except Exception as e:
            logger.warning("LLM detection failed: %s", e)
            return LanguageDetectionResult("unknown", "unknown", "unknown", 0.0)

    def _read_if_exists(self, filename: str) -> str | None:
        path = self.root / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None


async def detect_language(root: Path) -> LanguageDetectionResult:
    return await LanguageDetector(root).detect()
