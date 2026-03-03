from dataclasses import dataclass, field
from typing import List


@dataclass
class EditOperation:
    path: str
    action: str
    new_text: str
    old_text: str = ""


@dataclass
class FixPlan:
    summary: str
    done: bool
    edits: List[EditOperation] = field(default_factory=list)
    verify_command: str = ""


@dataclass
class ReviewDecision:
    approved: bool
    feedback: str
    revised_plan: FixPlan | None = None


@dataclass
class VerifyResult:
    passed: bool
    output: str
