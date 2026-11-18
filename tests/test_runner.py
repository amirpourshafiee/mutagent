from pathlib import Path

import pytest

from mutagent.runner import (
    TestsFailing,
    build_workspace,
    pick_survivors,
    protect_raise_lines,
    run_grade,
)

RL = Path(__file__).parent.parent / "bench" / "modules" / "ratelimiter"


def test_build_workspace_layout(tmp_path):
    ws = tmp_path / "ws"
    build_workspace(ws, RL / "src" / "ratelimiter.py", RL / "human_tests")
    assert (ws / "src" / "ratelimiter.py").is_file()
    assert (ws / "tests" / "test_ratelimiter.py").is_file()
    cfg = (ws / "pyproject.toml").read_text()
    assert "paths_to_mutate" in cfg and "no:randomly" in cfg


def test_pick_survivors_round_robin():
    names = ["a__mutmut_1", "a__mutmut_2", "a__mutmut_3", "b__mutmut_1", "c__mutmut_1"]
    assert pick_survivors(names, 4) == ["a__mutmut_1", "b__mutmut_1", "c__mutmut_1", "a__mutmut_2"]
    assert pick_survivors([], 5) == []


def test_protect_raise_lines_marks_every_line_of_a_raise():
    src = "def f(x):\n    if x:\n        raise ValueError(\n            'bad'\n        )\n    return 1\n"
    out = protect_raise_lines(src)
    assert out.count("pragma: no mutate") == 3
    assert "return 1  #" not in out
    assert protect_raise_lines(out) == out  # idempotent


@pytest.mark.slow
def test_golden_ratelimiter_human_tests_spec_scoring():
    rep = run_grade(RL / "src" / "ratelimiter.py", RL / "human_tests")
    assert (rep.grade.killed, rep.grade.survived) == (29, 2)


@pytest.mark.slow
def test_golden_ratelimiter_human_tests_with_message_mutants():
    rep = run_grade(RL / "src" / "ratelimiter.py", RL / "human_tests", score_messages=True)
    assert (rep.grade.killed, rep.grade.survived) == (29, 14)
    assert rep.grade.mutation_score == pytest.approx(29 / 43)
    assert rep.tests_passed > 0 and 0 < rep.line_coverage <= 100
    assert len(rep.survivors) == 5 and "@@" in rep.survivors[0].diff


@pytest.mark.slow
def test_failing_tests_are_reported_not_graded(tmp_path):
    bad = tmp_path / "tests"
    bad.mkdir()
    (bad / "test_bad.py").write_text("def test_x():\n    assert False\n")
    with pytest.raises(TestsFailing):
        run_grade(RL / "src" / "ratelimiter.py", bad)


def test_passed_count_ignores_subtest_summary(tmp_path):
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_sub.py").write_text(
        "import unittest\n\nclass T(unittest.TestCase):\n    def test_a(self):\n"
        "        for i in range(3):\n            with self.subTest(i=i):\n                self.assertTrue(i >= 0)\n"
    )
    rep = run_grade(RL / "src" / "ratelimiter.py", t)
    assert rep.tests_passed == 1
