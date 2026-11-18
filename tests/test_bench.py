import json
from pathlib import Path

from mutagent.bench import discover, make_key, run_one, summarize
from mutagent.grading import Grade
from mutagent.runner import GradeReport
from tests.test_agent import FakeLLM, block, scripted_grader

MODULES = Path(__file__).parent.parent / "bench" / "modules"


def rep(k, s):
    return GradeReport(Grade(k, s), 90.0, 3, (), ())


def test_discover_finds_modules_with_required_files():
    mods = discover(MODULES)
    assert {"ratelimiter", "inflection", "retrying", "schedule", "xmltodict"} <= set(mods)
    for info in mods.values():
        assert (info["dir"] / "SPEC.md").is_file() and (info["dir"] / "human_tests").is_dir()
        assert info["license"] in ("MIT", "Apache-2.0")


def test_b0_uses_human_tests_without_llm():
    info = discover(MODULES)["ratelimiter"]
    row = run_one(info, "B0", None, grader=scripted_grader([rep(29, 2)]))
    assert row["killed"] == 29 and row["cost_usd"] == 0.0


def test_b2_is_single_shot_and_b4_iterates():
    info = discover(MODULES)["ratelimiter"]
    llm = FakeLLM([block("def test_a(): pass")])
    b2 = run_one(info, "B2", llm, grader=scripted_grader([rep(5, 5)]))
    assert b2["rounds"] == 0 and len(llm.prompts) == 1
    llm = FakeLLM([block("def test_a(): pass"), block("def test_b(): pass")])
    b4 = run_one(info, "B4", llm, grader=scripted_grader([rep(5, 5), rep(10, 0)]))
    assert b4["score"] == 1.0 and b4["status"] == "target_reached"


def test_keys_and_summary():
    assert make_key("m", "B0", 0, "x") == "m|B0|0|-"
    res = {"m|B4|0|x": {"score": 0.5}, "m|B4|1|x": {"score": 1.0}, "m|B0|0|-": {"score": 0.8},
           "m|B2|0|x": {"status": "failing"}}
    assert summarize(res) == {"m": {"B4": 0.75, "B0": 0.8}}
    json.dumps(res)
