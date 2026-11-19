"""Describe how a module is imported and what its tests may use, for the agent's prompt.

Without this the model guesses the import path and avoids third-party packages, so suites for
package modules (vioreg) never even import (all 12 runs of the first vioreg attempt failed).
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path


def _top_imports(tree: ast.AST) -> set[str]:
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            names.add(n.module.split(".")[0])
    return names


def _relative_imports(tree: ast.AST) -> set[str]:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.level == 1:
            if n.module:
                out.add(n.module.split(".")[0])
            else:
                out |= {a.name for a in n.names}
    return out


def stub(source: str) -> str:
    """Signatures and first docstring lines of top-level defs and classes."""
    tree = ast.parse(source)
    lines = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
            lines.append(f"def {n.name}({ast.unparse(n.args)})" + (
                f" -> {ast.unparse(n.returns)}" if n.returns else ""))
        elif isinstance(n, ast.ClassDef):
            lines.append(f"class {n.name}:")
            for m in n.body:
                if isinstance(m, ast.FunctionDef):
                    lines.append(f"    def {m.name}({ast.unparse(m.args)})")
                elif isinstance(m, ast.AnnAssign) and isinstance(m.target, ast.Name):
                    lines.append(f"    {m.target.id}: {ast.unparse(m.annotation)}")
        elif isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) for t in n.targets):
            lines.append(ast.unparse(n)[:120])
        doc = ast.get_docstring(n) if isinstance(
            n, ast.FunctionDef | ast.ClassDef) else None
        if doc:
            lines[-1] += f"  # {doc.splitlines()[0][:100]}"
    return "\n".join(lines)


def describe_environment(module_file: Path) -> str:
    src = module_file.read_text()
    tree = ast.parse(src)
    pkg = module_file.parent if (module_file.parent / "__init__.py").exists() else None
    third = _top_imports(tree)
    parts = []
    if pkg is None:
        parts.append(f"Import the module under test with `import {module_file.stem}`.")
    else:
        parts.append(
            f"The module under test is part of the package `{pkg.name}`. Import it with "
            f"`from {pkg.name} import {module_file.stem}` (never as a bare `{module_file.stem}`). "
            f"Other modules of the package can be imported the same way."
        )
        sibs = sorted(_relative_imports(tree))
        stubs = []
        for s in sibs:
            f = pkg / f"{s}.py"
            if f.exists():
                stree = ast.parse(f.read_text())
                third |= _top_imports(stree)
                stubs.append(f"# {pkg.name}/{s}.py\n{stub(f.read_text())}")
        if stubs:
            parts.append(
                "Signatures of the package modules it uses (use the real ones in your tests, "
                "instead of faking them, when that is simpler):\n```python\n"
                + "\n\n".join(stubs) + "\n```"
            )
    ext = sorted(t for t in third if t not in sys.stdlib_module_names and t != pkg_name(pkg)
                 and importlib.util.find_spec(t) is not None)  # only what is installed
    parts.append(
        "You may use pytest, the standard library"
        + (f" and these installed packages: {', '.join(ext)}." if ext else ".")
    )
    return "\n\n".join(parts)


def pkg_name(pkg: Path | None) -> str:
    return pkg.name if pkg else ""
