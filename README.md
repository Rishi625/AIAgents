# Agentic Code Fixer (Gemini Flash)

This repo now contains an end-to-end starter pipeline for a multi-agent AI system that:

1. Reads your codebase.
2. Uses a **Planner agent** (Gemini Flash) to propose targeted edits.
3. Uses a **Reviewer agent** (Gemini Flash) to critique/revise the plan.
4. Applies edits in an agentic loop.
5. Runs verification commands (tests/lint) via a verifier role.
6. Iterates until verified or max iterations reached.

## Project Structure

```text
AIAgents/
├── agentic_fix/
│   ├── __init__.py
│   ├── agent.py          # Main agentic control loop
│   ├── config.py         # Env + runtime settings
│   ├── context.py        # Repo scanning + context building
│   ├── gemini_client.py  # Gemini API wrappers for planner/reviewer
│   ├── prompts.py        # Role-specific prompts
│   ├── schema.py         # Data models for plans/edits/results
│   ├── verify.py         # Safe verification command runner
│   └── workspace.py      # Apply create/replace edits
├── sample_buggy_repo/    # Demo target repo with intentional bug
├── sample_complex_repo/  # Larger multi-file buggy demo repo
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

## Run

```bash
python main.py "Fix import errors in the package" --repo . --verify "python -m pytest -q"
```

If `--verify` is not provided, the agent can use a verification command suggested by the model.

## Run Against Another Repo

Yes, you can point this agent to any other repository folder using `--repo`.

```bash
python main.py "Fix failing tests" --repo "C:\path\to\another\repo" --verify "python -m pytest -q"
```

## Live CLI Updates

Use `--verbose` to stream more detailed progress in the terminal:

```bash
python main.py "Fix failing tests" --repo . --verify "python -m pytest -q" --verbose
```

Useful CLI flags:
- `--max-iterations 8` to override iteration limit for one run.
- `--no-reviewer` to disable reviewer role for one run.
- `--error-file path/to/errors.txt` to seed first-iteration error context.
- `--check-api` to run API quota/access health check only.

## Check API Quota/Access

If web UI says quota is available but CLI fails, run:

```bash
python main.py --check-api
```

This performs a tiny live call using your configured `GEMINI_API_KEY` and `GEMINI_MODEL`, then prints:
- success + token usage (if available), or
- detailed quota/auth error (including 429/resource exhausted).

## Demo With Separate Buggy Folder

This repo includes `sample_buggy_repo` with an intentional bug in `calc.py`.
Try:

```bash
python main.py "Fix bug in add function" --repo .\sample_buggy_repo --verify "python -m pytest -q" --verbose
```

For a larger, more realistic target with multiple failing tests:

```bash
python main.py "Fix checkout pricing, shipping threshold, and tax bugs" --repo .\sample_complex_repo --verify "python -m pytest -q" --verbose --error-file .\sample_complex_repo\error_logs\pytest_failure.txt
```

## Agentic Multi-Agent Architecture

### 1) Context Builder
- Scans repository files (with extension filtering + ignored folders).
- Produces a bounded snapshot of file contents for the model.

### 2) Planner Agent (Gemini Flash)
- Receives:
  - task
  - current repository snapshot
  - previous iteration verification feedback
- Returns strict JSON:
  - `summary`
  - `edits[]` (create/replace operations)
  - `verify_command`
  - `done`

### 3) Reviewer Agent (Gemini Flash)
- Reviews planner output for safety/minimality/quality.
- Can:
  - approve existing plan, or
  - return feedback, or
  - provide a revised plan.

### 4) Executor Role
- Applies each edit to the workspace:
  - `create`: write a new file
  - `replace`: find `old_text` and replace with `new_text`

### 5) Verifier Role
- Executes safe allowlisted commands (`python`, `pytest`, `ruff`, etc.).
- Captures stdout/stderr.

### 6) Reflect + Iterate
- If verification fails, output is fed into the next planning iteration.
- Optional startup logs/errors passed by `--error-file` are used as initial context in iteration 1.
- Loop stops when:
  - verification passes, or
  - planner says done with no edits, or
  - max iterations reached.

## How You Can Extend This

- Add richer tools (AST edits, symbol search, test selection).
- Add memory/state file per run for better long-horizon tasks.
- Add Git integration for branch-per-fix and commit checkpoints.
- Add guardrails:
  - block edits to sensitive files
  - require human approval before apply
  - dry-run mode for previewing patch plans
