# mutagent

An LLM agent that writes pytest tests for a Python module from its code and a plain-English spec,
then improves them using feedback. Quality is judged by mutation testing (mutmut), not line
coverage: a suite only counts if it catches deliberately broken versions of the code.

## Results

Mutation score = killed / (killed + survived + no_tests); timeouts are excluded. Mean of 3 repeats,
Claude Sonnet 5.5. B0 is the human-written tests; B2 a single shot; B3 an agent that sees only
uncovered lines (optimizes coverage); B4 the full agent that sees surviving mutants.

**Held-out** (four modules of a separate project, `vioreg`; not used to tune the harness):

| module | B0 human | B2 single shot | B3 coverage agent | B4 mutation agent |
|---|---|---|---|---|
| vioreg_gate | 81.0 | 83.7 | 85.6 | **97.3** |
| vioreg_score | 66.3 | 55.8 | 68.4 | **78.3** |
| vioreg_variance | 36.5 | 40.2 | **70.4** | 63.9 |
| vioreg_sensitivity | 42.3 | 87.1 | 87.3 | **93.7** |

**Dev set** (the harness was tuned on these, so weaker evidence):

| module | B0 human | B2 | B3 | B4 |
|---|---|---|---|---|
| ratelimiter | 93.5 | 96.8 | 96.8 | **100.0** |
| retrying | 66.0 | 73.5 | 82.4 | **98.5** |
| schedule | 76.5 | 63.3 | 81.0 | **96.5** |
| xmltodict | 87.4 | 65.8 | 84.7 | **88.7** |

A B4 run costs $0.04 to $0.90 in API fees, roughly 2 to 5 times a single shot.

**What the numbers support:** the mutation-feedback agent beat the human tests on all eight modules,
and beat coverage feedback on seven of eight.

**What they do not support:**
- Three repeats, one model and eight modules is a small study. Standard deviations are in
  `bench/results/README.md`; these are consistent directions, not significance tests.
- B3 beat B4 on `vioreg_variance` (70.4 vs 63.9, ranges do not overlap). Diagnosed: a plotting
  function needs matplotlib, which the benchmark environment lacks. B4 skips those tests honestly,
  leaving 29% of mutants unreachable; B3 reaches them with mocks. See `bench/results/README.md`.
- On `xmltodict` the agent barely beats a mature human suite (88.7 vs 87.4).
- A single shot (B2) is often worse than the human tests (`schedule`, `xmltodict`, `vioreg_score`).
  The gain comes from the feedback loop, not from the model alone.
- `ratelimiter` is saturated and separates nothing. `inflection` was dropped because its
  import-time code cannot be killed by mutmut (see `bench/excluded/`).
- Setup choices changed after the first pilot and are disclosed in `bench/results/README.md`:
  timeouts are excluded from the score, exception-message text is not scored, and several harness
  bugs (blind repairs, truncated replies) were fixed. Final numbers use one frozen config:
  target 1.0, up to 6 improvement rounds, 5 survivors shown, 2 repairs, $1 budget per run.

## How it works

1. **Draft**: the model gets the module, the spec and an environment note (import line, installed
   packages, sibling-module signatures) and returns a full pytest file.
2. **Repair**: if tests fail, it sees the failure output and fixes them (up to 2 times).
3. **Improve**: it is shown surviving mutants (B4) or uncovered lines (B3) and returns only NEW
   tests, which are appended. A candidate is kept only if it passes, clears an anti-cheat guard
   (no reading files, exec/eval, or asserting exception text) and strictly raises the score.
4. **Stop** at the target, after 2 stalled rounds, at the round limit, or at the USD budget.

If the code contradicts the spec, the agent reports `POSSIBLE_BUG:` instead of asserting the bug.

## Run it

    python3.12 -m venv .venv && . .venv/bin/activate
    pip install -e ".[llm,dev,bench]"
    export ANTHROPIC_API_KEY=...          # then:
    python -m mutagent.agent_cli path/to/module.py path/to/SPEC.md out_dir --budget 1.0
    python -m mutagent.bench --out bench/results/my_run.json --modules ratelimiter \
        --baselines B2 B3 B4 --repeats 1 --max-usd 5
    pytest -m "not slow"                  # harness tests, no API calls

`python -m mutagent.probe MODULE` sends one draft prompt and prints what came back (a few cents).

## Layout

- `src/mutagent/`: `runner.py` (mutmut grading), `agent.py` (loop), `env.py`, `bench.py`, `llm.py`.
- `bench/modules/`: the eight benchmark modules (vendored ones keep their licenses and own tests).
- `bench/results/`: raw JSON per run plus a README that logs every finding, pilot and fix.
- `docs/PLAN.md`: scope and build plan.
