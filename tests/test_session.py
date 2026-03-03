import json
import tempfile
from pathlib import Path

from agentic_fix.schema import FixPlan, VerifyResult
from agentic_fix.session import SessionLog


def test_session_log_creates_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp) / "logs"
        session = SessionLog(output_dir=log_dir)
        plan = FixPlan(summary="test", done=False)
        session.log_iteration(1, plan, None, [], None)
        session.finalize("success")
        assert session.path.exists()
        data = json.loads(session.path.read_text())
        assert data["outcome"] == "success"
        assert len(data["iterations"]) == 1


def test_session_log_captures_verify() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp) / "logs"
        session = SessionLog(output_dir=log_dir)
        plan = FixPlan(summary="fix", done=False)
        verify = VerifyResult(passed=False, output="FAILED test_add")
        session.log_iteration(1, plan, None, [("ok", "Updated a.py")], verify)
        session.finalize("max_iterations")
        data = json.loads(session.path.read_text())
        assert data["iterations"][0]["verify"]["passed"] is False
