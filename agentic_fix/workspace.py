from pathlib import Path

from .schema import EditOperation


def apply_edit(root: Path, edit: EditOperation) -> tuple[bool, str]:
    file_path = (root / edit.path).resolve()
    if root.resolve() not in file_path.parents and root.resolve() != file_path:
        return False, f"Path escapes repository root: {edit.path}"

    if edit.action == "create":
        if file_path.exists():
            return False, f"File already exists: {edit.path}"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(edit.new_text, encoding="utf-8")
        return True, f"Created {edit.path}"

    if edit.action != "replace":
        return False, f"Unsupported action '{edit.action}' for {edit.path}"

    if not file_path.exists():
        return False, f"File not found for replace: {edit.path}"

    content = file_path.read_text(encoding="utf-8")
    if edit.old_text not in content:
        return False, f"old_text not found in {edit.path}"

    updated = content.replace(edit.old_text, edit.new_text, 1)
    file_path.write_text(updated, encoding="utf-8")
    return True, f"Updated {edit.path}"
