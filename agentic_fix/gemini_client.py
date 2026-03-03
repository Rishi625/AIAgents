import json
import logging
import re
import time
from typing import Any

from google import genai
from google.genai import errors, types

from .schema import EditOperation, FixPlan, ReviewDecision

logger = logging.getLogger("agentic_fix")

DEFAULT_MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0
RETRY_MAX_DELAY = 30.0


def _call_with_retry(
    fn,
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    **kwargs,
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except errors.ClientError as exc:
            last_exc = exc
            message = str(exc)
            if "429" in message or "RESOURCE_EXHAUSTED" in message:
                delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                logger.warning(
                    "Rate limited (attempt %d/%d). Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            raise
        except (ConnectionError, TimeoutError, OSError) as exc:
            last_exc = exc
            delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
            logger.warning(
                "Network error (attempt %d/%d): %s. Retrying in %.1fs...",
                attempt,
                max_retries,
                exc,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError(
        f"Failed after {max_retries} retries. Last error: {last_exc}"
    ) from last_exc


class GeminiFixPlanner:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_plan(self, system_prompt: str, user_prompt: str) -> FixPlan:
        response = _call_with_retry(
            self.client.models.generate_content,
            model=self.model,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=[types.Content(role="user", parts=[types.Part(text=user_prompt)])],
        )
        text = response.text or ""
        try:
            data = self._extract_json(text)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Planner returned invalid JSON: %s", exc)
            return FixPlan(summary=f"JSON parse error: {exc}", done=False)

        edits = []
        for item in data.get("edits", []):
            try:
                edits.append(
                    EditOperation(
                        path=item["path"],
                        action=item["action"],
                        old_text=item.get("old_text", ""),
                        new_text=item["new_text"],
                    )
                )
            except KeyError as exc:
                logger.warning("Skipping malformed edit (missing key %s): %s", exc, item)

        return FixPlan(
            summary=data.get("summary", ""),
            done=bool(data.get("done", False)),
            edits=edits,
            verify_command=data.get("verify_command", ""),
        )

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return json.loads(stripped)
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise ValueError("Model response did not contain valid JSON.")
        return json.loads(match.group(0))


class GeminiPlanReviewer:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def review_plan(self, system_prompt: str, user_prompt: str) -> ReviewDecision:
        response = _call_with_retry(
            self.client.models.generate_content,
            model=self.model,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=[types.Content(role="user", parts=[types.Part(text=user_prompt)])],
        )
        try:
            data = GeminiFixPlanner._extract_json(response.text or "")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Reviewer returned invalid JSON: %s", exc)
            return ReviewDecision(approved=True, feedback=f"JSON parse error: {exc}")

        revised_plan_data = data.get("revised_plan")
        revised_plan = self._parse_fix_plan(revised_plan_data) if revised_plan_data else None
        return ReviewDecision(
            approved=bool(data.get("approved", False)),
            feedback=data.get("feedback", ""),
            revised_plan=revised_plan,
        )

    @staticmethod
    def _parse_fix_plan(data: dict[str, Any]) -> FixPlan:
        edits = [
            EditOperation(
                path=item["path"],
                action=item["action"],
                old_text=item.get("old_text", ""),
                new_text=item["new_text"],
            )
            for item in data.get("edits", [])
        ]
        return FixPlan(
            summary=data.get("summary", ""),
            done=bool(data.get("done", False)),
            edits=edits,
            verify_command=data.get("verify_command", ""),
        )
