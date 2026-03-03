from agentic_fix.schema import EditOperation, FixPlan, VerifyResult


def test_edit_operation_defaults() -> None:
    edit = EditOperation(path="a.py", action="create", new_text="x = 1")
    assert edit.old_text == ""


def test_fix_plan_defaults() -> None:
    plan = FixPlan(summary="test", done=False)
    assert plan.edits == []
    assert plan.verify_command == ""


def test_line_item_total() -> None:
    edit = EditOperation(path="x.py", action="replace", new_text="y", old_text="x")
    plan = FixPlan(summary="fix", done=False, edits=[edit])
    assert len(plan.edits) == 1


def test_verify_result() -> None:
    v = VerifyResult(passed=True, output="ok")
    assert v.passed
