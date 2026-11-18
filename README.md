# mutagent

An LLM agent that writes pytest tests for a Python module and is graded by mutation testing.
Status: harness under construction (see docs/PLAN.md for the full scope and build plan).

    python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
    pytest -m "not slow"
