# Auto-Scaffold CLI — Governance Rules

## Hard Rules (Enforced in Code)

### 1. Propose, Never Auto-Apply
- All code modifications MUST go through `.proposed` sibling files
- Original source files are NEVER modified automatically
- User explicit approval required before any apply

### 2. Protected Paths (Hard-Coded Enforcement)
The following paths are protected and CANNOT be modified by any agent:
- `.clinerules/`
- `.github/`
- `pyproject.toml`
- `package.json`
- `Cargo.toml`
- `go.mod`
- `AGENTS_AND_SKILLS.md`
- `ARCHITECTURE.md`
- `PRD.md`

The `ProtectedPaths.assert_not_protected(path)` check is called in:
- `FixProposer` before writing any proposal
- `ApprovalGate` before applying any fix
- Any repair logic that writes to disk

### 3. Provider Routing Abstraction
- All LLM calls MUST go through `call_llm(prompt, tier)` 
- Never hardcode provider-specific logic in agents/skills
- Tiers: `core` (NVIDIA → OpenRouter), `planning` (Gemini → OpenRouter)

### 4. Rate Limit Handling
- On 429/5xx: immediate fallback to next provider (no retries, no waits)
- Round-robin key rotation per provider

## Agent vs Skill Classification

| Category | LLM Call | Deterministic | Examples |
|----------|----------|---------------|----------|
| **Agent** | Yes | No | LanguageDetector, TestGenerator, FixProposer |
| **Skill** | No | Yes | ASTParser, TestRunner, DiffEngine, ApprovalGate, ProtectedPaths |

## Enforcement
These rules are enforced in code, not just prose. See:
- `src/skills/protected_paths.py` — path protection logic
- `src/agents/fix_proposer.py` — calls `assert_not_protected` before write
- `src/skills/approval_gate.py` — calls `assert_not_protected` before apply