"""Run a module's tests and mutmut in an isolated temp workspace and return a graded report.

Isolation here is a plain temp directory. The Docker sandbox (no network, read-only
module) is session 3; this function is what the sandbox will call.
"""
from __future__ import annotations

import json
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


class TestsFailing(Exception):
    """The supplied tests do not pass on the unmutated module, so there is nothing to grade."""

    __test__ = False  # not a pytest class

    def __init__(self, output: str):
        super().__init__("tests fail on the original module")
        self.output = output


@dataclass(frozen=True)
class GradeReport:
    grade: Grade
    line_coverage: float  # percent, 0-100
    tests_passed: int


def build_workspace(ws: Path, module_file: Path, tests_dir: Path) -> None:
    """Lay out ws/src/<module>.py, ws/tests/*.py and the pytest + mutmut config."""
    (ws / "src").mkdir(parents=True)
    shutil.copy(module_file, ws / "src" / module_file.name)
    shutil.copytree(tests_dir, ws / "tests")
    (ws / "pyproject.toml").write_text(PYPROJECT)


def _run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, check=False, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )


def run_grade(module_file: Path, tests_dir: Path, *, timeout: int = 900) -> GradeReport:
    """Grade `tests_dir` against `module_file`: baseline pytest + coverage, then mutmut."""
    with tempfile.TemporaryDirectory(prefix="mutagent-") as tmp:
        ws = Path(tmp)
        build_workspace(ws, module_file, tests_dir)

        base = _run(
            [sys.executable, "-m", "pytest", "--cov=src", "--cov-report=json", "-q"],
            ws, timeout,
        )
        if base.returncode != 0:
            raise TestsFailing(base.stdout + base.stderr)
        cov = json.loads((ws / "coverage.json").read_text())["totals"]["percent_covered"]
        passed = int(base.stdout.rsplit(" passed", 1)[0].split()[-1])

        _run([sys.executable, "-m", "mutmut", "run"], ws, timeout)
        stats = _run([sys.executable, "-m", "mutmut", "export-cicd-stats"], ws, timeout)
        stats_file = ws / "mutants" / "mutmut-cicd-stats.json"
        if not stats_file.exists():
            raise RuntimeError("mutmut produced no stats:\n" + stats.stdout + stats.stderr)
        grade = grade_from_cicd_stats(json.loads(stats_file.read_text()))
        return GradeReport(grade=grade, line_coverage=cov, tests_passed=passed)
