# Auto-Scaffold CLI — Implementation Plan

## Project Overview
Build a self-contained, hackathon-compliant AI agent CLI tool that:
- Auto-detects codebase language/framework
- Generates test cases using LLMs
- Runs tests and captures failures structurally
- Proposes fixes as reviewable diffs (never auto-applies)
- Provides a local GUI for non-technical users
- Uses a strict provider routing: NVIDIA (core) -> OpenRouter, Gemini (planning) -> OpenRouter

---

## Architecture

### Provider Router (Single Source of Truth)
```
call_llm(prompt, tier) where tier in {"core", "planning"}
```
- **core tier**: NVIDIA Build (primary) -> OpenRouter (fallback on 429/outage)
- **planning tier**: Gemini Flash (primary) -> OpenRouter (fallback on 429/outage)
- Round-robin key rotation per provider
- No retries/waits on rate limits -- immediate fallback

### Core Components

| Component | Type | Tier | Description |
|-----------|------|------|-------------|
| `LanguageDetector` | Agent | planning | Detects language, package manager, test framework |
| `ASTParser` | Skill | -- | Deterministic AST parsing (no LLM) |
| `TestGenerator` | Agent | core (+planning assist) | Generates runnable test files |
| `TestRunner` | Skill | -- | Executes tests, parses failures to structured records |
| `FixProposer` | Agent | core | Generates fix proposals from failures |
| `DiffEngine` | Skill | -- | Produces unified diffs for proposals |
| `ApprovalGate` | Skill | -- | Enforces user approval before apply |
| `ProtectedPaths` | Skill | -- | Hard-coded governance enforcement |

### Data Model
```python
# Structural summary from ASTParser
CodebaseSummary:
  language: str
  package_manager: str
  test_framework: str
  files: List[FileSummary]

FileSummary:
  path: str
  functions: List[FunctionInfo]
  classes: List[ClassInfo]
  imports: List[str]
  syntax_errors: List[str]

# Test execution result
TestResult:
  test_id: str
  file: str
  passed: bool
  error_type: str | None
  message: str | None
  traceback: str | None

# Fix proposal
FixProposal:
  id: str
  target_file: str
  original_code: str
  proposed_code: str
  diff: str
  test_failures_addressed: List[str]
  status: "pending" | "approved" | "rejected" | "applied"
```