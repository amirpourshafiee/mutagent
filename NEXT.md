Done: S1-S4; S5b runner+baselines; pilots 1-2 (bench/results/README.md); package-mode modules: 4 vioreg modules vendored with B0 measured.
Benchmark set (8): ratelimiter, retrying, schedule, xmltodict (dev/pilot set) + vioreg_gate/score/variance/sensitivity (held out: NOT used for tuning).
Config frozen for the main run: target 1.0, max_rounds 6, 5 survivors, repairs 2, budget $1/run, Sonnet 5.5.
Next: main run on the 4 vioreg modules x B2/B3/B4 x 3 repeats (est. $10-20, check with one repeat first):
  python -m mutagent.bench --out bench/results/vioreg_run1.json --modules vioreg_gate vioreg_score vioreg_variance vioreg_sensitivity --baselines B2 B3 B4 --repeats 1 --max-usd 12
Python 3.12 required for vioreg (3.12-only f-string syntax). Docker sandbox: single-file only for now.
