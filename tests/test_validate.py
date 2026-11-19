from pathlib import Path

import pytest

from mutagent.validate import parse_junit, validate_flaky

RL = Path(__file__).parent.parent / "bench" / "modules" / "ratelimiter"


def test_parse_junit():
    xml = ('<testsuite><testcase classname="t" name="a"/>'
           '<testcase classname="t" name="b"><failure/></testcase></testsuite>')
    assert parse_junit(xml) == {"t::a": True, "t::b": False}


@pytest.mark.slow
def test_human_tests_are_not_flaky():
    assert validate_flaky(RL / "src" / "ratelimiter.py", RL / "human_tests", runs=4) == 0.0


@pytest.mark.slow
def test_order_dependent_tests_are_detected(tmp_path):
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_order.py").write_text(
        "state = []\n\ndef test_a():\n    state.append(1)\n\n"
        "def test_b():\n    assert state == [] or state == [1]\n\n"
        "def test_c():\n    assert state == [1]\n"
    )
    assert validate_flaky(RL / "src" / "ratelimiter.py", t, runs=8) > 0.0
