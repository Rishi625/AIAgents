import subprocess
from pathlib import Path

from .schema import VerifyResult

ALLOWED_COMMAND_PREFIXES = ("python ", "pytest", "ruff", "mypy", "npm test", "pnpm test")


def run_verification(command: str, cwd: Path) -> VerifyResult:
    command = command.strip()
    if not command:
        return VerifyResult(passed=True, output="No verification command provided.")
    if not command.startswith(ALLOWED_COMMAND_PREFIXES):
        return VerifyResult(
            passed=False,
            output=f"Blocked unsafe verification command: {command}",
        )

    completed = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
    )
    output = f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}"
    return VerifyResult(passed=completed.returncode == 0, output=output)
