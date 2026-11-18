Done: S1 scaffold; S2 run_grade; S3 Docker sandbox (verified on Mac); S4 agent loop (first real run: see bench/results/README.md); S5a review: message-mutant finding, spec scoring default, flaky validation (validate.py).
Next: re-run the agent with the new prompt + spec scoring on ratelimiter; S5b baselines B0-B3 + benchmark runner; pick the other 11 modules.
Docker golden test expects 29 killed / 2 survived under spec scoring; rebuild the image (docker build) before re-running it.
