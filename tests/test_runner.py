from pathlib import Path

import pytest

from mutagent.runner import TestsFailing, build_workspace, run_grade

RL = Path(__file__).parent.parent / "bench" / "modules" / "ratelimiter"


def test_build_workspace_layout(tmp_path):
    ws = tmp_path / "ws"
    build_workspace(ws, RL / "src" / "ratelimiter.py", RL / "human_tests")
    assert (ws / "src" / "ratelimiter.py").is_file()
    assert (ws / "tests" / "test_ratelimiter.py").is_file()
    cfg = (ws / "pyproject.toml").read_text()
    assert "paths_to_mutate" in cfg and "no:randomly" in cfg


@pytest.mark.slow
def test_golden_ratelimiter_human_tests():
    rep = run_grade(RL / "src" / "ratelimiter.py", RL / "human_tests")
    assert (rep.grade.killed, rep.grade.survived) == (29, 14)
    assert rep.grade.mutation_score == pytest.approx(29 / 43)
    assert rep.tests_passed > 0 and 0 < rep.line_coverage <= 100


@pytest.mark.slow
def test_failing_tests_are_reported_not_graded(tmp_path):
    bad = tmp_path / "tests"
    bad.mkdir()
    (bad / "test_bad.py").write_text("def test_x():\n    assert False\n")
    with pytest.raises(TestsFailing):
        run_grade(RL / "src" / "ratelimiter.py", bad)
