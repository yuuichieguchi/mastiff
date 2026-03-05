# Mastiff

[![PyPI version](https://img.shields.io/pypi/v/mastiff)](https://pypi.org/project/mastiff/)
[![Python 3.12+](https://img.shields.io/pypi/pyversions/mastiff)](https://pypi.org/project/mastiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AI code review agent that detects dangerous patterns in LLM-generated code.

Mastiff analyzes git diffs using Claude or OpenAI to detect production-risk patterns across five categories — blocking/deadlocks, race conditions, performance degradation, resource leaks, and security vulnerabilities — scoring each finding by severity and confidence. Works with API keys or directly through the `claude` / `codex` CLI (no API key required).

## Why Mastiff?

LLM-generated code often looks correct at first glance but can contain subtle patterns that only manifest in production:

- **Event loop blocking** — synchronous calls in async contexts that freeze the application
- **Race conditions** — shared mutable state accessed without proper synchronization
- **O(n²) algorithms** — nested loops and unbounded queries that degrade with scale
- **Resource leaks** — file handles, connections, and sockets opened but never closed
- **Security vulnerabilities** — SQL injection, command injection, XSS, hardcoded secrets

Traditional linters catch syntax and style issues. Mastiff focuses specifically on the patterns LLMs tend to introduce — not to replace linters, but to complement them with production-risk awareness.

## What It Detects

| Category | Description | Examples |
|---|---|---|
| Blocking/Deadlock | Synchronous blocking calls in async contexts, potential deadlocks | `time.sleep()` in async, synchronous I/O in event loop, inconsistent lock ordering |
| Race Condition | Shared mutable state without synchronization, TOCTOU | Global variable from multiple threads without locks, non-atomic read-modify-write |
| Degradation | O(n²) algorithms, excessive allocations, unbounded growth | Nested loops, loading entire DB table into memory, missing pagination |
| Resource Leak | Resources opened but not properly closed | `open()` without context manager, DB connection not returned to pool |
| Security | SQL injection, XSS, command injection, SSRF, hardcoded secrets | String-concatenated SQL queries, `os.system()` with user input, hardcoded API keys |

## Quick Start

```bash
pip install mastiff
export ANTHROPIC_API_KEY="sk-ant-..."
mastiff review --staged
```

Alternative installation methods:

```bash
pipx install mastiff
# or
uv tool install mastiff
```

Get your API key at https://console.anthropic.com/

**With CLI providers (no API key needed):**

If you have `claude` or `codex` CLI installed, Mastiff can use them directly — no API key required:

```bash
pip install mastiff
# claude CLI or codex CLI must be on PATH
mastiff review --staged
```

Mastiff auto-detects available providers in this order: `claude` CLI → `codex` CLI → `ANTHROPIC_API_KEY` → `OPENAI_API_KEY`. To force a specific provider:

```yaml
# mastiff.yaml
api:
  provider: claude-code  # or: codex, anthropic, openai
```

**With OpenAI:**

```bash
pip install "mastiff[openai]"
export OPENAI_API_KEY="sk-..."
mastiff review --staged
```

Supported OpenAI models: gpt-4.1, gpt-4o, gpt-4o-mini.

## Output Example

**Terminal (default):**

```
                    Review Findings
┏━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ File         ┃ Line ┃ Severity ┃ Category      ┃ Title                      ┃ Confidence ┃
┡━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ api/users.py │ 42   │ critical │ blocking      │ time.sleep in async handler │ 92%        │
│ db/pool.py   │ 15   │ warning  │ resource_leak │ Connection not returned     │ 78%        │
└──────────────┴──────┴──────────┴───────────────┴────────────────────────────┴────────────┘
```

**JSON (`--format json`):**

```json
{
  "findings": [
    {
      "rule_id": "blocking-sync-sleep",
      "category": "blocking",
      "severity": "critical",
      "file_path": "api/users.py",
      "line_start": 42,
      "title": "time.sleep in async handler",
      "confidence": 0.92
    }
  ]
}
```

**Agent (`--format agent`):**

```
[CRITICAL] src/api/users.py:42 blocking-sync-in-async
time.sleep() blocks the event loop in async handler
FIX: Replace time.sleep(n) with await asyncio.sleep(n)
```

## Usage

### CLI

```bash
# Review staged changes
mastiff review --staged

# Review a commit range
mastiff review HEAD~3..HEAD

# Choose review depth
mastiff review --staged --profile quick

# JSON output
mastiff review --staged --format json

# Strict mode: exit 2 on any finding
mastiff review --staged --strict

# Agent-friendly output (plain text, no ANSI)
mastiff review --staged --format agent

# Watch mode: continuous monitoring
mastiff watch --profile quick --format agent
```

**Review profiles:**

| Profile | Diff budget | Context budget | Use case |
|---|---|---|---|
| quick | 5,000 tokens | 3,000 tokens | Pre-commit, editor saves |
| standard | 20,000 tokens | 15,000 tokens | PR review (default) |
| deep | 50,000 tokens | 30,000 tokens | Release audits |

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Success, no findings |
| 1 | Runtime error (config, API, etc.) |
| 2 | Success, findings present (`--strict` or `--format agent`) |

### Pre-commit Hook

```bash
# Install the pre-commit hook
mastiff install

# Commits are automatically reviewed
git commit -m "feat: add user endpoint"
# → mastiff reviews staged changes
```

In CI environments (`CI=true`), the hook runs in strict mode and blocks on any finding. When a baseline exists, only new findings are reported.

### LSP Server (Experimental)

```bash
mastiff server
```

Provides real-time diagnostics on file save (quick profile). Configure your editor's LSP client to connect to mastiff.

### With Claude Code

Mastiff is designed to review LLM-generated code. When using [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as your development agent, Mastiff acts as an automated safety net that catches production-risk patterns before they reach your codebase.

**Automatic feedback loop (recommended):**

```bash
mastiff install --claude-code
```

This installs a PostToolUse hook that automatically reviews every file Claude Code writes or edits. When issues are found, they are fed back to Claude Code via stderr, creating an automatic fix loop.

**Pre-commit hook:**

Install the hook once and every commit Claude Code creates is automatically reviewed:

```bash
mastiff install
```

Claude Code commits through git, so the pre-commit hook runs transparently on every commit. Critical findings block the commit, giving you a chance to review before the code lands.

**CI integration:**

Add Mastiff to your CI pipeline to review every pull request that Claude Code opens:

```yaml
# .github/workflows/ci.yml
- run: pip install mastiff
- run: mastiff review origin/main..HEAD --strict --format json
```

**Manual review after a session:**

After Claude Code completes a task in a worktree, review all changes before merging:

```bash
mastiff review main..HEAD --profile deep
```

### With Codex CLI

```bash
mastiff install --codex
```

Installs a git `post-commit` hook. Since Codex CLI applies changes via commits, every commit is automatically reviewed. Existing post-commit hooks are preserved and chained.

## Baseline

```bash
# Record current findings as baseline
mastiff baseline

# Only new findings are reported from now on

# Regenerate after refactoring
mastiff baseline --rebase
```

The baseline uses fingerprint-based stable IDs that are independent of line numbers, so minor code shifts don't invalidate existing suppressions.

## Configuration

Generate a config file:

```bash
mastiff init
```

This creates `mastiff.yaml` with documented defaults. Key settings:

```yaml
api:
  provider: null                      # Auto-detect (claude-code, codex, anthropic, openai)
  model: claude-opus-4-20250514      # Model to use

detection:
  min_confidence: 0.6           # Minimum confidence to report

security:
  never_send_paths:             # Files never sent to the API
    - .env
    - "*.pem"
    - "*.key"

cost:
  max_cost_usd_per_run: 1.00   # Per-run cost limit
```

All config models use Pydantic `extra="forbid"`, so typos in config keys are caught immediately.

## Security & Privacy

Mastiff sends code to an LLM for analysis (via API or CLI). Here is what it does to minimize exposure:

- **What is sent**: Only the diff is sent — never complete source files. Import tracing may include small fragments from related files, bounded by a token budget.
- **Automatic redaction**: Built-in regex patterns detect API keys, tokens, passwords, and private key headers. Detected values are replaced with `[REDACTED]` before sending. The Redactor also exposes Shannon entropy analysis for identifying high-entropy strings.
- **File exclusion**: The `never_send_paths` setting excludes sensitive file patterns (`.env`, `*.pem`, `*.key`, etc.) by default. These files are filtered out before any API call.
- **Output sanitization**: ANSI escape sequences and control characters are stripped from all output to prevent terminal injection.
- **Prompt injection defense**: User-supplied data (diffs, context) is wrapped in delimiter tags (`<diff>`, `<context>`) and the system prompt establishes reviewer-only behavior.

This is a best-effort approach to minimize sensitive data exposure. It does not guarantee that no secrets are sent. Review your `never_send_paths` configuration and consider the sensitivity of your codebase before use.

## Cost Control

Approximate cost per review when using API providers (depends on diff size and API pricing):

| Profile | Estimated cost |
|---|---|
| quick | ~$0.01–0.05 |
| standard | ~$0.05–0.30 |
| deep | ~$0.10–0.50 |

CLI providers (`claude-code`, `codex`) use your existing subscription — no per-request API charges.

The `cost.max_cost_usd_per_run` setting (default: $1.00) enforces a per-run budget for API providers.

## Migration

### From v0.2.0

- **CLI providers**: Mastiff now auto-detects `claude` and `codex` CLIs and prefers them over API keys. If you want to keep using API keys when a CLI is also installed, set `api.provider: anthropic` (or `openai`) explicitly in `mastiff.yaml`.
- **New provider names**: `claude-code` and `codex` are now valid values for `api.provider`.

### From v0.1.0

- **Exit code change**: `--strict` now exits with code 2 (was 1) when findings are present. Update CI scripts that check for `exit 1`.
- **New category**: The `security` detection category is enabled by default. If you explicitly list categories in `mastiff.yaml`, add `security: true` to enable it.

## Requirements

- Python >= 3.12
- One of: `claude` CLI, `codex` CLI, [Anthropic API key](https://console.anthropic.com/), or [OpenAI API key](https://platform.openai.com/)
- Git

**Optional extras:**

```bash
pip install "mastiff[tree-sitter]"  # Enhanced import tracing
pip install "mastiff[lsp]"          # LSP server support
pip install "mastiff[openai]"       # OpenAI provider support
```

## Development

```bash
git clone <repo> && cd mastiff
uv sync --all-extras
pytest                 # 325 tests
ruff check .           # lint
mypy src/              # type check
```

**Package structure:**

```
src/mastiff/
├── _internal/       # Git and subprocess utilities
├── analysis/        # Categories, prompt building, LLM client
├── cli/             # Commands and terminal output
├── config/          # Schema, loader, defaults
├── context/         # Language parsers, import tracer, resolver
├── core/            # Engine, models, fingerprinting, severity
├── diff/            # Diff parsing, filtering, collection
├── integrations/    # Pre-commit, Claude Code, Codex hooks, LSP server
├── observability/   # Logging and metrics
└── security/        # Secret patterns, redactor, sanitizer
```

## License

[MIT](LICENSE)
