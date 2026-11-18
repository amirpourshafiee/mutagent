from dataclasses import dataclass


@dataclass(frozen=True)
class Grade:
    killed: int
    survived: int
    timeout: int = 0   # reported separately, never folded into the score
    no_tests: int = 0  # mutants no test reached; they count as not killed

    @property
    def mutation_score(self) -> float:
        """killed / (killed + survived + no_tests). Mutants no test reaches count against
        the suite: excluding them let a suite raise its score by leaving code untested
        (seen in the pilot: more coverage lowered the score). Timeouts stay out of both."""
        scored = self.killed + self.survived + self.no_tests
        if scored == 0:
            raise ValueError("no scored mutants")
        return self.killed / scored

    @property
    def score_or_zero(self) -> float:
        """Like mutation_score, but 0.0 when nothing was scored (all timeouts)."""
        scored = self.killed + self.survived + self.no_tests
        return self.killed / scored if scored else 0.0


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
