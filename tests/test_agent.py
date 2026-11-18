
from mutagent.agent import extract_bugs, extract_python, run_agent
from mutagent.grading import Grade
from mutagent.runner import GradeReport, TestsFailing


class FakeLLM:
    def __init__(self, replies):
        self.replies, self.prompts, self.cost_usd = list(replies), [], 0.0

    def complete(self, system, user):
        self.prompts.append(user)
        self.cost_usd += 0.01
        return self.replies.pop(0)


def block(code):
    return f"```python\n{code}\n```"


def report(killed, survived):
    return GradeReport(Grade(killed, survived), 90.0, 3, (7,), ())


def make_ws(tmp_path):
    mod = tmp_path / "m.py"
    mod.write_text("def f():\n    return 1\n")
    spec = tmp_path / "SPEC.md"
    spec.write_text("f returns 1")
    ws = tmp_path / "ws"
    (ws / "tests").mkdir(parents=True)
    return mod, spec, ws


def scripted_grader(results):
    results = list(results)

    def grader(module, tests_dir):
        r = results.pop(0)
        if isinstance(r, str):
            raise TestsFailing(r)
        return r

    return grader


def test_extractors():
    assert extract_python("x\n" + block("a = 1")) == "a = 1\n"
    assert extract_python("no code") is None
    assert extract_bugs("POSSIBLE_BUG: off by one\nok") == ["off by one"]


def test_reaches_target_and_feeds_survivors_back(tmp_path):
    mod, spec, ws = make_ws(tmp_path)
    llm = FakeLLM([block("def test_a(): pass"), block("def test_b(): pass")])
    g = scripted_grader([report(5, 5), report(9, 1)])
    res = run_agent(mod, spec, ws, llm, target=0.9, grader=g)
    assert res.status == "target_reached" and res.history == [0.5, 0.9]
    assert "Mutation score 50%" in llm.prompts[1]
    assert "def test_b" in (ws / "tests" / "test_generated.py").read_text()


def test_repairs_failing_draft(tmp_path):
    mod, spec, ws = make_ws(tmp_path)
    llm = FakeLLM([block("def test_a(): assert 0"), block("def test_a(): pass")])
    res = run_agent(mod, spec, ws, llm, target=0.5,
                    grader=scripted_grader(["AssertionError boom", report(6, 4)]))
    assert res.status == "target_reached"
    assert "AssertionError boom" in llm.prompts[1]


def test_never_graded_when_still_failing(tmp_path):
    mod, spec, ws = make_ws(tmp_path)
    llm = FakeLLM([block("def test_a(): assert 0")] * 3)
    res = run_agent(mod, spec, ws, llm, grader=scripted_grader(["f"] * 3))
    assert res.status == "failing" and res.best is None


def test_cheating_candidate_is_rejected_without_grading(tmp_path):
    mod, spec, ws = make_ws(tmp_path)
    cheat = block("import mutmut\ndef test_a(): pass")
    llm = FakeLLM([cheat, block("def test_a(): pass")])
    res = run_agent(mod, spec, ws, llm, target=0.5, grader=scripted_grader([report(6, 4)]))
    assert res.status == "target_reached" and "anti-cheat" in llm.prompts[1]


def test_worse_candidate_is_discarded_and_stall_stops(tmp_path):
    mod, spec, ws = make_ws(tmp_path)
    llm = FakeLLM([block("def test_1(): pass")] + [block("def test_2(): pass")] * 3)
    g = scripted_grader([report(5, 5), report(4, 6), report(5, 5)])
    res = run_agent(mod, spec, ws, llm, target=0.99, stall_after=2, repairs=0, grader=g)
    assert res.status == "stalled" and res.history == [0.5]
    assert "test_1" in (ws / "tests" / "test_generated.py").read_text()


def test_budget_stops_the_loop(tmp_path):
    mod, spec, ws = make_ws(tmp_path)
    llm = FakeLLM([block("def test_a(): pass")])
    res = run_agent(mod, spec, ws, llm, target=0.99, budget_usd=0.005,
                    grader=scripted_grader([report(5, 5)]))
    assert res.status == "budget"


def test_coverage_feedback_never_shows_mutants_and_optimizes_coverage(tmp_path):
    mod, spec, ws = make_ws(tmp_path)
    from mutagent.runner import Survivor

    def rep(cov, killed):
        return GradeReport(Grade(killed, 10 - killed), cov, 3, (7,), (Survivor("m_1", "SECRET_DIFF"),))

    llm = FakeLLM([block("def test_a(): pass"), block("def test_b(): pass")])
    res = run_agent(mod, spec, ws, llm, target=1.0, feedback="coverage",
                    grader=scripted_grader([rep(80.0, 5), rep(100.0, 4)]))
    assert res.status == "target_reached" and res.history == [0.8, 1.0]
    assert "SECRET_DIFF" not in llm.prompts[1] and "Mutation score" not in llm.prompts[1]
    assert res.best.grade.killed == 4  # still graded by mutation, even though it was worse


def test_zero_rounds_is_single_shot(tmp_path):
    mod, spec, ws = make_ws(tmp_path)
    llm = FakeLLM([block("def test_a(): pass")])
    res = run_agent(mod, spec, ws, llm, target=1.0, max_rounds=0,
                    grader=scripted_grader([report(5, 5)]))
    assert res.rounds == 0 and len(llm.prompts) == 1 and res.status == "max_rounds"
