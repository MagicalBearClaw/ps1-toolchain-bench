# ps1-toolchain-bench

A differential test and benchmark harness for PlayStation 1 toolchains. It compiles the same C source with nugget's GCC 16.2 and with the [PS1 LLVM fork](https://github.com/MagicalBearClaw/llvm-project-ps1-mips), runs both headless in PCSX-Redux, and compares their output, exit code, size and cycles.

GCC is the baseline. Until the clang pipeline lands (M2, MIC-31), the clang variants are skipped, and each test is checked against its own expected output.

## Setup

1. Install the tools listed in [docs/tools.md](docs/tools.md): GCC 16.2 (`mipsel-none-elf`), PCSX-Redux CLI, and Python 3.11 or newer.
2. Run `git submodule update --init` to fetch nugget, pinned to the commit the PCSX-Redux build uses.
3. Copy `tools.example.toml` to `tools.toml` and set the paths. `tools.toml` is ignored by git.

## Usage

```
python -I bench.py list
python -I bench.py run                      # every test, at -Os and -O2
python -I bench.py run micro                # a whole tier
python -I bench.py run micro/hello --opt O2
python -I bench.py run --enforce-thresholds # also fail on size or cycle growth
python -I bench.py runtime                  # clang vs gas on the runtime's assembly
```

- `run` prints PASS or FAIL for each test and exits with 1 if any test failed.
- Each run writes `reports/<time>/report.md` and `report.json`.
- Build outputs, build logs and emulator logs go to `build/<test>/<toolchain>/<opt>/`.

A test **fails** when:
- it does not build;
- it times out;
- its exit code differs from `exit_code`;
- its stdout differs from `expected.txt`;
- the GCC and clang variants differ in stdout or exit code;
- with `--enforce-thresholds`, clang's text, data or cycles grow past the test's threshold compared with GCC.

## Tests

The four tiers are `micro/`, `suites/` (CoreMark, Dhrystone), `examples/` (nugget, PSn00bSDK) and `hazard/`. A test is a directory under a tier with a `test.toml`. Every key in it is optional:

```toml
sources = ["main.c"]   # default: every .c and .s file in the directory
runtime = "nugget"     # nugget crt0 + printf; "none" = the sources define _start
exit_code = 0          # what the program passes to pcsx_exit()
timeout = 60           # seconds of emulator wall time

[thresholds]           # growth allowed against GCC, in percent (default 5)
text = 5
data = 5
cycles = 5
```

An `expected.txt` next to it holds the exact expected stdout. C tests include `bench.h`, which provides nugget's `ramsyscall_printf` and `bench_exit(code)`.

## What is measured

- **Build.** The GCC variant uses nugget's `common.mk` flags. It links the crt0, `printf` and `ps-exe.ld` in [runtime/](runtime/README.md), which are nugget's files copied unchanged with their MIT licence. The clang variant will link the same files (MIC-31).
- **Size.** Sizes come from the ELF:
  - text is the executable sections;
  - data is the other loaded sections;
  - bss is the NOBITS sections.

  The 2048-byte PS-X EXE header and nugget's `PADD` padding at the end of `.data` are not counted.
- **Cycles.** PCSX-Redux runs with the interpreter, which gives the same count on every run. Counting starts when the BIOS reaches the shell and stops when the program calls `pcsx_exit()` (see `ps1bench/lua/cycles.lua`).

## Self-tests

```
python -I -m unittest discover -s selftest -t .
```

Work is tracked in the Linear project "PS1 MIPS Toolchain (LLVM + Zig)".
