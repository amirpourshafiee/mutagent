import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mutagent.cli import main, report_to_json
from mutagent.grading import Grade
from mutagent.runner import GradeReport, Survivor, TestsFailing
from mutagent.sandbox import docker_command, parse_output, run_grade_docker

RL = Path(__file__).parent.parent / "bench" / "modules" / "ratelimiter"
MOD, TESTS = RL / "src" / "ratelimiter.py", RL / "human_tests"


def test_command_is_locked_down():
    cmd = docker_command(MOD, TESTS)
    joined = " ".join(cmd)
    for flag in ("--network none", "--read-only", "--cap-drop ALL",
                 "no-new-privileges", "--pids-limit", "--memory"):
        assert flag in joined
    mounts = [cmd[i + 1] for i, c in enumerate(cmd) if c == "-v"]
    assert len(mounts) == 2 and all(m.endswith(":ro") for m in mounts)


def test_report_json_roundtrip():
    rep = GradeReport(Grade(29, 14, 1, 2), 91.5, 12, (3, 4), (Survivor("m_1", "-a\n+b"),))
    assert parse_output("noise\n" + report_to_json(rep)) == rep


def test_tests_failing_is_raised():
    out = json.dumps({"error": "tests_failing", "output": "boom"})
    with pytest.raises(TestsFailing):
        parse_output(out)


@pytest.mark.slow
def test_cli_in_process(capsys):
    assert main([str(MOD), str(TESTS)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert (data["killed"], data["survived"]) == (29, 2)


def _docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], check=False, capture_output=True).returncode == 0


@pytest.mark.slow
@pytest.mark.skipif(not _docker_ready(), reason="docker not installed or daemon not running")
def test_docker_golden_matches_host():
    rep = run_grade_docker(MOD, TESTS)
    assert (rep.grade.killed, rep.grade.survived) == (29, 2)
