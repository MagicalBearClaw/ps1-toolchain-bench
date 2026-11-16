"""Run a PS1 executable headless in PCSX-Redux and collect what it did."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

LUA_PROBE = Path(__file__).with_name("lua") / "cycles.lua"
LOADED_PREFIX = "Successful: new PC"
BENCH_PREFIX = "BENCH_"
QUIT_MARK = "BENCH_CYCLES="


@dataclass
class Output:
    loaded: bool
    stdout: str
    cycles: int | None


@dataclass
class RunResult:
    exit_code: int | None
    stdout: str
    cycles: int | None
    error: str | None
    raw: str


def parse_output(raw: str) -> Output:
    """Split PCSX-Redux's stdout into the program's own output and the cycle count.

    The program's output is every line after the loader's "Successful: new PC"
    line, up to the quit marker, without the Lua probe's own lines. Trailing
    whitespace is stripped from each line (the BIOS TTY ends lines with CRLF).
    Cycles run from the shell being reached (the BIOS is booted and the
    executable is about to be loaded) to the emulator quitting.
    """
    lines = [line.rstrip() for line in raw.splitlines()]
    marks = {}
    for line in lines:
        if line.startswith(BENCH_PREFIX) and "=" in line:
            key, _, value = line.partition("=")
            marks.setdefault(key, int(value))

    program, loaded, in_program = [], False, False
    for line in lines:
        if not loaded and line.startswith(LOADED_PREFIX):
            loaded = in_program = True
            continue
        if in_program:
            if line.startswith(QUIT_MARK):
                in_program = False
            elif not line.startswith(BENCH_PREFIX):
                program.append(line)

    cycles = None
    if "BENCH_SHELL" in marks and "BENCH_CYCLES" in marks:
        cycles = marks["BENCH_CYCLES"] - marks["BENCH_SHELL"]
    stdout = "".join(line + "\n" for line in program)
    return Output(loaded=loaded, stdout=stdout, cycles=cycles)


def run(exe: Path, bios: Path, program: Path, timeout: float) -> RunResult:
    """Boot the BIOS, load the program and run it until it calls pcsx_exit().

    The interpreter is used, not the dynarec: its cycle counts are
    deterministic and closer to the hardware.
    """
    cmd = [str(exe), "-cli", "-stdout", "-testmode", "-no-ui", "-interpreter", "-run",
           "-bios", str(bios), "-loadexe", str(program), "-dofile", str(LUA_PROBE)]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as e:
        raw = (e.stdout or b"").decode("utf-8", "replace")
        out = parse_output(raw)
        return RunResult(None, out.stdout, None, f"timed out after {timeout:g} s", raw)

    raw = proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")
    out = parse_output(raw)
    error = None if out.loaded else "the emulator did not load the program"
    return RunResult(proc.returncode, out.stdout, out.cycles, error, raw)
