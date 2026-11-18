Done: S1 scaffold; S2 run_grade (golden ratelimiter 29 killed / 14 survived); S3 Docker sandbox code (Dockerfile, cli, sandbox.run_grade_docker).
Verify on a machine with Docker: docker build -f docker/Dockerfile -t mutagent-grader . && pytest -m slow tests/test_sandbox.py
  (the Docker golden test was skipped in the cloud sandbox because Docker is not installed there; command building and JSON parsing are unit tested).
Next: S4 agent loop (draft tests, repair failures, coverage pass, mutation pass with top 5 survivors).
Open: pick the other 11 benchmark modules; pin Python 3.12 + mutmut 3.8.1.
