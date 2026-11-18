from dataclasses import dataclass


@dataclass(frozen=True)
class Grade:
    killed: int
    survived: int
    timeout: int = 0   # reported separately, never folded into the score
    no_tests: int = 0  # mutants no test reached

    @property
    def mutation_score(self) -> float:
        scored = self.killed + self.survived
        if scored == 0:
            raise ValueError("no scored mutants")
        return self.killed / scored


def flaky_rate(runs: list[dict[str, bool]]) -> float:
    """runs: one dict per rerun, mapping test id -> passed."""
    tests = set().union(*runs)
    flaky = {t for t in tests if len({r.get(t) for r in runs}) > 1}
    return len(flaky) / len(tests)


def grade_from_cicd_stats(stats: dict) -> Grade:
    """Build a Grade from the JSON that `mutmut export-cicd-stats` writes
    (mutants/mutmut-cicd-stats.json). Only killed and survived are scored."""
    return Grade(
        killed=int(stats["killed"]),
        survived=int(stats["survived"]),
        timeout=int(stats.get("timeout", 0)),
        no_tests=int(stats.get("no_tests", 0)),
    )
