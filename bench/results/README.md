# Results log

## ratelimiter, agent run 1 (2026-11-18, Sonnet 5.5, ~$0.11)

| Suite | Scoring | Killed / survived | Score |
|---|---|---|---|
| Human tests | incl. exception-message mutants | 29 / 14 | 67% |
| Agent run 1 | incl. exception-message mutants | 43 / 0 | 100% |
| Human tests | spec scoring (messages not mutated) | 29 / 2 | 94% |
| Agent run 1 | spec scoring (messages not mutated) | 31 / 0 | 100% |

Finding: 12 of the 14 human-test survivors were exception-message mutants. The spec never
states message text, yet 7 of the agent's assertions pin it (`match=r"^...$"`). That inflated
the first score. The grader now excludes `raise` lines from mutation by default
(`score_messages=False`), and the agent prompt says not to assert message text.
Agent run 1 flaky rate over 10 randomized reruns: 0.0.
Honest read: on this module the agent beats the human tests by about 6 points, not 33.

## Pilot 1 (2026-11-18, one repeat, agent v1) and what it exposed

Scores with the definition in force at the time (unreached mutants excluded):
B0 / B2 / B3 / B4 -- ratelimiter 94 / 97 / 97 / 100, retrying 66 / 63 / 84 / 64,
inflection 56 / 56 / 56 / 57, schedule 77 / 74 / 68 / error, xmltodict 87 / 67 / 69 / failing.
The agent did NOT beat the human tests except on ratelimiter. Cause analysis, all bugs in my harness:
1. The repair prompt did not include the module or spec, so repairs were blind (xmltodict B4: the
   model said "no module was provided"; three failed repairs, no suite).
2. Improvement rounds asked for the whole file back, so the model could drop earlier tests; the strict
   accept rule then rejected most rounds ("stalled").
3. Mutants no test reaches were excluded from the score, so covering more code could LOWER it
   (retrying B2 -> B4). The score is now killed / (killed + survived + no_tests), timeouts excluded.
   This definition was changed after seeing pilot data, because of that artifact; B0 recomputed:
   inflection 56.2, retrying 66.0, schedule 76.5, xmltodict 87.4, ratelimiter 93.5.
4. A candidate with zero scored mutants crashed the run (fixed in the previous commit).
Fixes: repair prompts carry module + spec; improvement rounds return only NEW tests that are
appended (name collisions renamed); the new score definition. Pilot 2 reruns everything with them.
File: pilot1_old_agent.json (raw rows, including the generated suites).

## Pilot 2 (2026-11-18, one repeat, agent v2, new score definition)

| Module | B0 human | B2 single shot | B3 coverage agent | B4 full agent |
|---|---|---|---|---|
| ratelimiter | 93.5 | 100 | 96.8 | 100 |
| retrying | 66.0 | 61.0 | 83.5 | 95.7 |
| schedule | 76.5 | failing (no valid suite) | 78.1 | 95.9 |
| xmltodict | 87.4 | 65.4 | 84.0 | (invalid, see below) |
| inflection | 56.2 | 56.4 | 56.4 | 56.9 (module excluded, see bench/excluded) |

Reading, with one run per cell so no significance claims: mutation feedback (B4) beat coverage
feedback (B3) by 12 and 18 points on retrying and schedule; on xmltodict B3 did not beat the human
tests. The agent's own notes on retrying call the remaining survivors equivalent mutants.

Two invalid results found: the xmltodict B4 run produced a suite with zero passing tests (module
skipped), which the grader accepted and scored 0. run_grade now raises TestsFailing when no test
passes. That row was removed from pilot2.json and needs a rerun. inflection was excluded (import-time
mutants cannot be killed). Cost of pilot 2: about $4.

## B0 for the vioreg modules (own project, package mode), 2026-11-18
Python 3.12, human tests = the project's own tests (written with AI assistance).
| Module | killed / survived / unreached | score | line coverage |
|---|---|---|---|
| vioreg_gate | 600 / 130 / 11 | 81.0% | 93.3% |
| vioreg_score | 434 / 209 / 12 | 66.3% | 95.2% |
| vioreg_sensitivity | 479 / 104 / 550 | 42.3% | 61.3% |
| vioreg_variance | 296 / 66 / 450 | 36.5% | 52.6% |
Much of the headroom on variance and sensitivity is unreached code (CLI entry points). The spec for
each is the module docstring plus its docs page, so the CLI behavior is described to the agent.
Not yet supported: the Docker sandbox mounts one file, so package mode runs on the host only.

## First vioreg attempt (2026-11-18): 12 of 12 runs failed, $2.71 wasted
Cause: the prompt said "import the module by its file name" and "use only the standard library and
pytest". vioreg modules need `from vioreg import score` and numpy, so every generated suite failed to
import. Fix: mutagent.env.describe_environment now tells the model the real import line, the
installed third-party packages the module uses, and signature stubs of the sibling package modules;
the prompt carries it in an ENVIRONMENT section. This changed the prompt after looking at the held-out
modules, but only for interface information (no run produced a score, so no result guided the change).
Verified offline before spending anything: a stand-in model returning the project's own gate tests
goes through the whole package-mode pipeline and is graded (501 killed / 192 survived).
Raw failed rows kept in vioreg_run0_all_failed.json.

## Held-out vioreg, run 2 (1 repeat, frozen config, $5.82)

Earlier vioreg attempts (run0, run0b, run1) failed because of harness bugs, not model failures:
missing numpy in the venv, a prompt that said "stdlib only", and a reply truncated at 8000 output
tokens whose retry carried no context. Fixed before run 2 (max_tokens 16000, context-keeping retry).

Mutation score (killed / (killed + survived + no_tests)), n=1 per cell, so no variance claims yet:

| module | B0 human | B2 single shot | B3 coverage agent | B4 mutation agent |
|---|---|---|---|---|
| vioreg_gate | 81.0 | 82.1 | 88.5 | 97.0 |
| vioreg_score | 66.3 | 52.5 | 70.1 | 79.6 |
| vioreg_variance | 36.5 | 37.6 | 71.4 | 62.4 (stalled) |
| vioreg_sensitivity | 42.3 | 85.0 | 86.1 | 92.8 |

Caveats: B4 beat B3 on 3 of 4 modules but lost on variance; with one run per cell that is not
distinguishable from noise. "target_reached" for B3 means 100% line coverage, not a mutation target.

## Held-out vioreg, runs 2+3 combined (3 repeats per cell, except two cells with 2)

Mean mutation score %, population sd, range. B0 is human tests (1 run, deterministic).
Two sensitivity cells (B2 repeat 1, B3 repeat 0) first ended in API timeouts; they were rerun
after adding client retries, so every cell now has n=3. Run 3 cost $10.48; run 2 cost $5.82.

| module | B0 | B2 single shot | B3 coverage agent | B4 mutation agent |
|---|---|---|---|---|
| vioreg_gate | 81.0 | 83.7 (sd 1.8) | 85.6 (sd 2.1) | 97.3 (sd 0.2) |
| vioreg_score | 66.3 | 55.8 (sd 4.8) | 68.4 (sd 1.4) | 78.3 (sd 3.7) |
| vioreg_variance | 36.5 | 40.2 (sd 1.9) | 70.4 (sd 0.7) | 63.9 (sd 1.5) |
| vioreg_sensitivity | 42.3 | 87.1 (sd 1.5) | 87.3 (sd 1.2) | 93.7 (sd 0.8) |

Cost per run (B2/B3/B4): gate $0.44/$0.51/$0.86, score $0.16/$0.37/$0.54,
variance $0.10/$0.41/$0.64, sensitivity $0.22/$0.28/$0.90.
Readings: B4 > B3 on gate, score, sensitivity with non-overlapping ranges; B3 > B4 on variance,
also non-overlapping (69.7-71.4 vs 62.4-66.0). n=3 is small, so these are consistent-direction
observations, not significance tests.

## Dev set, final harness (3 repeats per cell), `dev_final.json`

The dev set is the four modules the harness was tuned on, so it is NOT a held-out result; treat the
vioreg table above as the headline. Mean mutation score %, population sd:

| module | B0 human | B2 single shot | B3 coverage agent | B4 mutation agent |
|---|---|---|---|---|
| ratelimiter | 93.5 | 96.8 (sd 0.0) | 96.8 (n=2 valid, see below) | 100.0 (sd 0.0) |
| retrying | 66.0 | 73.5 (sd 2.3) | 82.4 (sd 0.3) | 98.5 (sd 1.1) |
| schedule | 76.5 | 63.3 (sd 7.6) | 81.0 (sd 1.6) | 96.5 (sd 0.4) |
| xmltodict | 87.4 | 65.8 (sd 1.7) | 84.7 (sd 0.8) | 88.7 (sd 0.8) |

Cost per run (B2/B3/B4): ratelimiter $0.04/$0.05/$0.04, retrying $0.06/$0.10/$0.32,
schedule $0.16/$0.48/$0.73, xmltodict $0.21/$0.89/$0.71. Dev-set run total $11.35.

Notes:
- ratelimiter B3 repeat 0 produced no valid suite ("failing", excluded from the mean above, not
  counted as 0). The agent asserted what the spec says (`tokens()` returns a float) and the code
  returns an int at capacity because `_refill` uses `min(self.capacity, ...)`. That is a genuine
  spec/code mismatch in my own fixture, which the agents flagged via POSSIBLE_BUG in several runs.
- ratelimiter is at the ceiling (96.8 to 100), so it separates nothing.
- xmltodict: B4 beats B3 by only 4 points and barely beats the human tests (88.7 vs 87.4), the
  weakest agent result. Human tests are strongest where the project's own suite is mature.
- schedule and xmltodict: single shot is below the human tests (63.3 vs 76.5, 65.8 vs 87.4).

## Why B4 trails B3 on vioreg_variance (diagnosed from stored suites, no API spend)

Established:
- Every B4 run ends with exactly 232 `no_tests` mutants and 75% line coverage. The unexecuted lines
  (173-214, 259 of variance.py) are one function, `plot_spread`, which imports matplotlib.
- matplotlib is not installed in the benchmark environment (it is not in the `bench` extra), so the
  environment note correctly lists it as unavailable. B4's suites cover that function with
  `pytest.importorskip("matplotlib")`, so those tests skip and the mutants are never run against a test.
- B3's suites reach 100% line coverage using mocks (`monkeypatch`/`mock`), which executes the plotting
  lines without matplotlib. B3's rounds were also driven by "uncovered lines", so covering them was its goal.
- The 232 unreachable mutants are 29% of the 812 total, which alone caps B4's score at 71%. B4 scored 62 to 66.

Not established (would need per-mutant data): which mutants B3 killed versus left alive. If B3's roughly
240 survivors are mostly the plot mutants, then B3's mocked coverage earned line coverage but few real
kills there, and the gap on the rest of the module is B4 killing fewer reachable mutants (44 to 73
survivors among the 580 reachable ones), which is a separate, smaller effect.

Consequence for reading the table: the variance row mixes an environment artifact with a real
difference. The score gap should not be read as "coverage feedback beats mutation feedback" on this module.
A supplementary run with matplotlib installed, reported separately and not replacing the numbers above,
would show whether the gap closes. The held-out numbers above stay as run (environment unchanged).
