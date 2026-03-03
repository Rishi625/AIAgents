from pathlib import Path
import json
from datetime import datetime

from .config import AgentConfig
from .context import build_repo_context
from .gemini_client import GeminiFixPlanner, GeminiPlanReviewer
from .prompts import (
    PLANNER_SYSTEM_PROMPT,
    REVIEWER_SYSTEM_PROMPT,
    build_planner_prompt,
    build_reviewer_prompt,
)
from .schema import FixPlan
from .verify import run_verification
from .workspace import apply_edit


class AgenticFixLoop:
    def __init__(self, repo_root: Path, config: AgentConfig, verbose: bool = False) -> None:
        self.repo_root = repo_root
        self.config = config
        self.verbose = verbose
        self.planner = GeminiFixPlanner(api_key=config.api_key, model=config.model)
        self.reviewer = GeminiPlanReviewer(api_key=config.api_key, model=config.model)

    def run(self, task: str, verify_command: str = "", initial_error_context: str = "") -> None:
        previous_result = initial_error_context.strip()
        self._log("Starting agentic loop.", always=True)
        if previous_result:
            self._log("Loaded initial error context for first iteration.", always=True)
        for iteration in range(1, self.config.max_iterations + 1):
            self._log(f"[iteration {iteration}] Building repository context...", always=True)
            repo_context = build_repo_context(
                root=self.repo_root,
                max_files=self.config.max_files_in_context,
                max_chars_per_file=self.config.max_chars_per_file,
            )
            self._log(
                f"[iteration {iteration}] Context size: {len(repo_context)} chars",
                always=False,
            )

            self._log(f"[iteration {iteration}] Planner creating fix plan...", always=True)
            planner_prompt = build_planner_prompt(
                task=task,
                repo_context=repo_context,
                previous_result=previous_result,
                iteration=iteration,
            )
            plan = self.planner.generate_plan(PLANNER_SYSTEM_PROMPT, planner_prompt)
            self._log(
                f"[iteration {iteration}] Planner proposed {len(plan.edits)} edit(s).",
                always=True,
            )
            plan = self._review_plan_if_enabled(
                plan=plan,
                task=task,
                repo_context=repo_context,
                previous_result=previous_result,
                iteration=iteration,
            )

            self._log(f"[iteration {iteration}] Plan summary: {plan.summary}", always=True)

            if plan.done and not plan.edits:
                self._log("Planner marked task as complete.", always=True)
                return

            if not plan.edits:
                self._log("No edits proposed; stopping loop.", always=True)
                return

            edit_failures = []
            self._log(f"[iteration {iteration}] Applying edits...", always=True)
            for edit in plan.edits:
                ok, message = apply_edit(self.repo_root, edit)
                self._log(message, always=True)
                if not ok:
                    edit_failures.append(message)

            if edit_failures:
                previous_result = "Edit failures:\n" + "\n".join(edit_failures)
                self._log(
                    f"[iteration {iteration}] Edit failures encountered, retrying next iteration.",
                    always=True,
                )
                continue

            effective_verify = verify_command or plan.verify_command
            self._log(
                f"[iteration {iteration}] Running verifier: {effective_verify or '[none]'}",
                always=True,
            )
            verify = run_verification(effective_verify, self.repo_root)
            self._log(verify.output, always=self.verbose)
            if verify.passed:
                self._log("Verification passed. Task complete.", always=True)
                return

            previous_result = verify.output
            self._log(
                f"[iteration {iteration}] Verification failed; feeding output back to planner.",
                always=True,
            )

        self._log("Reached max iterations without a verified fix.", always=True)

    def _review_plan_if_enabled(
        self,
        plan: FixPlan,
        task: str,
        repo_context: str,
        previous_result: str,
        iteration: int,
    ) -> FixPlan:
        if not self.config.enable_reviewer:
            self._log(f"[iteration {iteration}] Reviewer disabled for this run.", always=False)
            return plan

        plan_json = json.dumps(
            {
                "summary": plan.summary,
                "done": plan.done,
                "verify_command": plan.verify_command,
                "edits": [
                    {
                        "path": edit.path,
                        "action": edit.action,
                        "old_text": edit.old_text,
                        "new_text": edit.new_text,
                    }
                    for edit in plan.edits
                ],
            },
            ensure_ascii=True,
        )

        reviewer_prompt = build_reviewer_prompt(
            task=task,
            repo_context=repo_context,
            previous_result=previous_result,
            iteration=iteration,
            proposed_plan_json=plan_json,
        )
        decision = self.reviewer.review_plan(REVIEWER_SYSTEM_PROMPT, reviewer_prompt)
        self._log(f"[iteration {iteration}] Reviewer approved: {decision.approved}", always=True)
        if decision.feedback:
            self._log(f"[iteration {iteration}] Reviewer feedback: {decision.feedback}", always=True)

        if decision.revised_plan:
            self._log(f"[iteration {iteration}] Reviewer provided revised plan.", always=True)
            return decision.revised_plan

        return plan

    def _log(self, message: str, always: bool) -> None:
        if not always and not self.verbose:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
