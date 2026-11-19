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
