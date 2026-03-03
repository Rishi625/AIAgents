import tempfile
from pathlib import Path

from agentic_fix.schema import EditOperation
from agentic_fix.workspace import apply_edit, preview_edit


def test_create_new_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        edit = EditOperation(path="hello.py", action="create", new_text="print('hi')\n")
        ok, msg = apply_edit(root, edit)
        assert ok
        assert (root / "hello.py").read_text() == "print('hi')\n"


def test_create_rejects_existing_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "existing.py").write_text("x = 1")
        edit = EditOperation(path="existing.py", action="create", new_text="x = 2")
        ok, msg = apply_edit(root, edit)
        assert not ok
        assert "already exists" in msg


def test_replace_existing_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "calc.py").write_text("return a - b\n")
        edit = EditOperation(
            path="calc.py", action="replace", old_text="a - b", new_text="a + b"
        )
        ok, msg = apply_edit(root, edit)
        assert ok
        assert "a + b" in (root / "calc.py").read_text()


def test_replace_missing_old_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "calc.py").write_text("return a + b\n")
        edit = EditOperation(
            path="calc.py", action="replace", old_text="NOTFOUND", new_text="x"
        )
        ok, msg = apply_edit(root, edit)
        assert not ok
        assert "old_text not found" in msg


def test_replace_missing_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        edit = EditOperation(
            path="nope.py", action="replace", old_text="x", new_text="y"
        )
        ok, msg = apply_edit(root, edit)
        assert not ok
        assert "not found" in msg


def test_path_escape_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        edit = EditOperation(path="../../etc/passwd", action="create", new_text="bad")
        ok, msg = apply_edit(root, edit)
        assert not ok
        assert "escapes" in msg


def test_unsupported_action() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        edit = EditOperation(path="x.py", action="delete", new_text="")
        ok, msg = apply_edit(root, edit)
        assert not ok
        assert "Unsupported" in msg


def test_preview_replace() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "calc.py").write_text("return a - b\n")
        edit = EditOperation(
            path="calc.py", action="replace", old_text="a - b", new_text="a + b"
        )
        preview = preview_edit(root, edit)
        assert "old_text" in preview
        assert "new_text" in preview


def test_preview_create() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        edit = EditOperation(path="new.py", action="create", new_text="x = 1\n")
        preview = preview_edit(root, edit)
        assert "create" in preview
