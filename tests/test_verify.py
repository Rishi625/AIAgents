import tempfile
from pathlib import Path

from agentic_fix.verify import run_verification


def test_empty_command_passes() -> None:
    result = run_verification("", Path("."))
    assert result.passed


def test_blocked_command() -> None:
    result = run_verification("rm -rf /", Path("."))
    assert not result.passed
    assert "Blocked" in result.output


def test_allowed_command_success() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_verification("python -c \"print('ok')\"", Path(tmp))
        assert result.passed
        assert "ok" in result.output


def test_allowed_command_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_verification("python -c \"raise SystemExit(1)\"", Path(tmp))
        assert not result.passed
