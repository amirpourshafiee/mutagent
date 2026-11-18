import ast

BANNED_MODULES = {"mutmut", "inspect"}
BANNED_CALLS = {"open", "exec", "eval"}


def find_cheats(test_source: str) -> list[str]:
    """Return reasons a generated test file looks like it games the grader."""
    problems = []
    for node in ast.walk(ast.parse(test_source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in BANNED_MODULES:
                    problems.append(f"line {node.lineno}: imports {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in BANNED_MODULES:
                problems.append(f"line {node.lineno}: imports from {node.module}")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in BANNED_CALLS
        ):
            problems.append(f"line {node.lineno}: calls {node.func.id}()")
    return problems
