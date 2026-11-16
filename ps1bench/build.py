"""Build a test with one toolchain at one -O level."""

import subprocess
from pathlib import Path

from .config import ROOT, TestSpec, Tools

NUGGET = ROOT / "third_party" / "nugget"
INCLUDE = ROOT / "include"

# From nugget's common.mk (ARCHFLAGS and CPPFLAGS), so the GCC variant is built
# the way nugget projects are.
ARCHFLAGS = ["-march=mips1", "-mabi=32", "-EL", "-fno-pic", "-mno-shared", "-mno-abicalls",
             "-mfp32", "-mno-llsc", "-fno-stack-protector", "-nostdlib", "-ffreestanding"]
GCC_CFLAGS = ["-ffunction-sections", "-fdata-sections", "-mno-gpopt", "-fomit-frame-pointer",
              "-fno-builtin", "-fno-strict-aliasing", "-Wno-attributes",
              # common.mk probes for this. GCC 16 needs it: without it, volatile
              # loads are folded into the next operation and a 32-bit hardware
              # register read can be narrowed to lhu/lbu.
              "-fno-fuse-ops-with-volatile-access", "-g"]
NUGGET_RUNTIME = [NUGGET / "common" / "crt0" / "crt0.s",
                  NUGGET / "common" / "syscalls" / "printf.s"]
LDSCRIPTS = [NUGGET / "nooverlay.ld", NUGGET / "ps-exe.ld"]


class BuildError(Exception):
    def __init__(self, message: str, log: str):
        super().__init__(message)
        self.log = log


class Unavailable(Exception):
    """The toolchain cannot build this variant yet; the variant is skipped."""


def _run(cmd: list[str], log: list[str]) -> None:
    log.append(" ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                          stdin=subprocess.DEVNULL)
    if proc.stdout or proc.stderr:
        log.append(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        raise BuildError(f"{Path(cmd[0]).name} exited with {proc.returncode}", "\n".join(log))


class Gcc:
    name = "gcc"

    def __init__(self, tools: Tools):
        self.prefix = tools.gcc_prefix

    def build(self, spec: TestSpec, opt: str, out: Path) -> Path:
        out.mkdir(parents=True, exist_ok=True)
        cc = self.prefix + "gcc"
        sources = list(spec.sources)
        if spec.runtime == "nugget":
            sources = NUGGET_RUNTIME + sources

        log, objs = [], []
        for i, src in enumerate(sources):
            obj = out / f"{i:02d}-{src.stem}.o"
            if src.suffix == ".s":
                cmd = [cc, *ARCHFLAGS, f"-I{NUGGET}", "-g", "-c", "-o", str(obj), str(src)]
            else:
                cmd = [cc, *ARCHFLAGS, *GCC_CFLAGS, opt, f"-I{NUGGET}", f"-I{INCLUDE}",
                       "-c", "-o", str(obj), str(src)]
            _run(cmd, log)
            objs.append(str(obj))

        elf = out / "test.elf"
        _run([cc, "-g", "-o", str(elf), *objs, f"-Wl,-Map={out / 'test.map'}", "-nostdlib",
              *(f"-T{s}" for s in LDSCRIPTS), "-static", "-Wl,--gc-sections", *ARCHFLAGS,
              "-Wl,--oformat=elf32-littlemips", opt, "-fno-fuse-ops-with-volatile-access"], log)
        _run([self.prefix + "objcopy", "-O", "binary", str(elf), str(out / "test.ps-exe")], log)
        (out / "build.log").write_text("\n".join(log), encoding="utf-8")
        return elf


class Clang:
    name = "clang"

    def __init__(self, tools: Tools):
        self.bin = tools.clang_bin

    def build(self, spec: TestSpec, opt: str, out: Path) -> Path:
        # The clang pipeline (psx triple, crt0 built with clang, lld with
        # nugget's scripts) lands in M2; MIC-31 wires it in here.
        raise Unavailable("clang pipeline not wired yet (MIC-31)")
