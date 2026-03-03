# Agentic Code Fixer (Gemini Flash)

A production-ready multi-agent AI system that reads your codebase, diagnoses bugs, and fixes them autonomously using an iterative agentic loop powered by Gemini Flash.

## Features

- **Multi-agent roles**: Planner, Reviewer, Executor, Verifier
- **Retry with exponential backoff**: handles 429/rate limits gracefully
- **Proper Python logging**: structured, timestamped, verbose mode
- **Dry-run mode**: preview proposed edits before applying
- **Session history**: every run saved as JSON for audit/replay
- **Git checkpoints**: optional commit after each iteration
- **Error context input**: seed agent with stack traces/logs
- **API health check**: validate key/model/quota from CLI
- **Test suite**: unit tests for all core modules

## Project Structure

```text
AIAgents/
├── agentic_fix/
│   ├── __init__.py
│   ├── agent.py          # Main agentic control loop
│   ├── api_check.py      # API quota/access health check
│   ├── config.py         # Env + runtime settings
│   ├── context.py        # Repo scanning + context building
│   ├── gemini_client.py  # Gemini API with retry + error handling
│   ├── git_utils.py      # Git checkpoint utilities
│   ├── logger.py         # Structured Python logging setup
│   ├── prompts.py        # Role-specific prompts
│   ├── schema.py         # Data models for plans/edits/results
│   ├── session.py        # Run session history (JSON logs)
│   ├── verify.py         # Safe verification command runner
│   └── workspace.py      # Apply/preview edits
├── tests/                # Unit tests for agent modules
│   ├── test_context.py
│   ├── test_schema.py
│   ├── test_session.py
│   ├── test_verify.py
│   └── test_workspace.py
├── sample_buggy_repo/    # Simple demo target
├── sample_complex_repo/  # Multi-file buggy demo target
├── main.py               # CLI entrypoint
├── requirements.txt
└── .gitignore
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add environment variables in `.env`:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash
MAX_AGENT_ITERATIONS=5
MAX_FILES_IN_CONTEXT=20
MAX_CHARS_PER_FILE=4000
ENABLE_REVIEWER=true
```

## Check API Quota/Access

```bash
python main.py --check-api
```

Performs a tiny live call to validate your key, model, and quota.

## Run

```bash
python main.py "Fix failing tests" --repo ./sample_complex_repo --verify "python -m pytest -q" --verbose
```

## Run Against Any External Repo

```bash
python main.py "Fix billing module bugs" --repo "C:/path/to/repo" --verify "python -m pytest -q"
```

## CLI Flags

| Flag | Description |
|------|-------------|
| `--repo PATH` | Target repo folder (default: `.`) |
| `--verify CMD` | Verification command (e.g. `pytest -q`) |
| `--verbose` | Detailed step-by-step logging |
| `--max-iterations N` | Override max loop iterations |
| `--no-reviewer` | Disable reviewer agent for this run |
| `--error-file PATH` | Seed first iteration with error logs |
| `--check-api` | Validate API key/model/quota and exit |
| `--dry-run` | Preview edits without applying |
| `--git-checkpoint` | Git commit after each iteration |

## Demo With Complex Buggy Repo

```bash
python main.py "Fix checkout pricing, shipping threshold, and tax bugs" \
  --repo ./sample_complex_repo \
  --verify "python -m pytest -q" \
  --verbose \
  --error-file ./sample_complex_repo/error_logs/pytest_failure.txt
```

## Run Tests

```bash
python -m pytest tests/ -v
```

## Agentic Multi-Agent Architecture

### 1) Context Builder
- Scans repo files (extension filtering + ignored dirs).
- Produces a bounded snapshot of file contents.

### 2) Planner Agent (Gemini Flash)
- Receives task + repo snapshot + previous failure context.
- Returns strict JSON with edits, verify command, done flag.

### 3) Reviewer Agent (Gemini Flash)
- Reviews planner output for safety/minimality/quality.
- Can approve, return feedback, or provide revised plan.

### 4) Executor
- Applies edits (`create` / `replace`).
- Path-escape protection + permission error handling.

### 5) Verifier
- Runs safe allowlisted commands with timeout.
- Captures stdout/stderr.

### 6) Reflect + Iterate
- Failed verification output fed back to next planner iteration.
- Optional `--error-file` seeds first iteration context.
- Loop stops on: success, planner done, or max iterations.

### 7) Session Logging
- Every run writes a JSON session log to `.agentic_fix_logs/`.
- Contains all iterations, plans, reviews, edits, and verify results.

### 8) Git Checkpoints
- With `--git-checkpoint`, commits after each successful edit iteration.
- Easy rollback to any iteration.
