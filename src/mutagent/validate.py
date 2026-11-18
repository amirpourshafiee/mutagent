"""Flakiness check: rerun the suite under different random orders and compare outcomes."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from mutagent.grading import flaky_rate
from mutagent.runner import build_workspace


def parse_junit(xml_text: str) -> dict[str, bool]:
    out = {}
    for case in ET.fromstring(xml_text).iter("testcase"):
        bad = case.find("failure") is not None or case.find("error") is not None
        out[f"{case.get('classname')}::{case.get('name')}"] = not bad
    return out


def validate_flaky(module_file: Path, tests_dir: Path, runs: int = 10) -> float:
    """Fraction of tests whose pass/fail result differs between randomized reruns."""
    with tempfile.TemporaryDirectory(prefix="mutagent-val-") as tmp:
        ws = Path(tmp)
        build_workspace(ws, module_file, tests_dir)
        # grading disables pytest-randomly; validation needs it on
        cfg = ws / "pyproject.toml"
        cfg.write_text(cfg.read_text().replace("-p no:randomly ", ""))
        results = []
        for seed in range(runs):
            junit = ws / f"r{seed}.xml"
            subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                 f"--junitxml={junit}", f"--randomly-seed={seed}"],
                cwd=ws, capture_output=True, text=True, check=False,
            )
            results.append(parse_junit(junit.read_text()))
        return flaky_rate(results)
