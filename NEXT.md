Done: S1-S4; S5b runner + baselines; pilots; benchmark of 8 modules x B2/B3/B4 x 3 repeats
(dev set: ratelimiter, retrying, schedule, xmltodict; held-out: vioreg_gate/score/variance/sensitivity).
All numbers and caveats: bench/results/README.md. Total API spend for the final runs about $29.

Next (in order):
1. Top-level README: what mutagent is, the results table (held-out first), honest caveats
   (n=3, one model, one run family, B4 loses to B3 on vioreg_variance, xmltodict margin is small).
2. Diagnose why B4 trails B3 on vioreg_variance (stalled run, survivor feedback quality).
3. Optional: replace the excluded inflection module with a fresh one, Docker support for package
   mode, pin Python 3.12 and mutmut 3.8.1, MCP server / GitHub Action per the plan.
Python 3.12 required for vioreg. Install bench deps with: pip install -e ".[llm,dev,bench]"
