Done: S1 scaffold; S2 grader (mutagent.runner.run_grade: temp workspace, pytest + coverage baseline, mutmut -> GradeReport; golden ratelimiter human tests = 29 killed / 14 survived).
Next: S3 Docker sandbox (no network, read-only module) wrapping run_grade, then S4 agent loop.
Open: pick the other 11 benchmark modules; pin Python 3.12 + mutmut 3.8.1 (tested on 3.10 and 3.13).
