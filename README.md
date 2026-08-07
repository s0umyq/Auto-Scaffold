# Auto-Scaffold CLI

AI-powered developer tool that automatically detects a codebase's language, generates test cases, runs them, and proposes fixes as reviewable diffs — **never auto-applying**. Includes a local GUI for non-technical users.

## Features

- **Auto-detection** — Identifies language, package manager, and test framework (Python/pytest, JS/TS/vitest/jest, Go, Rust)
- **Test Generation** — Creates real, runnable test files using your project's conventions
- **Test Execution** — Runs tests and captures failures as structured records
- **Fix Proposals** — AI generates minimal fixes for failures, written as `.proposed` sibling files
- **Human Approval** — Review diffs in CLI or GUI, approve/reject each fix before application
- **Governance** — Protected paths (`.clinerules`, `.github`, `pyproject.toml`, etc.) enforced in code
- **Provider Routing** — Tier-based LLM routing with automatic fallback:
  - **Core tier**: NVIDIA Build → OpenRouter
  - **Planning tier**: Gemini Flash → OpenRouter
- **Local GUI** — Simple HTTP server + vanilla JS web interface at `http://localhost:8080`

## Quick Start

### Prerequisites
- Python 3.11+
- API keys for at least one provider per tier

### Installation

```bash
# Clone and install
git clone https://github.com/s0umyq/Auto-Scaffold.git
cd Auto-Scaffold
pip install -e .
```

### Configuration

```bash
# Copy template and add your API keys
cp .env.example .env
# Edit .env with your keys:
# NVIDIA_API_KEY=nvapi-...
# GEMINI_API_KEY=...
# OPENROUTER_API_KEY=sk-or-...
```

### CLI Usage

```bash
# Full pipeline: scan → generate tests → run → propose fixes → review
auto-scaffold auto /path/to/project

# Individual steps
auto-scaffold scan /path/to/project
auto-scaffold generate-tests /path/to/project
auto-scaffold run-tests /path/to/project
auto-scaffold propose-fixes /path/to/project
auto-scaffold review /path/to/project  # Interactive approval
```

### GUI Usage

```bash
# One-click launcher (Windows)
start_gui.bat

# Or using Python launcher
python launch_gui.py

# Or using Python's built-in HTTP server
python -m http.server 8080 --directory src/auto_scaffold/gui
# Open http://localhost:8080 in your browser
```

## Architecture

```
┌─────────────┐     ┌─────────────────────────────────────┐
│   User      │────▶│  Pipeline: scan → gen → run →       │
│  (CLI/GUI)  │     │  propose → review → apply           │
└─────────────┘     └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              ┌───────────┐  ┌───────────┐  ┌───────────┐
              │  Agents   │  │  Skills   │  │ Governance│
              │ (LLM)     │  │ (Determ.) │  │ (Code)    │
              └───────────┘  └───────────┘  └───────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │     Provider Router         │
                    │  core: NVIDIA → OpenRouter  │
                    │  planning: Gemini → OpenRouter│
                    └─────────────────────────────┘
```

### Components

| Type | Component | Tier | Description |
|------|-----------|------|-------------|
| **Agent** | LanguageDetector | planning | Detects language/framework |
| **Agent** | TestGenerator | core + planning | Generates test files |
| **Agent** | FixProposer | core | Proposes fixes for failures |
| **Skill** | ASTParser | — | Parses code (Python, JS, TS, Go, Rust) |
| **Skill** | TestRunner | — | Runs tests, parses failures |
| **Skill** | DiffEngine | — | Generates unified diffs |
| **Skill** | ApprovalGate | — | CLI/GUI approval flow |
| **Skill** | ProtectedPaths | — | Enforces governance in code |

## Governance (Enforced in Code)

**Protected paths** — Never modified by AI:
- `.clinerules/`, `.github/`, `pyproject.toml`, `package.json`
- `Cargo.toml`, `go.mod`, `AGENTS_AND_SKILLS.md`, `ARCHITECTURE.md`, `PRD.md`

**Hard rules:**
- All fixes go through `.proposed` files — original source never modified
- User must explicitly approve each fix
- Provider routing uses `call_llm(prompt, tier)` — never hardcoded
- Immediate fallback on 429/5xx (no retries)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src tests

# Type check
mypy src

# Format
black src tests
```

## Project Structure

```
auto-scaffold-cli/
├── .clinerules/GOVERNANCE.md    # Governance rules
├── .github/workflows/ci.yml     # CI/CD pipeline
├── AGENTS_AND_SKILLS.md         # Agent/skill registry
├── ARCHITECTURE.md              # Architecture doc
├── PRD.md                       # Product requirements
├── PLAN.md                      # Implementation plan
├── .env.example                 # API key template
├── .gitignore
├── pyproject.toml
├── setup.py                     # Setuptools config
├── setup.cfg                    # Setuptools metadata
├── MANIFEST.in                  # Source distribution manifest
├── start_gui.bat                # Windows GUI launcher
├── launch_gui.py                # Python GUI launcher
├── src/auto_scaffold/
│   ├── __init__.py
│   ├── cli.py                   # CLI entry point
│   ├── models.py                # Data models
│   ├── provider_router.py       # LLM routing
│   ├── agents/                  # LLM-based agents
│   │   ├── language_detector.py
│   │   ├── test_generator.py
│   │   └── fix_proposer.py
│   ├── skills/                  # Deterministic skills
│   │   ├── ast_parser.py
│   │   ├── test_runner.py
│   │   ├── diff_engine.py
│   │   ├── approval_gate.py
│   │   └── protected_paths.py
│   └── gui/                     # Web GUI
│       ├── index.html           # Vanilla JS frontend
│       ├── style.css            # GUI styling
│       └── app.js               # GUI logic
└── tests/
    ├── unit/                    # Unit tests (mocked)
    └── e2e/                     # E2E tests (mocked)
```
## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
1. **Lint** — ruff
2. **Type Check** — mypy
3. **Tests** — pytest (fully mocked, no network)
4. **Governance** — Verify required files exist
5. **Build** — python -m build, verify CLI works

## Hackathon Compliance

All 12 mandatory criteria satisfied:
- ✅ Architecture document (`ARCHITECTURE.md`)
- ✅ Agent rules file (`.clinerules/GOVERNANCE.md`)
- ✅ Working demo code (CLI + GUI)
- ✅ Custom agent (FixProposer) and skill (ASTParser)
- ✅ `AGENTS_AND_SKILLS.md` with clear I/O
- ✅ Green CI/CD pipeline
- ✅ PRD with Given/When/Then (`PRD.md`)
- ✅ E2E tests (mocked, offline)
- ✅ Linter in CI (ruff)
- ✅ Clean commit history
- ✅ Tagged release (v0.1.0)
- ✅ Task breakdown (`PLAN.md`)

## License

MIT License — see LICENSE file for details.

## Team

- **Soumya Sandeep Mishra** — Team Lead, AST Skill, Documentation
- **Swayam Krishna ** — AI Agent Engineer, Provider Router
- **Gourav Laxmi ** — CI/CD, Test Runner, Verification
- **Lokesh Kumar ** — Systems Architect, CLI/GUI, Integration