"""The PS1 runtime in runtime/, and the gas parity check for its assembly.

`bench runtime` assembles every runtime .s file with GCC (gas) and with
clang's integrated assembler, then compares the two objects as listed by GNU
objdump and nm: loaded sections, disassembly with relocations, data bytes and
symbols. Both toolchains build test programs from these same files.
"""

import difflib
import itertools
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT, Tools
from .elfinfo import SHF_ALLOC, SHF_EXECINSTR, SHF_WRITE, SHT_NOBITS, read_sections

RUNTIME = ROOT / "runtime"
CRT0 = RUNTIME / "common" / "crt0" / "crt0.s"
PRINTF = RUNTIME / "common" / "syscalls" / "printf.s"
LDSCRIPTS = [RUNTIME / "nooverlay.ld", RUNTIME / "ps-exe.ld"]

# From nugget's common.mk ARCHFLAGS; .s files are assembled with only these.
GCC_ARCHFLAGS = ["-march=mips1", "-mabi=32", "-EL", "-fno-pic", "-mno-shared", "-mno-abicalls",
                 "-mfp32", "-mno-llsc", "-fno-stack-protector", "-nostdlib", "-ffreestanding"]
# The psx triple's driver defaults cover the same ground (MIC-15).
CLANG_TARGET = ["--target=mipsel-sony-psx"]

# Loaded sections that describe the object rather than hold program content.
# The linker scripts discard .MIPS.abiflags; .reginfo is MIC-27's to settle.
METADATA_SECTIONS = {".reginfo", ".MIPS.abiflags"}


def section_table(obj: Path) -> list[str]:
    """One row per loaded section with contents: name, flags, alignment, size.

    Empty sections are left out. LLVM's MIPS streamer raises .text, .data and
    .bss to 16-byte alignment and gas does not, which only changes a link when
    the section holds something.
    """
    rows = []
    for sec in read_sections(obj):
        if not sec.flags & SHF_ALLOC or sec.size == 0 or sec.name in METADATA_SECTIONS:
            continue
        flags = "A" + ("W" if sec.flags & SHF_WRITE else "") + ("X" if sec.flags & SHF_EXECINSTR else "")
        rows.append((sec.name, flags, f"align {sec.align}", f"size {sec.size}"))
    rows.sort()
    widths = [max(len(r[i]) for r in rows) for i in range(3)] if rows else []
    return ["  ".join(c.ljust(w) for c, w in zip(r[:3], widths)) + "  " + r[3] for r in rows]


def normalize_objdump(text: str) -> str:
    """objdump output without the leading line that names the object file."""
    lines = text.splitlines(keepends=True)
    lines = [l for l in lines if "file format" not in l]
    while lines and not lines[0].strip():
        lines.pop(0)
    return "".join(lines)


def side_by_side(left: str, right: str, width: int = 60) -> str:
    """Two listings in columns. '|' marks a changed row, '<' or '>' a row on
    one side only, as in diff -y."""
    a, b = left.expandtabs().splitlines(), right.expandtabs().splitlines()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        for l, r in itertools.zip_longest(a[i1:i2], b[j1:j2]):
            if tag == "equal":
                mark = " "
            elif l is None:
                mark = ">"
            elif r is None:
                mark = "<"
            else:
                mark = "|"
            line = f"{(l or ''):<{width}} {mark} {r or ''}"
            out.append(line.rstrip())
    return "\n".join(out) + "\n"


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                          stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{proc.stdout}{proc.stderr}")
    return proc.stdout


def listing(tools: Tools, obj: Path) -> str:
    """Everything the check compares about one object, as text."""
    objdump, nm = tools.gcc_prefix + "objdump", tools.gcc_prefix + "nm"
    parts = ["Sections:\n" + "\n".join(section_table(obj)) + "\n\n"]
    # -z: objdump otherwise folds runs of zero words (nops) into "...".
    parts.append(normalize_objdump(_run([objdump, "-d", "-r", "-z", str(obj)])))
    for sec in read_sections(obj):
        if (sec.flags & SHF_ALLOC and not sec.flags & SHF_EXECINSTR and sec.type != SHT_NOBITS
                and sec.size and sec.name not in METADATA_SECTIONS):
            parts.append("\n" + normalize_objdump(_run([objdump, "-s", "-r", "-j", sec.name, str(obj)])))
    parts.append("\nSymbols:\n" + "".join(sorted(_run([nm, str(obj)]).splitlines(keepends=True),
                                                 key=lambda l: l.split()[-1])))
    return "".join(parts)


@dataclass
class ParityResult:
    source: str
    same: bool
    report: Path


def assemble_gcc(tools: Tools, src: Path, obj: Path) -> None:
    _run([tools.gcc_prefix + "gcc", *GCC_ARCHFLAGS, f"-I{RUNTIME}", "-g", "-c", "-o", str(obj), str(src)])


def assemble_clang(tools: Tools, src: Path, obj: Path) -> None:
    _run([str(tools.clang_bin / "clang"), *CLANG_TARGET, f"-I{RUNTIME}", "-g", "-c",
          "-o", str(obj), str(src)])


def check_parity(tools: Tools, out: Path) -> list[ParityResult]:
    """Assemble each runtime .s file both ways and compare the listings.

    Writes <out>/<source>.txt with gas on the left and clang on the right.
    """
    results = []
    for src in sorted(RUNTIME.rglob("*.s")):
        rel = src.relative_to(RUNTIME).as_posix()
        stem = out / rel
        stem.parent.mkdir(parents=True, exist_ok=True)
        gcc_obj, clang_obj = stem.with_suffix(".gcc.o"), stem.with_suffix(".clang.o")
        assemble_gcc(tools, src, gcc_obj)
        assemble_clang(tools, src, clang_obj)
        left, right = listing(tools, gcc_obj), listing(tools, clang_obj)
        report = stem.with_suffix(".txt")
        header = f"{'gas (' + rel + ')':<60}   clang integrated assembler\n\n"
        report.write_text(header + side_by_side(left, right), encoding="utf-8")
        results.append(ParityResult(rel, left == right, report))
    return results
