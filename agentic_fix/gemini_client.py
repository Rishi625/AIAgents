import json
import re
from typing import Any

from google import genai
from google.genai import types

from .schema import EditOperation, FixPlan, ReviewDecision


class GeminiFixPlanner:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_plan(self, system_prompt: str, user_prompt: str) -> FixPlan:
        response = self.client.models.generate_content(
            model=self.model,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=[types.Content(role="user", parts=[types.Part(text=user_prompt)])],
        )
        text = response.text or ""
        data = self._extract_json(text)
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
        response = self.client.models.generate_content(
            model=self.model,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=[types.Content(role="user", parts=[types.Part(text=user_prompt)])],
        )
        data = GeminiFixPlanner._extract_json(response.text or "")
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
