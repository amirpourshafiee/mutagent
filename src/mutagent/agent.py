"""The test-generation loop: draft, repair, then improve using coverage and surviving mutants.

Rules baked in: a candidate is only kept if it passes, is not flagged by the anti-cheat
guard, and strictly raises the mutation score. Tests are written only under tests/.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mutagent.guards import find_cheats
from mutagent.llm import LLM
from mutagent.runner import GradeReport, TestsFailing, run_grade
from mutagent.tools import write_tests

TEST_FILE = "test_generated.py"

SYSTEM = (
    "You write pytest tests for a Python module. Return the COMPLETE test file in one "
    "```python block. Import the module by its file name. Use only the standard library "
    "and pytest. Do not read files, use open/exec/eval, or import inspect or mutmut. "
    "Test behavior stated in the spec, with exact expected values, and no sleeping. "
    "Do not assert exception message text; assert only the exception type unless the spec "
    "gives the message. "
    "If the code seems to contradict the spec, do not assert the buggy behavior; add a line "
    "'POSSIBLE_BUG: <explanation>' outside the code block."
)

Grader = Callable[[Path, Path], GradeReport]


@dataclass
class AgentResult:
    status: str  # "target_reached" | "stalled" | "max_rounds" | "budget" | "failing"
    best: GradeReport | None
    best_source: str | None
    rounds: int = 0
    cost_usd: float = 0.0
    notes: list[str] = field(default_factory=list)
    history: list[float] = field(default_factory=list)  # mutation score after each kept round


def extract_python(text: str) -> str | None:
    m = re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.DOTALL)
    return m[-1].strip() + "\n" if m else None


def extract_bugs(text: str) -> list[str]:
    return re.findall(r"^POSSIBLE_BUG:\s*(.+)$", text, flags=re.MULTILINE)


def draft_prompt(module_src: str, spec: str) -> str:
    return f"SPEC:\n{spec}\n\nMODULE (import it by its file name):\n```python\n{module_src}\n```\n\nWrite the tests."


def improve_prompt(module_src: str, spec: str, current: str, rep: GradeReport,
                   use_survivors: bool = True) -> str:
    parts = [
        f"SPEC:\n{spec}", f"MODULE:\n```python\n{module_src}\n```",
        f"CURRENT TESTS (all pass):\n```python\n{current}\n```",
        f"Line coverage {rep.line_coverage:.0f}%."
        + (f" Mutation score {rep.grade.mutation_score:.0%}." if use_survivors else ""),
    ]
    if rep.missing_lines:
        parts.append(f"Lines never executed: {list(rep.missing_lines)}")
    if rep.survivors and use_survivors:
        diffs = "\n\n".join(f"```diff\n{s.diff}\n```" for s in rep.survivors)
        parts.append(
            "These mutations of the module were NOT caught by any test. Add or strengthen "
            f"tests so each is caught, while keeping spec-correct behavior:\n{diffs}"
        )
    parts.append("Return the complete improved test file.")
    return "\n\n".join(parts)


def repair_prompt(candidate: str, output: str) -> str:
    return (f"These tests fail on the original module:\n```python\n{candidate}\n```\n"
            f"pytest output:\n{output[-3000:]}\n\n"
            "Fix the tests (the module is correct unless the spec says otherwise). "
            "Return the complete file.")


def _try(workspace: Path, source: str, module: Path, grader: Grader) -> GradeReport | str:
    """Write the candidate and grade it. Returns a report, or the failure text."""
    problems = find_cheats(source)
    if problems:
        return "anti-cheat guard: " + "; ".join(problems)
    write_tests(workspace, TEST_FILE, source)
    try:
        return grader(module, workspace / "tests")
    except TestsFailing as e:
        return e.output


def run_agent(module: Path, spec_file: Path, workspace: Path, llm: LLM, *,
              target: float = 0.9, max_rounds: int = 6, stall_after: int = 2,
              repairs: int = 2, budget_usd: float = 2.0,
              grader: Grader = run_grade, feedback: str = "mutation") -> AgentResult:
    """feedback="mutation": the agent sees surviving mutants and optimizes mutation score.
    feedback="coverage": baseline B3, sees only uncovered lines and optimizes line coverage
    (it never sees mutants); the final suite is still graded by mutation score."""
    if feedback not in ("mutation", "coverage"):
        raise ValueError(feedback)
    use_mut = feedback == "mutation"

    def score(r: GradeReport) -> float:
        return r.grade.mutation_score if use_mut else r.line_coverage / 100

    module_src, spec = module.read_text(), spec_file.read_text()
    res = AgentResult("failing", None, None)

    def ask(prompt: str) -> str | None:
        reply = llm.complete(SYSTEM, prompt)
        res.notes += extract_bugs(reply)
        res.cost_usd = llm.cost_usd
        return extract_python(reply)

    def attempt(prompt: str) -> tuple[str, GradeReport] | None:
        """Ask, then give the model `repairs` chances to fix failing tests."""
        for _ in range(repairs + 1):
            src = ask(prompt)
            if src is None:
                prompt = "Your reply had no ```python block. Return the complete test file."
                continue
            out = _try(workspace, src, module, grader)
            if isinstance(out, GradeReport):
                return src, out
            prompt = repair_prompt(src, out)
            if llm.cost_usd >= budget_usd:
                break
        return None

    first = attempt(draft_prompt(module_src, spec))
    if first is None:
        return res
    res.best_source, res.best = first
    res.history.append(score(res.best))
    stalled = 0
    for res.rounds in range(1, max_rounds + 1):
        if score(res.best) >= target:
            res.status = "target_reached"
            break
        if llm.cost_usd >= budget_usd:
            res.status = "budget"
            break
        if stalled >= stall_after:
            res.status = "stalled"
            break
        cand = attempt(improve_prompt(module_src, spec, res.best_source, res.best, use_mut))
        if cand and score(cand[1]) > score(res.best):
            res.best_source, res.best = cand
            res.history.append(score(res.best))
            stalled = 0
        else:
            stalled += 1
    else:
        res.status = (
            "target_reached" if score(res.best) >= target else "max_rounds"
        )
    # leave the best passing suite on disk, not the last (possibly rejected) candidate
    write_tests(workspace, TEST_FILE, res.best_source)
    return res
