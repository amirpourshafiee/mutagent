"""Run the agent on one module:  python -m mutagent.agent_cli MODULE SPEC OUT_DIR"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mutagent.agent import run_agent
from mutagent.llm import AnthropicLLM


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mutagent-agent")
    p.add_argument("module", type=Path)
    p.add_argument("spec", type=Path)
    p.add_argument("out", type=Path, help="workspace; tests land in OUT/tests/test_generated.py")
    p.add_argument("--model", default="claude-sonnet-5-5")
    p.add_argument("--target", type=float, default=0.9)
    p.add_argument("--budget", type=float, default=1.0, help="USD cap for this run")
    a = p.parse_args(argv)
    (a.out / "tests").mkdir(parents=True, exist_ok=True)
    res = run_agent(a.module, a.spec, a.out, AnthropicLLM(model=a.model),
                    target=a.target, budget_usd=a.budget)
    print(json.dumps({"status": res.status, "rounds": res.rounds, "history": res.history,
                      "cost_usd": round(res.cost_usd, 4), "notes": res.notes,
                      "coverage": res.best.line_coverage if res.best else None}, indent=2))
    return 0 if res.best else 2


if __name__ == "__main__":
    raise SystemExit(main())
