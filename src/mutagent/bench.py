"""Benchmark runner: every module x baseline x repeat, results appended to one JSON file.

Baselines (all graded by the same grader, spec scoring):
  B0  the project's own human tests (no LLM, deterministic, run once)
  B2  single shot: one draft plus repairs, no feedback rounds
  B3  coverage-feedback agent: sees uncovered lines only, optimizes line coverage
  B4  full mutagent: sees surviving mutants, optimizes mutation score
Runs are resumable: a (module, baseline, repeat) key already in the file is skipped.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Callable
from pathlib import Path

from mutagent.agent import run_agent
from mutagent.llm import LLM, AnthropicLLM
from mutagent.runner import TestsFailing, run_grade

BASELINES = ("B0", "B2", "B3", "B4")
MODULES_DIR = Path(__file__).resolve().parents[2] / "bench" / "modules"


def discover(modules_dir: Path = MODULES_DIR) -> dict[str, dict]:
    found = {}
    for meta in sorted(modules_dir.glob("*/meta.yaml")):
        d = meta.parent
        info = dict(
            line.split(": ", 1) for line in meta.read_text().splitlines() if ": " in line
        )
        info["dir"] = d
        info["module"] = next((d / "src").glob("*.py"))
        found[d.name] = info
    return found


def make_key(module: str, baseline: str, repeat: int, model: str) -> str:
    return f"{module}|{baseline}|{repeat}|{model if baseline != 'B0' else '-'}"


def run_one(info: dict, baseline: str, llm: LLM | None, grader: Callable = run_grade) -> dict:
    module, spec, human = info["module"], info["dir"] / "SPEC.md", info["dir"] / "human_tests"
    if baseline == "B0":
        rep = grader(module, human)
        return _row(rep, status="n/a", rounds=0, cost=0.0, notes=[])
    with tempfile.TemporaryDirectory(prefix="mutagent-bench-") as tmp:
        ws = Path(tmp)
        (ws / "tests").mkdir()
        kwargs = {"target": 1.0, "budget_usd": 1.0, "grader": grader}
        if baseline == "B2":
            res = run_agent(module, spec, ws, llm, max_rounds=0, **kwargs)
        elif baseline == "B3":
            res = run_agent(module, spec, ws, llm, feedback="coverage", **kwargs)
        elif baseline == "B4":
            res = run_agent(module, spec, ws, llm, **kwargs)
        else:
            raise ValueError(baseline)
        if res.best is None:
            return {"status": "failing", "cost_usd": round(res.cost_usd, 4), "notes": res.notes}
        return _row(res.best, res.status, res.rounds, res.cost_usd, res.notes,
                    source=res.best_source)


def _row(rep, status, rounds, cost, notes, source=None) -> dict:
    row = {
        "killed": rep.grade.killed, "survived": rep.grade.survived,
        "timeout": rep.grade.timeout, "no_tests": rep.grade.no_tests,
        "score": round(rep.grade.mutation_score, 4),
        "coverage": round(rep.line_coverage, 1), "tests_passed": rep.tests_passed,
        "status": status, "rounds": rounds, "cost_usd": round(cost, 4), "notes": notes,
    }
    if source is not None:
        row["suite"] = source
    return row


def summarize(results: dict) -> dict:
    """Median-free summary: mean score per (module, baseline) across repeats."""
    table: dict[str, dict[str, list[float]]] = {}
    for key, row in results.items():
        module, baseline, _, _ = key.split("|")
        if "score" in row:
            table.setdefault(module, {}).setdefault(baseline, []).append(row["score"])
    return {m: {b: round(sum(v) / len(v), 3) for b, v in bs.items()} for m, bs in table.items()}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mutagent-bench")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--modules", nargs="*", help="default: all")
    p.add_argument("--baselines", nargs="*", default=list(BASELINES))
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--model", default="claude-sonnet-5-5")
    p.add_argument("--max-usd", type=float, default=20.0, help="stop starting runs past this")
    a = p.parse_args(argv)

    mods = discover()
    names = a.modules or list(mods)
    results = json.loads(a.out.read_text()) if a.out.exists() else {}
    spent = sum(r.get("cost_usd", 0.0) for r in results.values())
    for name in names:
        for b in a.baselines:
            for rep in range(1 if b == "B0" else a.repeats):
                key = make_key(name, b, rep, a.model)
                if key in results:
                    continue
                if spent >= a.max_usd:
                    print(f"budget reached (${spent:.2f}); stopping")
                    a.out.write_text(json.dumps(results, indent=1))
                    return 1
                llm = None if b == "B0" else AnthropicLLM(model=a.model)
                try:
                    row = run_one(mods[name], b, llm)
                except TestsFailing as e:
                    row = {"status": "tests_failing_on_original", "notes": [e.output[-500:]]}
                results[key] = row
                spent += row.get("cost_usd", 0.0)
                a.out.write_text(json.dumps(results, indent=1))
                print(key, row.get("score"), row.get("status"), f"${spent:.2f} total")
    print(json.dumps(summarize(results), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
