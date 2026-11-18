"""Grade tests inside a locked-down Docker container (no network, read-only inputs)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mutagent.grading import Grade
from mutagent.runner import GradeReport, TestsFailing

IMAGE = "mutagent-grader:latest"


def docker_command(module_file: Path, tests_dir: Path, *, timeout: int = 900,
                   image: str = IMAGE) -> list[str]:
    module_file, tests_dir = module_file.resolve(), tests_dir.resolve()
    return [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only", "--tmpfs", "/tmp:rw,exec,size=512m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--memory", "2g", "--cpus", "2", "--pids-limit", "256",
        "-v", f"{module_file}:/in/{module_file.name}:ro",
        "-v", f"{tests_dir}:/in/tests:ro",
        image, f"/in/{module_file.name}", "/in/tests", "--timeout", str(timeout),
    ]


def parse_output(stdout: str) -> GradeReport:
    data = json.loads(stdout.strip().splitlines()[-1])
    if data.get("error") == "tests_failing":
        raise TestsFailing(data["output"])
    return GradeReport(
        grade=Grade(data["killed"], data["survived"], data["timeout"], data["no_tests"]),
        line_coverage=data["line_coverage"],
        tests_passed=data["tests_passed"],
    )


def run_grade_docker(module_file: Path, tests_dir: Path, *, timeout: int = 900) -> GradeReport:
    proc = subprocess.run(
        docker_command(module_file, tests_dir, timeout=timeout),
        check=False, capture_output=True, text=True, timeout=timeout + 60,
    )
    if proc.returncode not in (0, 2):
        raise RuntimeError(f"sandbox failed ({proc.returncode}):\n{proc.stderr[-2000:]}")
    return parse_output(proc.stdout)
