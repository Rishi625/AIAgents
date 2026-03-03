import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .schema import FixPlan, ReviewDecision, VerifyResult

logger = logging.getLogger("agentic_fix")


class SessionLog:
    """Captures a full run history and writes it to a JSON file."""

    def __init__(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = output_dir / f"session_{timestamp}.json"
        self.data: dict[str, Any] = {
            "started_at": datetime.now().isoformat(),
            "iterations": [],
        }

    def log_iteration(
        self,
        iteration: int,
        plan: FixPlan,
        review: ReviewDecision | None,
        edit_results: list[tuple[bool, str]],
        verify: VerifyResult | None,
    ) -> None:
        entry: dict[str, Any] = {
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "plan": asdict(plan),
        }
        if review:
            entry["review"] = {
                "approved": review.approved,
                "feedback": review.feedback,
                "has_revised_plan": review.revised_plan is not None,
            }
        entry["edit_results"] = [
            {"ok": ok, "message": msg} for ok, msg in edit_results
        ]
        if verify:
            entry["verify"] = {"passed": verify.passed, "output": verify.output[:2000]}

        self.data["iterations"].append(entry)

    def finalize(self, outcome: str) -> None:
        self.data["finished_at"] = datetime.now().isoformat()
        self.data["outcome"] = outcome
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        logger.info("Session log saved to %s", self.path)
