import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("agentic_fix")


def is_git_repo(cwd: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def git_checkpoint(cwd: Path, iteration: int, summary: str) -> bool:
    if not is_git_repo(cwd):
        logger.debug("Not a git repo; skipping checkpoint.")
        return False

    subprocess.run(["git", "add", "-A"], cwd=str(cwd), capture_output=True)
    msg = f"[agentic-fix] iteration {iteration}: {summary[:72]}"
    result = subprocess.run(
        ["git", "commit", "-m", msg, "--allow-empty"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        logger.info("Git checkpoint: %s", msg)
        return True

    logger.warning("Git checkpoint failed: %s", result.stderr.strip())
    return False
