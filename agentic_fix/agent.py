import json
import logging
from pathlib import Path

from .config import AgentConfig
from .context import build_repo_context
from .gemini_client import GeminiFixPlanner, GeminiPlanReviewer
from .git_utils import git_checkpoint
from .prompts import (
    PLANNER_SYSTEM_PROMPT,
    REVIEWER_SYSTEM_PROMPT,
    build_planner_prompt,
    build_reviewer_prompt,
)
from .schema import FixPlan, ReviewDecision, VerifyResult
from .session import SessionLog
from .verify import run_verification
from .workspace import apply_edit, preview_edit

logger = logging.getLogger("agentic_fix")


class AgenticFixLoop:
    def __init__(self, repo_root: Path, config: AgentConfig, verbose: bool = False) -> None:
        self.repo_root = repo_root
        self.config = config
        self.verbose = verbose
        self.planner = GeminiFixPlanner(api_key=config.api_key, model=config.model)
        self.reviewer = GeminiPlanReviewer(api_key=config.api_key, model=config.model)

    def run(
        self,
        task: str,
        verify_command: str = "",
        initial_error_context: str = "",
        dry_run: bool = False,
        git_checkpoint_enabled: bool = False,
    ) -> str:
        """
        Returns outcome string: 'success', 'done_no_edits', 'max_iterations', or 'error:<msg>'.
        """
        session = SessionLog(output_dir=self.repo_root / ".agentic_fix_logs")
        previous_result = initial_error_context.strip()

        logger.info("=== Agentic Fix Loop ===")
        logger.info("Task: %s", task)
        logger.info("Repo: %s", self.repo_root)
        logger.info("Dry run: %s", dry_run)
        if previous_result:
            logger.info("Loaded initial error context (%d chars).", len(previous_result))

        outcome = "max_iterations"

        for iteration in range(1, self.config.max_iterations + 1):
            review_decision: ReviewDecision | None = None
            edit_results: list[tuple[bool, str]] = []
            verify_result: VerifyResult | None = None

            try:
                # --- Context ---
                logger.info("[iter %d] Building repository context...", iteration)
                repo_context = build_repo_context(
                    root=self.repo_root,
                    max_files=self.config.max_files_in_context,
                    max_chars_per_file=self.config.max_chars_per_file,
                )
                logger.debug("[iter %d] Context: %d chars", iteration, len(repo_context))

                # --- Planner ---
                logger.info("[iter %d] Planner generating fix plan...", iteration)
                planner_prompt = build_planner_prompt(
                    task=task,
                    repo_context=repo_context,
                    previous_result=previous_result,
                    iteration=iteration,
                )
                plan = self.planner.generate_plan(PLANNER_SYSTEM_PROMPT, planner_prompt)
                logger.info(
                    "[iter %d] Planner proposed %d edit(s).", iteration, len(plan.edits)
                )

                # --- Reviewer ---
                plan, review_decision = self._review_plan(
                    plan, task, repo_context, previous_result, iteration
                )
                logger.info("[iter %d] Plan: %s", iteration, plan.summary)

                # --- Done check ---
                if plan.done and not plan.edits:
                    outcome = "done_no_edits"
                    logger.info("Planner marked task as complete.")
                    session.log_iteration(iteration, plan, review_decision, [], None)
                    break

                if not plan.edits:
                    outcome = "done_no_edits"
                    logger.info("No edits proposed; stopping.")
                    session.log_iteration(iteration, plan, review_decision, [], None)
                    break

                # --- Dry run preview ---
                if dry_run:
                    logger.info("[iter %d] DRY RUN — previewing edits:", iteration)
                    for edit in plan.edits:
                        logger.info("\n%s", preview_edit(self.repo_root, edit))
                    session.log_iteration(iteration, plan, review_decision, [], None)
                    outcome = "dry_run_complete"
                    break

                # --- Executor ---
                logger.info("[iter %d] Applying %d edit(s)...", iteration, len(plan.edits))
                edit_failures = []
                for edit in plan.edits:
                    ok, message = apply_edit(self.repo_root, edit)
                    edit_results.append((ok, message))
                    if ok:
                        logger.info("  %s", message)
                    else:
                        logger.warning("  FAIL: %s", message)
                        edit_failures.append(message)

                if edit_failures:
                    previous_result = "Edit failures:\n" + "\n".join(edit_failures)
                    logger.warning("[iter %d] Edit failures; retrying.", iteration)
                    session.log_iteration(iteration, plan, review_decision, edit_results, None)
                    continue

                # --- Git checkpoint ---
                if git_checkpoint_enabled:
                    git_checkpoint(self.repo_root, iteration, plan.summary)

                # --- Verifier ---
                effective_verify = verify_command or plan.verify_command
                logger.info("[iter %d] Verifier: %s", iteration, effective_verify or "[none]")
                verify_result = run_verification(effective_verify, self.repo_root)
                if verify_result.passed:
                    outcome = "success"
                    logger.info("Verification passed. Task complete.")
                    session.log_iteration(
                        iteration, plan, review_decision, edit_results, verify_result
                    )
                    break

                logger.warning("[iter %d] Verification failed.", iteration)
                logger.debug("Verifier output:\n%s", verify_result.output)
                previous_result = verify_result.output

                session.log_iteration(
                    iteration, plan, review_decision, edit_results, verify_result
                )

            except RuntimeError as exc:
                logger.error("[iter %d] Runtime error: %s", iteration, exc)
                outcome = f"error:{exc}"
                session.log_iteration(
                    iteration,
                    FixPlan(summary=str(exc), done=False),
                    review_decision,
                    edit_results,
                    verify_result,
                )
                break

        if outcome == "max_iterations":
            logger.warning("Reached max iterations (%d) without verified fix.", self.config.max_iterations)

        session.finalize(outcome)
        return outcome

    def _review_plan(
        self,
        plan: FixPlan,
        task: str,
        repo_context: str,
        previous_result: str,
        iteration: int,
    ) -> tuple[FixPlan, ReviewDecision | None]:
        if not self.config.enable_reviewer:
            logger.debug("[iter %d] Reviewer disabled.", iteration)
            return plan, None

        plan_json = json.dumps(
            {
                "summary": plan.summary,
                "done": plan.done,
                "verify_command": plan.verify_command,
                "edits": [
                    {
                        "path": e.path,
                        "action": e.action,
                        "old_text": e.old_text,
                        "new_text": e.new_text,
                    }
                    for e in plan.edits
                ],
            },
            ensure_ascii=True,
        )

        logger.info("[iter %d] Reviewer evaluating plan...", iteration)
        reviewer_prompt = build_reviewer_prompt(
            task=task,
            repo_context=repo_context,
            previous_result=previous_result,
            iteration=iteration,
            proposed_plan_json=plan_json,
        )
        decision = self.reviewer.review_plan(REVIEWER_SYSTEM_PROMPT, reviewer_prompt)
        logger.info("[iter %d] Reviewer approved: %s", iteration, decision.approved)
        if decision.feedback:
            logger.info("[iter %d] Reviewer: %s", iteration, decision.feedback)

        if decision.revised_plan:
            logger.info("[iter %d] Reviewer provided revised plan.", iteration)
            return decision.revised_plan, decision

        return plan, decision
