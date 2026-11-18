from pathlib import Path


def write_tests(workspace: Path, rel_path: str, content: str) -> Path:
    """Write a generated test file; refuse anything outside workspace/tests."""
    tests_dir = (workspace / "tests").resolve()
    target = (tests_dir / rel_path).resolve()
    if not target.is_relative_to(tests_dir):
        raise PermissionError(f"refusing to write outside tests/: {rel_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return target
