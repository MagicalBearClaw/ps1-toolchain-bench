"""Checks on one build variant, and GCC-versus-clang comparison of two."""

import math
from dataclasses import dataclass, field

METRICS = ("text", "data", "cycles")


@dataclass
class Variant:
    toolchain: str
    opt: str
    built: bool
    stdout: str | None = None
    exit_code: int | None = None
    cycles: int | None = None
    sizes: dict[str, int] = field(default_factory=dict)
    error: str | None = None

    def metric(self, name: str) -> int | None:
        return self.cycles if name == "cycles" else self.sizes.get(name)


@dataclass
class Comparison:
    deltas: dict[str, float]
    over_threshold: list[str]
    problems: list[str]


def delta_pct(base: int, cand: int) -> float:
    """Relative change of cand against base, in percent."""
    if base == 0:
        return 0.0 if cand == 0 else math.inf
    return (cand - base) * 100.0 / base


def check_variant(v: Variant, expected_exit: int, expected_stdout: str | None) -> list[str]:
    """Problems with one variant on its own: build, run, exit code, expected output."""
    if v.error:
        return [v.error]
    problems = []
    if v.exit_code != expected_exit:
        problems.append(f"exit code {v.exit_code}, expected {expected_exit}")
    if expected_stdout is not None and v.stdout != expected_stdout:
        problems.append("stdout differs from expected.txt")
    return problems


def compare_pair(base: Variant, cand: Variant, thresholds: dict[str, float]) -> Comparison:
    """Compare a candidate (clang) against the baseline (GCC) at one -O level.

    Behaviour must match exactly. Size and cycle growth past a threshold is
    reported in over_threshold; getting smaller or faster never is.
    """
    problems = []
    if base.stdout != cand.stdout:
        problems.append(f"stdout differs between {base.toolchain} and {cand.toolchain}")
    if base.exit_code != cand.exit_code:
        problems.append(f"exit code differs between {base.toolchain} ({base.exit_code}) "
                        f"and {cand.toolchain} ({cand.exit_code})")

    deltas, over = {}, []
    for name in METRICS:
        b, c = base.metric(name), cand.metric(name)
        if b is None or c is None:
            continue
        deltas[name] = delta_pct(b, c)
        if deltas[name] > thresholds[name]:
            over.append(name)
    return Comparison(deltas=deltas, over_threshold=over, problems=problems)
