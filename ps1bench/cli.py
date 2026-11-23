"""Command line: bench run / bench list / bench runtime."""

import argparse
import datetime
import sys
from pathlib import Path

from . import emulator, report
from .build import BuildError, Clang, Gcc, Unavailable
from .compare import Variant, check_variant, compare_pair
from .config import DEFAULT_OPTS, ROOT, ConfigError, discover_tests, load_test, load_tools
from .elfinfo import section_sizes
from .runtime import check_parity


def _build_and_run(toolchain, spec, opt, tools) -> Variant:
    out = ROOT / "build" / spec.name / toolchain.name / opt.lstrip("-")
    try:
        elf = toolchain.build(spec, opt, out)
    except BuildError as e:
        (out / "build.log").write_text(e.log, encoding="utf-8")
        return Variant(toolchain.name, opt, built=False,
                       error=f"build failed: {e} (see {out / 'build.log'})")
    result = emulator.run(tools.pcsx_exe, tools.bios, elf, spec.timeout)
    (out / "emulator.log").write_text(result.raw, encoding="utf-8")
    return Variant(toolchain.name, opt, built=True, stdout=result.stdout,
                   exit_code=result.exit_code, cycles=result.cycles,
                   sizes=section_sizes(elf), error=result.error)


def run_test(spec, opts, toolchains, tools, enforce_thresholds) -> report.TestResult:
    skipped, opt_results = set(), []
    for opt in opts:
        variants, problems = [], []
        for tc in toolchains:
            try:
                v = _build_and_run(tc, spec, opt, tools)
            except Unavailable as e:
                skipped.add(f"{tc.name}: {e}")
                continue
            variants.append(v)
            problems += [f"{tc.name}: {p}"
                         for p in check_variant(v, spec.exit_code, spec.expected_stdout)]

        comparison = None
        by_name = {v.toolchain: v for v in variants if v.built and not v.error}
        if "gcc" in by_name and "clang" in by_name:
            comparison = compare_pair(by_name["gcc"], by_name["clang"], spec.thresholds)
            problems += comparison.problems
            if enforce_thresholds:
                problems += [f"{m} over the {spec.thresholds[m]:g}% threshold"
                             for m in comparison.over_threshold]
        opt_results.append(report.OptResult(opt, variants, comparison, problems))

    status = "FAIL" if any(o.problems for o in opt_results) else "PASS"
    return report.TestResult(spec.name, status, opt_results, sorted(skipped))


def _select(names: list[str]) -> list[Path]:
    all_tests = discover_tests()
    if not names:
        return all_tests
    chosen = []
    for n in names:
        n = n.replace("\\", "/").rstrip("/")
        matches = [t for t in all_tests
                   if (rel := t.relative_to(ROOT).as_posix()) == n or rel.startswith(n + "/")]
        if not matches:
            raise ConfigError(f"no test matches {n!r} (see `bench list`)")
        chosen += [m for m in matches if m not in chosen]
    return chosen


def _runtime(tools) -> int:
    if tools.clang_bin is None:
        raise ConfigError("bench runtime needs [clang] bin in tools.toml")
    results = check_parity(tools, ROOT / "build" / "runtime")
    for r in results:
        print(f"{'SAME' if r.same else 'DIFF'}  {r.source}  ({r.report})")
    differ = sum(not r.same for r in results)
    print(f"\n{len(results) - differ} same, {differ} different.")
    return 1 if differ else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bench", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list the tests")
    r = sub.add_parser("run", help="build, run and compare tests")
    r.add_argument("tests", nargs="*", help="test or tier names (default: all)")
    r.add_argument("--opt", action="append",
                   help="optimization level such as Os or O2 (or --opt=-O2), "
                        "repeatable (default: Os and O2)")
    r.add_argument("--tools", type=Path, default=ROOT / "tools.toml")
    r.add_argument("--report-dir", type=Path)
    r.add_argument("--enforce-thresholds", action="store_true",
                   help="fail tests whose size or cycles are over threshold")
    rt = sub.add_parser("runtime", help="check that clang assembles runtime/ the way gas does")
    rt.add_argument("--tools", type=Path, default=ROOT / "tools.toml")
    args = p.parse_args(argv)

    try:
        if args.cmd == "list":
            for t in discover_tests():
                print(t.relative_to(ROOT).as_posix())
            return 0
        if args.cmd == "runtime":
            return _runtime(load_tools(args.tools))

        tools = load_tools(args.tools)
        specs = [load_test(t) for t in _select(args.tests)]
    except ConfigError as e:
        print(f"bench: {e}", file=sys.stderr)
        return 2

    toolchains = [Gcc(tools), Clang(tools)]
    results = []
    for spec in specs:
        opts = [o if o.startswith("-") else "-" + o for o in args.opt or DEFAULT_OPTS]
        res = run_test(spec, opts, toolchains, tools,
                       args.enforce_thresholds)
        results.append(res)
        print(f"{res.status}  {spec.name}")
        for o in res.opts:
            for prob in o.problems:
                print(f"      {o.opt}: {prob}")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = args.report_dir or ROOT / "reports" / stamp
    json_path, md_path = report.write(results, out_dir)
    failed = sum(r.status == "FAIL" for r in results)
    print(f"\n{len(results) - failed} passed, {failed} failed. Report: {md_path}")
    return 1 if failed else 0
