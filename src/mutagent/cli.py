"""Command line entry point used inside the sandbox image: grade a module and print JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mutagent.runner import TestsFailing, run_grade


def report_to_json(report) -> str:
    return json.dumps(
        {
            "killed": report.grade.killed,
            "survived": report.grade.survived,
            "timeout": report.grade.timeout,
            "no_tests": report.grade.no_tests,
            "line_coverage": report.line_coverage,
            "tests_passed": report.tests_passed,
            "missing_lines": list(report.missing_lines),
            "survivors": [{"name": x.name, "diff": x.diff} for x in report.survivors],
        }
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mutagent")
    p.add_argument("module", type=Path)
    p.add_argument("tests", type=Path)
    p.add_argument("--timeout", type=int, default=900)
    a = p.parse_args(argv)
    try:
        print(report_to_json(run_grade(a.module, a.tests, timeout=a.timeout)))
    except TestsFailing as e:
        print(json.dumps({"error": "tests_failing", "output": e.output[-4000:]}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
