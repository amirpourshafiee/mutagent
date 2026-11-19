"""One-call diagnostic: build the draft prompt for a module, send it, and show what the API
received (token counts) and what came back. Costs a few cents.

    python -m mutagent.probe vioreg_gate
"""
from __future__ import annotations

import sys

from mutagent.agent import SYSTEM, draft_prompt
from mutagent.bench import discover
from mutagent.env import describe_environment
from mutagent.llm import AnthropicLLM


def main(argv: list[str] | None = None) -> int:
    name = (argv or sys.argv[1:] or ["ratelimiter"])[0]
    info = discover()[name]
    module_src = info["module"].read_text()
    spec = (info["dir"] / "SPEC.md").read_text()
    prompt = draft_prompt(module_src, spec, describe_environment(info["module"]))
    print(f"prompt chars: {len(prompt)}  (spec {len(spec)}, module {len(module_src)})")
    llm = AnthropicLLM()
    reply = llm.complete(SYSTEM, prompt)
    print(f"API reported input_tokens={llm.input_tokens} output_tokens={llm.output_tokens} "
          f"cost=${llm.cost_usd:.4f}")
    print("--- reply (first 1500 chars) ---")
    print(reply[:1500])
    print("--- reply tail ---")
    print(reply[-400:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
