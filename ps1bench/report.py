"""JSON and markdown reports of a run."""

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .compare import Comparison, Variant


@dataclass
class OptResult:
    opt: str
    variants: list[Variant]
    comparison: Comparison | None
    problems: list[str]


@dataclass
class TestResult:
    name: str
    status: str  # PASS, FAIL
    opts: list[OptResult]
    skipped: list[str] = field(default_factory=list)


def _json_safe(obj):
    if isinstance(obj, float) and math.isinf(obj):
        return "inf"
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def _fmt_delta(d: float | None) -> str:
    if d is None:
        return "–"
    if math.isinf(d):
        return "+inf%"
    return f"{d:+.1f}%"


def _fmt_int(n: int | None) -> str:
    return "–" if n is None else f"{n:,}"


def write(results: list[TestResult], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = out_dir / "report.json", out_dir / "report.md"
    json_path.write_text(json.dumps(_json_safe([asdict(r) for r in results]), indent=2),
                         encoding="utf-8")

    lines = ["# ps1bench report", "",
             "Deltas are clang against GCC; positive means bigger or slower.", "",
             "| Test | Opt | Status | GCC text | GCC data | GCC cycles | "
             "Δ text | Δ data | Δ cycles | Notes |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in results:
        for o in r.opts:
            gcc = next((v for v in o.variants if v.toolchain == "gcc"), None)
            d = o.comparison.deltas if o.comparison else {}
            notes = list(o.problems)
            if o.comparison and o.comparison.over_threshold:
                notes.append("over threshold: " + ", ".join(o.comparison.over_threshold))
            notes += [f"skipped: {s}" for s in r.skipped]
            status = "FAIL" if o.problems else "PASS"
            lines.append(
                f"| {r.name} | {o.opt} | {status} | "
                f"{_fmt_int(gcc.sizes.get('text') if gcc else None)} | "
                f"{_fmt_int(gcc.sizes.get('data') if gcc else None)} | "
                f"{_fmt_int(gcc.cycles if gcc else None)} | "
                f"{_fmt_delta(d.get('text'))} | {_fmt_delta(d.get('data'))} | "
                f"{_fmt_delta(d.get('cycles'))} | {'; '.join(notes)} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
