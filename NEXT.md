Done: S1 scaffold; S2 run_grade (golden 29/14); S3 Docker sandbox (verified on Mac); S4 agent loop (agent.py, llm.py, agent_cli.py; unit tested with a fake LLM, NOT yet run against the real API).
Next: first real run on ratelimiter (needs ANTHROPIC_API_KEY, pip install -e ".[llm]"):
  python -m mutagent.agent_cli bench/modules/ratelimiter/src/ratelimiter.py bench/modules/ratelimiter/SPEC.md /tmp/rl-run --budget 0.5
Then S5 baselines B0-B3 and the benchmark runner; pick the other 11 modules.
