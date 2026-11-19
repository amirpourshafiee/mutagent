B0 (project's own tests), spec scoring, 2026-11-18:
inflection 56.2% (223/174) | retrying 66.3% (173/88) | schedule 76.5% (411/126) | xmltodict 87.4% (568/82) | ratelimiter 93.5% (29/2)
Also graded but not selected: ordered_set 89.2%, jsonpointer 92.6% (CLI tests removed), parse 90.0% (1283 mutants, 280 s).
Rejected: base58 and docopt (their tests error under the current pytest).
