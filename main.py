from argparse import ArgumentParser
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from agentic_fix import AgentConfig, AgenticFixLoop
from agentic_fix.api_check import check_api_limit_status


def resolve_cli_path(raw_path: str) -> Path:
    """
    Resolve user-provided CLI paths across shells.
    Git Bash can transform '.\\foo' into '.foo', so we try safe fallbacks.
    """
    candidates = [raw_path]
    if "\\" in raw_path:
        candidates.append(raw_path.replace("\\", "/"))
    if raw_path.startswith(".") and not raw_path.startswith("./") and len(raw_path) > 1:
        # Handles Git Bash quirk: '.\\dir' can become '.dir'
        candidates.append("./" + raw_path[1:])

    for candidate in candidates:
        path = Path(candidate).resolve()
        if path.exists():
            return path

    return Path(raw_path).resolve()


def parse_args() -> ArgumentParser:
    parser = ArgumentParser(description="Agentic code-fixing loop powered by Gemini Flash.")
    parser.add_argument(
        "task",
        nargs="?",
        default="",
        help="Problem statement for the agent, e.g. 'Fix failing tests in parser module.'",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the repository root to inspect and edit.",
    )
    parser.add_argument(
        "--verify",
        default="",
        help="Optional verification command, e.g. 'pytest -q'.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed live updates for each loop step.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=0,
        help="Override MAX_AGENT_ITERATIONS from .env (0 means use env value).",
    )
    parser.add_argument(
        "--no-reviewer",
        action="store_true",
        help="Disable reviewer role for this run.",
    )
    parser.add_argument(
        "--error-file",
        default="",
        help="Optional path to a traceback/log file to seed agent context on iteration 1.",
    )
    parser.add_argument(
        "--check-api",
        action="store_true",
        help="Run a lightweight API quota/access check and exit.",
    )
    return parser


def main() -> None:
    load_dotenv()
    parser = parse_args()
    args = parser.parse_args()
    if not args.check_api and not args.task.strip():
        parser.error("task is required unless --check-api is used.")

    config = AgentConfig.from_env()
    if args.max_iterations > 0:
        config = replace(config, max_iterations=args.max_iterations)
    if args.no_reviewer:
        config = replace(config, enable_reviewer=False)

    print("=== Agentic Fix CLI ===")
    print(f"Model: {config.model}")
    if args.check_api:
        ok, message = check_api_limit_status(api_key=config.api_key, model=config.model)
        print(message)
        if not ok:
            raise SystemExit(1)
        return

    repo_root = resolve_cli_path(args.repo)
    if not repo_root.exists() or not repo_root.is_dir():
        raise ValueError(f"Invalid repo path: {repo_root}")

    print(f"Task: {args.task}")
    print(f"Repo: {repo_root}")
    print(f"Max iterations: {config.max_iterations}")
    print(f"Reviewer enabled: {config.enable_reviewer}")
    if args.verify:
        print(f"Verify command: {args.verify}")
    if args.error_file:
        print(f"Error context file: {args.error_file}")

    loop = AgenticFixLoop(repo_root=repo_root, config=config, verbose=args.verbose)
    initial_error_context = ""
    if args.error_file:
        error_path = resolve_cli_path(args.error_file)
        if not error_path.exists() or not error_path.is_file():
            raise ValueError(f"Invalid error context file: {error_path}")
        initial_error_context = error_path.read_text(encoding="utf-8")

    loop.run(
        task=args.task,
        verify_command=args.verify,
        initial_error_context=initial_error_context,
    )


if __name__ == "__main__":
    main()

