"""Tool locations (tools.toml) and test definitions (test.toml)."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIERS = ("micro", "suites", "examples", "hazard")
DEFAULT_THRESHOLD_PCT = 5.0
DEFAULT_OPTS = ("-Os", "-O2")


class ConfigError(Exception):
    pass


@dataclass
class Tools:
    gcc_prefix: str
    pcsx_exe: Path
    bios: Path
    clang_bin: Path | None


@dataclass
class TestSpec:
    name: str
    dir: Path
    sources: list[Path]
    runtime: str
    exit_code: int
    timeout: float
    thresholds: dict[str, float]
    expected_stdout: str | None = field(default=None, repr=False)


def load_tools(path: Path) -> Tools:
    if not path.is_file():
        raise ConfigError(f"{path} not found: copy tools.example.toml to tools.toml "
                          "and set the paths for this machine")
    with path.open("rb") as f:
        t = tomllib.load(f)
    try:
        clang = t.get("clang", {})
        return Tools(
            gcc_prefix=t["gcc"]["prefix"],
            pcsx_exe=Path(t["pcsx-redux"]["exe"]),
            bios=Path(t["pcsx-redux"]["bios"]),
            clang_bin=Path(clang["bin"]) if clang.get("bin") else None,
        )
    except KeyError as e:
        raise ConfigError(f"{path}: missing key {e}") from None


def load_test(test_dir: Path) -> TestSpec:
    """Read <tier>/<name>/test.toml. Every key is optional.

    sources   files to build, relative to the test directory
              (default: every .c and .s file in it)
    runtime   "nugget" links nugget's crt0 and printf; "none" links only the
              sources, which must define _start (default "nugget")
    exit_code value the program passes to pcsx_exit() (default 0)
    timeout   seconds of emulator wall time (default 60)
    [thresholds]  text / data / cycles growth allowed against GCC, in
              percent (default 5 each)

    An expected.txt file next to test.toml, if present, is the exact stdout.
    """
    spec_file = test_dir / "test.toml"
    with spec_file.open("rb") as f:
        t = tomllib.load(f)

    if "sources" in t:
        sources = [test_dir / s for s in t["sources"]]
    else:
        sources = sorted(p for p in test_dir.iterdir() if p.suffix in (".c", ".s"))
    if not sources:
        raise ConfigError(f"{spec_file}: no sources")

    runtime = t.get("runtime", "nugget")
    if runtime not in ("nugget", "none"):
        raise ConfigError(f"{spec_file}: runtime must be \"nugget\" or \"none\"")

    thresholds = {k: DEFAULT_THRESHOLD_PCT for k in ("text", "data", "cycles")}
    for k, v in t.get("thresholds", {}).items():
        if k not in thresholds:
            raise ConfigError(f"{spec_file}: unknown threshold {k!r}")
        thresholds[k] = float(v)

    expected = test_dir / "expected.txt"
    return TestSpec(
        name=test_dir.relative_to(ROOT).as_posix(),
        dir=test_dir,
        sources=sources,
        runtime=runtime,
        exit_code=int(t.get("exit_code", 0)),
        timeout=float(t.get("timeout", 60)),
        thresholds=thresholds,
        expected_stdout=expected.read_text(encoding="utf-8").replace("\r\n", "\n")
        if expected.is_file() else None,
    )


def discover_tests() -> list[Path]:
    """Every directory under a tier that has a test.toml."""
    found = []
    for tier in TIERS:
        found += sorted(p.parent for p in (ROOT / tier).rglob("test.toml"))
    return found
