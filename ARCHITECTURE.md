# Auto-Scaffold CLI — Architecture Document

## System Overview

Auto-Scaffold CLI is an AI-powered developer tool that automatically generates tests, runs them, and proposes fixes for failures — all with human-in-the-loop approval.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │    CLI      │  │    GUI      │                              │
│  │ (Rich/Click)│  │ (FastAPI+JS)│                              │
│  └──────┬──────┘  └──────┬──────┘                              │
└─────────┼────────────────┼─────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Pipeline Orchestrator                       │
│  scan → generate-tests → run-tests → propose-fixes → review     │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Agents      │ │   Skills      │ │  Governance   │
│  (LLM calls)  │ │ (Deterministic)│ │  Enforcement  │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                │                │
        ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Provider Router (Tier-based)                  │
│  ┌──────────────────┐        ┌──────────────────┐              │
│  │   Core Tier      │        │  Planning Tier   │              │
│  │ NVIDIA Build →   │        │ Gemini Flash →   │              │
│  │ OpenRouter       │        │ OpenRouter       │              │
│  └──────────────────┘        └──────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### Provider Router (`src/auto_scaffold/provider_router.py`)

Single entry point for all LLM calls. Exposes `call_llm(prompt, tier)`.

**Tier Routing:**
- `core` → NVIDIA Build (primary) → OpenRouter (fallback on 429/5xx)
- `planning` → Gemini Flash (primary) → OpenRouter (fallback on 429/5xx)

**Features:**
- Round-robin API key rotation per provider
- Immediate fallback on rate limits (no retries/waits)
- Structured logging
- OpenAI-compatible API for all providers

### Agents (LLM-based)

| Agent | Tier | Responsibility |
|-------|------|----------------|
| `LanguageDetector` | planning | Detect language, package manager, test framework |
| `TestGenerator` | core + planning assist | Generate runnable test files |
| `FixProposer` | core | Generate fix proposals from failures |

### Skills (Deterministic)

| Skill | Responsibility |
|-------|----------------|
| `ASTParser` | Parse source code into structured summaries (Python, JS, TS, Go, Rust) |
| `TestRunner` | Execute tests, parse failures into structured `TestResult` records |
| `DiffEngine` | Generate unified diffs for proposals |
| `ApprovalGate` | CLI/GUI approval flow, apply approved fixes |
| `ProtectedPaths` | Hard-coded governance enforcement |

### Data Models (`src/auto_scaffold/models.py`)

```python
LanguageDetectionResult: { primary_language, package_manager, test_framework, confidence }
CodebaseSummary: { language, package_manager, test_framework, files: [FileSummary] }
FileSummary: { path, functions: [FunctionInfo], classes: [ClassInfo], imports, syntax_errors }
TestResult: { test_id, file, passed, error_type, message, traceback }
FixProposal: { id, target_file, original_code, proposed_code, diff, test_failures_addressed, status }
```

## Governance Enforcement (Code, Not Prose)

**Protected Paths** (in `src/auto_scaffold/skills/protected_paths.py`):
- `.clinerules/`, `.github/`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`
- `AGENTS_AND_SKILLS.md`, `ARCHITECTURE.md`, `PRD.md`

**Enforcement Points:**
1. `FixProposer` calls `assert_not_protected()` before writing `.proposed` files
2. `ApprovalGate` calls `assert_not_protected()` before applying approved fixes
3. CI/CD verifies governance files exist

**Hard Rules:**
- Never auto-apply fixes — all changes go through `.proposed` files
- User must explicitly approve each fix
- Provider routing must use `call_llm(tier)` — never hardcode providers

## CLI Commands (`src/auto_scaffold/cli.py`)

| Command | Description |
|---------|-------------|
| `scan <folder>` | Detect language, parse AST |
| `generate-tests <folder>` | Generate test files |
| `run-tests <folder>` | Run tests, show failures |
| `propose-fixes <folder>` | Generate fix proposals |
| `review <folder>` | Interactive approval of proposals |
| `auto <folder>` | Full pipeline |

## GUI (`src/auto_scaffold/gui/`)

- **Server**: FastAPI with WebSocket for real-time progress
- **Frontend**: Single HTML file with vanilla JS (no build step)
- **Features**: Folder picker, step-by-step pipeline, diff view with approve/reject buttons, real-time logs
- **Runs on**: `http://127.0.0.1:8765`

## CI/CD Pipeline (`.github/workflows/ci.yml`)

1. **Lint** — ruff
2. **Type Check** — mypy
3. **Tests** — pytest (fully mocked, no network)
4. **Governance** — Verify required files exist
5. **Build** — python -m build, verify CLI works

## Security Considerations

- API keys via environment variables only
- No keys in code or config files
- Protected paths prevent modification of governance files
- All fixes require human approval
- No arbitrary code execution — only test running and file writing

## Extensibility

- New languages: Add parser in `ASTParser._parse_<language>()`
- New test frameworks: Add runner in `TestRunner._run_<framework>()`
- New providers: Add config in `ProviderRouter._init_configs()`