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
