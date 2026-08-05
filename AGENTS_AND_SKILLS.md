# Agents and Skills Registry

## Agents (Call LLMs, Make Judgment Calls)

### 1. LanguageDetector
- **Tier**: planning (Gemini Flash → OpenRouter)
- **Input**: `folder_path: Path`
- **Output**: `LanguageDetectionResult`
  - `primary_language: str` (e.g., "python", "javascript", "typescript", "go", "rust")
  - `package_manager: str` (e.g., "pip", "npm", "yarn", "pnpm", "cargo", "go mod")
  - `test_framework: str` (e.g., "pytest", "vitest", "jest", "go test", "cargo test")
  - `confidence: float` (0.0-1.0)
- **Responsibility**: Analyze folder structure, config files, and file extensions to detect language/framework. Uses planning-tier LLM for ambiguous cases.

### 2. TestGenerator
- **Tier**: core (NVIDIA Build → OpenRouter) + planning assist for framework idioms
- **Input**: `CodebaseSummary` (from ASTParser)
- **Output**: Generated test files written to disk under `tests/` or `__tests__/` per framework convention
- **Responsibility**: Generate real, runnable test code (not scenarios) for each public function/class in the codebase. Uses core tier for test logic, planning tier for framework-specific patterns.

### 3. FixProposer
- **Tier**: core (NVIDIA Build → OpenRouter)
- **Input**: 
  - `failing_test: TestResult`
  - `source_code: str` (original source file content)
  - `traceback: str`
- **Output**: `FixProposal` written as `.proposed` sibling file
- **Responsibility**: Analyze failure + source + traceback, propose a minimal fix. NEVER modifies original source. Calls `ProtectedPaths.assert_not_protected()` before writing.

---

## Skills (Deterministic, No LLM Calls)

### 1. ASTParser
- **Input**: `folder_path: Path`
- **Output**: `CodebaseSummary`
- **Responsibility**: Parse source files into structured summary (functions, classes, imports, syntax errors). Supports:
  - Python: `ast` module
  - JavaScript/TypeScript: `tree-sitter` or `esprima`
  - Go: `go/ast`
  - Rust: `syn`
- **Language detection**: File extensions + config files (package.json, pyproject.toml, Cargo.toml, go.mod)

### 2. TestRunner
- **Input**: `folder_path: Path`, `test_framework: str`
- **Output**: `List[TestResult]`
- **Responsibility**: Execute detected test framework, capture output, parse failures into structured records. Handles:
  - pytest: `pytest --json-report`
  - vitest/jest: `--reporter=json`
  - go test: `-json`
  - cargo test: `--message-format=json`

### 3. DiffEngine
- **Input**: `original: str`, `proposed: str`, `file_path: str`
- **Output**: `unified_diff: str`
- **Responsibility**: Generate unified diff format for display in CLI/GUI.

### 4. ApprovalGate
- **Input**: `List[FixProposal]`
- **Output**: `List[FixProposal]` with updated status (approved/rejected)
- **Responsibility**: Present diffs to user (CLI interactive or GUI), collect approval decisions. Calls `ProtectedPaths.assert_not_protected()` before applying approved fixes.

### 5. ProtectedPaths
- **Input**: `path: Path`
- **Output**: `None` (raises `ProtectedPathError` if protected)
- **Responsibility**: Hard-coded governance enforcement. Checks if path or any parent is in protected set. Called by FixProposer and ApprovalGate before any write.

### 6. ProviderRouter
- **Input**: `prompt: str`, `tier: Literal["core", "planning"]`
- **Output**: `str` (LLM response)
- **Responsibility**: Single entry point for all LLM calls. Implements:
  - Tier routing: core → NVIDIA Build → OpenRouter; planning → Gemini Flash → OpenRouter
  - Round-robin key rotation per provider
  - Immediate fallback on 429/5xx (no retries)
  - Structured logging

---

## Data Models (Shared)

### LanguageDetectionResult
```python
@dataclass
class LanguageDetectionResult:
    primary_language: str
    package_manager: str
    test_framework: str
    confidence: float
```

### CodebaseSummary
```python
@dataclass
class CodebaseSummary:
    language: str
    package_manager: str
    test_framework: str
    files: List[FileSummary]

@dataclass
class FileSummary:
    path: str
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[str]
    syntax_errors: List[str]

@dataclass
class FunctionInfo:
    name: str
    args: List[str]
    returns: str | None
    docstring: str | None
    start_line: int
    end_line: int

@dataclass
class ClassInfo:
    name: str
    methods: List[FunctionInfo]
    bases: List[str]
    start_line: int
    end_line: int
```

### TestResult
```python
@dataclass
class TestResult:
    test_id: str
    file: str
    passed: bool
    error_type: str | None
    message: str | None
    traceback: str | None
```

### FixProposal
```python
@dataclass
class FixProposal:
    id: str
    target_file: str
    original_code: str
    proposed_code: str
    diff: str
    test_failures_addressed: List[str]
    status: Literal["pending", "approved", "rejected", "applied"]
```