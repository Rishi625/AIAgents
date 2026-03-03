import logging
import subprocess
from pathlib import Path

from .schema import VerifyResult

logger = logging.getLogger("agentic_fix")

ALLOWED_COMMAND_PREFIXES = ("python ", "pytest", "ruff", "mypy", "npm test", "pnpm test")
VERIFY_TIMEOUT_SECONDS = 120


def run_verification(command: str, cwd: Path) -> VerifyResult:
    command = command.strip()
    if not command:
        return VerifyResult(passed=True, output="No verification command provided.")
    if not command.startswith(ALLOWED_COMMAND_PREFIXES):
        return VerifyResult(
            passed=False,
            output=f"Blocked unsafe verification command: {command}",
        )

    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT_SECONDS,
        )
        output = f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}"
        return VerifyResult(passed=completed.returncode == 0, output=output)
    except subprocess.TimeoutExpired:
        msg = f"Verification timed out after {VERIFY_TIMEOUT_SECONDS}s: {command}"
        logger.error(msg)
        return VerifyResult(passed=False, output=msg)
    except OSError as exc:
        msg = f"Verification command failed to execute: {exc}"
        logger.error(msg)
        return VerifyResult(passed=False, output=msg)
