import tempfile
from pathlib import Path

from agentic_fix.context import build_repo_context, iter_code_files


def test_iter_code_files_finds_py() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "app.py").write_text("x = 1")
        (root / "data.csv").write_text("a,b")
        files = list(iter_code_files(root))
        names = [f.name for f in files]
        assert "app.py" in names
        assert "data.csv" not in names


def test_iter_ignores_venv() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        venv = root / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "pkg.py").write_text("x = 1")
        (root / "main.py").write_text("x = 2")
        files = list(iter_code_files(root))
        names = [f.name for f in files]
        assert "main.py" in names
        assert "pkg.py" not in names


def test_build_repo_context_limits_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for i in range(10):
            (root / f"f{i}.py").write_text(f"x = {i}")
        ctx = build_repo_context(root, max_files=3, max_chars_per_file=500)
        assert ctx.count("### FILE:") == 3


def test_build_repo_context_limits_chars() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "big.py").write_text("x" * 5000)
        ctx = build_repo_context(root, max_files=5, max_chars_per_file=100)
        assert len(ctx) < 200
