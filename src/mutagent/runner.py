"""Run a module's tests and mutmut in an isolated temp workspace and return a graded report.

Isolation here is a plain temp directory. The Docker sandbox (no network, read-only
module) is session 3; this function is what the sandbox will call.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from mutagent.grading import Grade, grade_from_cicd_stats

PYPROJECT = """\
[tool.pytest.ini_options]
pythonpath = ["src"]
addopts = "-p no:randomly -p no:cacheprovider"

[tool.mutmut]
paths_to_mutate = ["src/"]
tests_dir = ["tests/"]
"""

# Package mode: the module sits in a package directory (it has an __init__.py next to it).
# The whole package is copied, but only the target file is mutated and measured.
PACKAGE_PYPROJECT = """\
[tool.pytest.ini_options]
pythonpath = ["src"]
addopts = "-p no:randomly -p no:cacheprovider"

[tool.mutmut]
paths_to_mutate = ["src/{pkg}/{file}"]
also_copy = ["src/{pkg}"{extra}]
tests_dir = ["tests/"]
"""


class TestsFailing(Exception):
    """The supplied tests do not pass on the unmutated module, so there is nothing to grade."""

    __test__ = False  # not a pytest class

    def __init__(self, output: str):
        super().__init__("tests fail on the original module")
        self.output = output


@dataclass(frozen=True)
class Survivor:
    name: str
    diff: str  # unified diff of the mutation that no test caught


@dataclass(frozen=True)
class GradeReport:
    grade: Grade
    line_coverage: float  # percent, 0-100
    tests_passed: int
    missing_lines: tuple[int, ...] = ()
    survivors: tuple[Survivor, ...] = ()


def pick_survivors(names: list[str], k: int) -> list[str]:
    """Pick up to k survivor names, round-robin across functions so one function
    with many survivors does not crowd out the rest."""
    groups: dict[str, list[str]] = {}
    for n in names:
        groups.setdefault(n.rsplit("__mutmut_", 1)[0], []).append(n)
    picked: list[str] = []
    while len(picked) < k and any(groups.values()):
        for g in groups.values():
            if g and len(picked) < k:
                picked.append(g.pop(0))
    return picked


def protect_raise_lines(source: str) -> str:
    """Add `# pragma: no mutate` to every line of every `raise` statement, so mutmut does
    not mutate exception messages. Message text is rarely in a spec; scoring tests on it
    rewards pinning implementation details (measured on ratelimiter: 100% vs 72%)."""
    lines = source.split("\n")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Raise):
            for n in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                if "pragma: no mutate" not in lines[n - 1]:
                    lines[n - 1] += "  # pragma: no mutate"
    return "\n".join(lines)


def build_workspace(ws: Path, module_file: Path, tests_dir: Path, *,
                    score_messages: bool = False) -> str:
    """Lay out ws/src, ws/tests and the pytest + mutmut config. Returns the import name of
    the module under test (for coverage): "mod" or, in package mode, "pkg.mod"."""
    (ws / "src").mkdir(parents=True)
    pkg_dir = module_file.parent if (module_file.parent / "__init__.py").exists() else None
    if pkg_dir is None:
        src = module_file.read_text()
        (ws / "src" / module_file.name).write_text(
            src if score_messages else protect_raise_lines(src))
        cfg, target = PYPROJECT, module_file.stem
    else:
        dest = ws / "src" / pkg_dir.name
        shutil.copytree(pkg_dir, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if not score_messages:
            f = dest / module_file.name
            f.write_text(protect_raise_lines(f.read_text()))
        cfg = PACKAGE_PYPROJECT  # filled in below, once the root files are known
        target = f"{pkg_dir.name}.{module_file.stem}"
    shutil.copytree(tests_dir, ws / "tests")
    # Files the tests expect at the project root (e.g. docker/IMAGE_REF): a `root_files`
    # directory next to `src/` is copied into the workspace root.
    root_files = module_file.parents[1 if pkg_dir is None else 2] / "root_files"
    extra = ""
    if root_files.is_dir():
        shutil.copytree(root_files, ws, dirs_exist_ok=True)
        # mutmut runs the tests inside a copy of the tree, so these must be listed too
        extra = "".join(f', "{p.name}"' for p in sorted(root_files.iterdir()))
    if pkg_dir is not None:
        cfg = cfg.format(pkg=pkg_dir.name, file=module_file.name, extra=extra)
    (ws / "pyproject.toml").write_text(cfg)
    return target


def _run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, check=False, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )


def run_grade(module_file: Path, tests_dir: Path, *, timeout: int = 900,
              max_survivors: int = 5, score_messages: bool = False) -> GradeReport:
    """Grade `tests_dir` against `module_file`: baseline pytest + coverage, then mutmut."""
    with tempfile.TemporaryDirectory(prefix="mutagent-") as tmp:
        ws = Path(tmp)
        target = build_workspace(ws, module_file, tests_dir, score_messages=score_messages)

        base = _run(
            [sys.executable, "-m", "pytest", f"--cov={target}", "--cov-report=json", "-q"],
            ws, timeout,
        )
        if base.returncode != 0:
            raise TestsFailing(base.stdout + base.stderr)
        cov_file = ws / "coverage.json"
        if cov_file.exists():
            cov_data = json.loads(cov_file.read_text())
            cov = cov_data["totals"]["percent_covered"]
            missing = tuple(
                n for f in cov_data["files"].values() for n in f.get("missing_lines", [])
            )
        else:  # the module under test was never imported by any test
            cov, missing = 0.0, ()
        m = re.search(r"(\d+) passed", base.stdout)
        passed = int(m.group(1)) if m else 0
        if passed == 0:  # e.g. the whole module was skipped: exit code 0 but nothing ran
            raise TestsFailing("no test passed (all skipped, deselected or none collected)\n"
                               + base.stdout[-1500:])

        _run([sys.executable, "-m", "mutmut", "run"], ws, timeout)
        stats = _run([sys.executable, "-m", "mutmut", "export-cicd-stats"], ws, timeout)
        stats_file = ws / "mutants" / "mutmut-cicd-stats.json"
        if not stats_file.exists():
            raise RuntimeError("mutmut produced no stats:\n" + stats.stdout + stats.stderr)
        grade = grade_from_cicd_stats(json.loads(stats_file.read_text()))
        res = _run([sys.executable, "-m", "mutmut", "results"], ws, timeout).stdout
        names = re.findall(r"^\s*(\S+): survived", res, flags=re.MULTILINE)
        survivors = []
        for n in pick_survivors(names, max_survivors):
            shown = _run([sys.executable, "-m", "mutmut", "show", n], ws, timeout).stdout
            survivors.append(Survivor(n, shown.split("\n", 1)[-1].strip()))
        return GradeReport(grade, cov, passed, missing, tuple(survivors))


def preflight(module_file: Path, tests_dir: Path, timeout: int = 300) -> str | None:
    """Cheap environment check before any API spend: do the module's own tests pass here
    (right Python, dependencies installed)? Returns None if fine, else the failure text."""
    with tempfile.TemporaryDirectory(prefix="mutagent-pre-") as tmp:
        ws = Path(tmp)
        build_workspace(ws, module_file, tests_dir)
        r = _run([sys.executable, "-m", "pytest", "-q", "-x"], ws, timeout)
        return None if r.returncode == 0 else (r.stdout + r.stderr)[-1500:]
