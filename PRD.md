# Auto-Scaffold CLI — Product Requirements Document

## Vision

A self-contained AI agent CLI tool that automatically detects a codebase's language, generates test cases, runs them, and proposes fixes as reviewable diffs — never auto-applying. Includes a local GUI for non-technical users.

## User Stories

### Epic 1: Codebase Analysis

**US-1.1** — Language Detection
> **As a** developer  
> **I want to** automatically detect my project's language and test framework  
> **So that** I don't need to configure anything manually

**Acceptance Criteria:**
- Given a Python project with pytest, when I run `scan`, then it detects "python", "pip", "pytest" with confidence ≥ 0.8
- Given a TypeScript project with vitest, when I run `scan`, then it detects "typescript", "npm", "vitest"
- Given a mixed project, when I run `scan`, then it identifies the primary language correctly

**US-1.2** — AST Parsing
> **As a** developer  
> **I want to** parse my codebase into structured summaries  
> **So that** downstream agents can reason about code structure

**Acceptance Criteria:**
- Given a Python file with functions and classes, when parsed, then it extracts names, args, returns, docstrings
- Given a JavaScript file, when parsed, then it extracts functions, classes, imports via tree-sitter
- Given a file with syntax errors, when parsed, then errors are captured and reported
### Epic 2: Test Generation

**US-2.1** — Generate Runnable Tests
> **As a** developer  
> **I want to** generate real, runnable test files for my codebase  
> **So that** I get immediate test coverage without writing tests manually

**Acceptance Criteria:**
- Given a CodebaseSummary, when `generate-tests` runs, then it creates test files in the correct location (tests/, __tests__/, etc.)
- Given a Python function, when test generated, then it produces valid pytest code with assertions
- Given a TypeScript function, when test generated, then it produces valid vitest/jest code
- Generated tests follow framework conventions (naming, imports, assertions)

### Epic 3: Test Execution

**US-3.1** — Run Tests & Capture Failures
> **As a** developer  
> **I want to** run tests and get structured failure data  
> **So that** I can programmatically analyze what failed

**Acceptance Criteria:**
- Given a project with pytest, when `run-tests` runs, then it executes `pytest --json-report` and parses results
- Given failing tests, when run, then each failure produces a TestResult with test_id, file, error_type, message, traceback
- Given vitest/jest/go test/cargo test, when run, then each produces structured TestResult records

### Epic 4: Fix Proposals

**US-4.1** — Propose Fixes for Failures
> **As a** developer  
> **I want to** get AI-generated fix proposals for test failures  
> **So that** I can quickly resolve issues without manual debugging

**Acceptance Criteria:**
- Given a failing test + source code + traceback, when `propose-fixes` runs, then it generates a FixProposal
- Each proposal includes: id, target_file, original_code, proposed_code, unified diff, test_failures_addressed
- Proposals are written as `.proposed` sibling files — original source is NEVER modified
- Multiple failures in same file are addressed in a single proposal when possible

### Epic 5: Human Approval Loop

**US-5.1** — Review & Approve Fixes (CLI)
> **As a** developer  
> **I want to** review proposed fixes interactively in the terminal  
> **So that** I maintain control over what changes are applied

**Acceptance Criteria:**
- Given proposals, when `review` runs, then it shows each diff with approve/reject/skip options
- Approved fixes are applied to the original file
- Rejected fixes are discarded
- After applying, tests are re-run to verify the fix works

**US-5.2** — Review & Approve Fixes (GUI)
> **As a** non-technical user  
> **I want to** review fixes visually in a web interface  
> **So that** I can approve/reject without using the command line

**Acceptance Criteria:**
- Given a running GUI server, when I open localhost:8765, then I see a folder picker and pipeline controls
- When I trigger the pipeline, then I see real-time progress for each step
- When proposals are ready, then I see a diff view with Approve/Reject buttons
- When I click Approve, then the fix is applied and tests re-run automatically

### Epic 6: Governance & Safety

**US-6.1** — Protected Paths Enforcement
> **As a** project maintainer  
> **I want to** ensure governance files are never modified by AI  
> **So that** project configuration remains under human control

**Acceptance Criteria:**
- Given any write operation, when the target path is protected, then it raises ProtectedPathError
- Protected paths include: .clinerules/, .github/, pyproject.toml, package.json, Cargo.toml, go.mod, AGENTS_AND_SKILLS.md, ARCHITECTURE.md, PRD.md
- Enforcement happens in code (FixProposer, ApprovalGate), not just documentation

**US-6.2** — Provider Routing Abstraction
> **As a** developer  
> **I want to** use tier-based LLM routing without hardcoding providers  
> **So that** provider changes don't require agent modifications

**Acceptance Criteria:**
- All LLM calls go through `call_llm(prompt, tier)` with tier ∈ {core, planning}
- Core tier routes: NVIDIA Build → OpenRouter
- Planning tier routes: Gemini Flash → OpenRouter
- Fallback on 429/5xx is immediate (no retries)

### Epic 7: CI/CD & Quality

**US-7.1** — Green CI Pipeline
> **As a** team lead  
> **I want to** have a passing CI pipeline that verifies all quality gates  
> **So that** every commit meets standards

**Acceptance Criteria:**
- GitHub Actions workflow runs on push/PR
- Jobs: lint (ruff), typecheck (mypy), tests (pytest), governance check, build
- All tests are fully mocked — no real network calls in CI
- Pipeline passes on main branch

## Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| **Performance** | Scan + parse < 5s for 1000 files; Test generation < 30s per file |
| **Reliability** | Provider fallback on 429/5xx within 1s; no hanging requests |
| **Security** | API keys via env vars only; no keys in repo; protected paths enforced in code |
| **Usability** | CLI: rich output with progress; GUI: no-build frontend, single binary/server |
| **Extensibility** | Parser/Runner/Provider registry pattern for adding languages/frameworks |

## Success Metrics

- **Hackathon Criteria**: All 12 mandatory items satisfied (architecture doc, agent rules, working demo, custom agent/skill, AGENTS_AND_SKILLS.md, green CI, PRD, E2E tests, linter in CI, clean history, tagged release, task breakdown)
- **Developer Experience**: `auto-scaffold auto <folder>` completes full pipeline with zero config
- **Safety**: Zero auto-applied fixes without human approval in testing