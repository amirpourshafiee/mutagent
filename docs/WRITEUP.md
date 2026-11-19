# mutagent: an LLM test-writing agent, graded by mutation testing

**Amir Pourshafiee** · November 2026 · [github.com/amirpourshafiee/mutagent](https://github.com/amirpourshafiee/mutagent)

## Summary

I built an agent that writes pytest tests for a Python module from its source code and a plain-English
spec, then improves them using feedback. I graded it with mutation testing (mutmut) instead of line
coverage, because a test suite only has value if it fails when the code is wrong. Across eight
modules and three repeats each, the agent that sees surviving mutants beat the project's own
human-written tests on all eight, and beat an agent guided by coverage on seven of eight. The study is
small, uses one model, and has real limits, which are listed below.

## Why mutation testing

Line coverage tells you which lines ran, not whether any test would notice a bug on them. Mutation
testing changes the code on purpose (flip a comparison, swap an operator, drop a statement) and checks
whether the tests fail. A mutant the tests miss is a bug the suite would let through. The score I
report is:

    mutation score = killed / (killed + survived + no_tests)

Mutants with no covering test count against the suite, and timeouts are excluded. This is stricter than
coverage: in one case (below) a suite reached 100% line coverage and still left about 30% of the
mutants alive (232 to 246 of 812).

## How the agent works

1. **Draft.** The model gets the module, the spec, and an environment note (the import line, which
   third-party packages are installed, signatures of sibling modules). It returns a full pytest file.
2. **Repair.** If tests fail, it sees the failure output and fixes them, up to two times.
3. **Improve.** It is shown up to five surviving mutants as diffs (plus lines never executed) and
   returns only new tests, which are appended. A candidate is kept only if it passes, clears an
   anti-cheat guard, and strictly raises the score.
4. **Stop** at the target, after two stalled rounds, at six rounds, or at a $1 budget per run.

The guard rejects tests that read files, use `exec`/`eval`, import `inspect` or `mutmut`, or assert
exception message text, since none of those test behavior. If the code contradicts the spec, the agent
is told to report `POSSIBLE_BUG:` instead of asserting the bug.

## Experimental setup

Four baselines, all graded the same way:

| Name | What it is |
|---|---|
| B0 | Human-written tests (the project's own suite) |
| B2 | Single shot: draft and repair only, no improvement rounds |
| B3 | Agent that sees only uncovered lines and optimizes line coverage |
| B4 | Full agent: sees surviving mutants and optimizes mutation score |

Eight modules in two groups. The **dev set** is four modules I tuned the harness on: a small rate
limiter I wrote, and three open-source libraries (`retrying`, `schedule`, `xmltodict`) using their own
tests as B0 and their README as the spec. The **held-out set** is four modules of `vioreg`, a separate
perception-testing project of mine (`gate`, `score`, `variance`, `sensitivity`), which I did not use
for tuning. The configuration was frozen before the held-out runs: target 1.0, six rounds, five
survivors shown, two repairs, $1 per run, Claude Sonnet 5.5, mutmut 3.8.1, Python 3.12. Each cell is
the mean of three repeats.

## Results

Mean mutation score (%), with population standard deviation for the agent baselines.

**Held-out (vioreg)**

| Module | B0 human | B2 single shot | B3 coverage | B4 mutation |
|---|---|---|---|---|
| gate | 81.0 | 83.7 (1.8) | 85.6 (2.1) | **97.3** (0.2) |
| score | 66.3 | 55.8 (4.8) | 68.4 (1.4) | **78.3** (3.7) |
| variance | 36.5 | 40.2 (1.9) | **70.4** (0.7) | 63.9 (1.5) |
| sensitivity | 42.3 | 87.1 (1.5) | 87.3 (1.2) | **93.7** (0.8) |

**Dev set**

| Module | B0 human | B2 single shot | B3 coverage | B4 mutation |
|---|---|---|---|---|
| ratelimiter | 93.5 | 96.8 (0.0) | 96.8 (0.0)* | **100.0** (0.0) |
| retrying | 66.0 | 73.5 (2.3) | 82.4 (0.3) | **98.5** (1.1) |
| schedule | 76.5 | 63.3 (7.6) | 81.0 (1.6) | **96.5** (0.4) |
| xmltodict | 87.4 | 65.8 (1.7) | 84.7 (0.8) | **88.7** (0.8) |

\* Two valid runs; the third produced no valid suite (explained below).

A B4 run cost between $0.04 and $0.90 in API fees, about two to five times a single shot.

## What the results show

- **The feedback loop is what helps.** B2, the model alone, was worse than the human tests on three
  modules (`schedule`, `xmltodict`, `score`). Showing the model which mutants survived is what moved
  scores into the 90s.
- **Agent against humans.** B4 beat B0 on all eight modules. The margin on `xmltodict` is small
  (88.7 against 87.4), because that project's own suite is mature. The largest gaps are where the human
  tests were weak (`sensitivity`, `variance`).
- **Mutation feedback against coverage feedback.** B4 beat B3 on seven of eight, with non-overlapping
  ranges on most of them. The exception is `variance`, covered next.

## The one result that went against me

On `variance`, the coverage agent scored 70.4 and the mutation agent 63.9. I diagnosed it from the
stored suites. One function, `plot_spread`, imports matplotlib, which is not installed in the
benchmark environment. The mutation agent wrote tests for it guarded by `pytest.importorskip`, which
skip honestly, so 232 mutants (29% of the module) had no test at all. That alone caps its score at 71%.
The coverage agent got to 100% line coverage by mocking the plotting library, which runs the lines
without checking real behavior. So that row mixes an environment artifact with, possibly, a smaller
real difference on the rest of the module. I could not separate the two without per-mutant data, and I
chose not to rerun with matplotlib installed, since changing the environment after seeing held-out
results would weaken the held-out claim. The numbers stay as run.

## Mistakes that mattered

The first benchmark runs were wrong because of my harness, not the model. In order:

- **Pilot 1 inflated scores.** Mutants that no test reached were left out of the score, and the agent
  rewrote the whole file each round instead of adding tests. I changed the score to count unreached
  mutants against the suite and made improvement rounds append-only. This changed the definition of the
  metric after seeing data, so I disclose it here and in the repository log.
- **A suite with zero passing tests could be accepted and scored.** It now fails the run.
- **A prompt told the model to use only the standard library** for modules that need numpy. All twelve
  first held-out cells failed ($2.71). The environment note fixed it.
- **A reply cut off at the output limit.** The closing code fence went missing, my parser found no code,
  and my retry resent only "no code block" with no spec or module. The model reasonably answered with
  placeholder skipped tests claiming no spec was provided. Raising the limit, detecting truncation, and
  resending the full prompt fixed it. I found this by sending one diagnostic request and reading the
  token counts, after three blind full runs had wasted money.
- **API timeouts** hit two cells. The client now retries, and the bench reruns error rows.

I also excluded exception-message text from scoring. Specs rarely state messages, and scoring them
rewarded pinning implementation details (on the rate limiter, 100% against 72%). One module,
`inflection`, was dropped because its import-time code cannot be killed by mutmut; it is documented in
the repository.

## A side result worth noting

On the rate limiter, which I wrote, the agents flagged in five of nine runs that `tokens()` returns an int at full
capacity while the spec says float. It was a real bug in my code. On one coverage-agent run, the agent
asserted the spec-correct behavior, the test failed against the code, and no valid suite came out. That
shows a limit of the design: an agent told not to assert buggy behavior can fail to produce a suite when
the code is wrong.

## Limitations

- **Small study.** Three repeats, eight modules, one model. Standard deviations are small, but these
  are consistent directions, not significance tests.
- **Mutation score is a proxy for finding real bugs.** I did not check whether suites that kill more
  mutants also catch more real defects. Mutmut's mutations may not match the bugs people write.
- **White-box.** The agent sees the source, so it can write tests that mirror the implementation. The
  spec and the guard limit this; they do not remove it.
- **Dev and held-out are not equally strong evidence.** The dev set is what I tuned on. The held-out
  set is my own project, and its human tests were written with AI assistance, so B0 there is not a
  clean human baseline.
- **Specs vary.** One I wrote, three are READMEs, and four combine a module docstring with a doc page.

## Cost and reproduction

The final runs cost about $29 in API fees ($17 held-out, $11 dev). Pilots and failed attempts cost more.
Everything is in the repository: raw results per run, a log of every finding and fix
(`bench/results/README.md`), and the harness. To reproduce:

    python3.12 -m venv .venv && . .venv/bin/activate
    pip install -e ".[llm,dev,bench]"
    export ANTHROPIC_API_KEY=...
    python -m mutagent.bench --out bench/results/my_run.json --modules ratelimiter \
        --baselines B2 B3 B4 --repeats 1 --max-usd 5

## Built with AI assistance

I designed the project, set the experiment rules, and ran and reviewed the benchmarks. I built the
code with Claude (Anthropic) as a coding assistant, and the agent itself calls Claude Sonnet 5.5.
