from pathlib import Path
from typing import Iterable


IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".cursor"}
CODE_EXTENSIONS = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt"}


def iter_code_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in CODE_EXTENSIONS:
            yield path


def build_repo_context(root: Path, max_files: int, max_chars_per_file: int) -> str:
    parts: list[str] = []
    for index, file_path in enumerate(iter_code_files(root)):
        if index >= max_files:
            break
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = file_path.relative_to(root).as_posix()
        parts.append(f"### FILE: {relative}\n{content[:max_chars_per_file]}")
    return "\n\n".join(parts)
