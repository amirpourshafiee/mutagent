import pytest

from mutagent.grading import Grade, flaky_rate
from mutagent.guards import find_cheats
from mutagent.tools import write_tests


def test_mutation_score_ignores_timeouts():
    assert Grade(killed=8, survived=2, timeout=5).mutation_score == pytest.approx(0.8)


def test_mutation_score_with_nothing_scored_raises():
    with pytest.raises(ValueError):
        _ = Grade(killed=0, survived=0).mutation_score


@pytest.mark.parametrize("src", [
    "import mutmut",
    "from inspect import getsource",
    "def test_x():\n    open('src/mod.py').read()",
])
def test_cheating_tests_are_rejected(src):
    assert find_cheats(src)


def test_honest_test_passes_the_guard():
    src = "from mod import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    assert find_cheats(src) == []


def test_flaky_rate_counts_tests_that_disagree_across_runs():
    runs = [{"t1": True, "t2": True}, {"t1": True, "t2": False}, {"t1": True, "t2": True}]
    assert flaky_rate(runs) == 0.5


def test_write_tests_refuses_paths_outside_tests_dir(tmp_path):
    with pytest.raises(PermissionError):
        write_tests(tmp_path, "../src/mod.py", "x = 1")


def test_write_tests_writes_inside_tests_dir(tmp_path):
    path = write_tests(tmp_path, "test_mod_gen.py", "def test_ok():\n    assert True\n")
    assert path.parent == (tmp_path / "tests").resolve()


def test_grade_from_real_mutmut_cicd_stats():
    from mutagent.grading import grade_from_cicd_stats

    # copied from a real `mutmut export-cicd-stats` run on bench/modules/ratelimiter
    stats = {"killed": 29, "survived": 14, "total": 43, "no_tests": 0, "skipped": 0,
             "suspicious": 0, "timeout": 0, "check_was_interrupted_by_user": 0, "segfault": 0}
    grade = grade_from_cicd_stats(stats)
    assert (grade.killed, grade.survived) == (29, 14)
    assert grade.mutation_score == pytest.approx(29 / 43)
