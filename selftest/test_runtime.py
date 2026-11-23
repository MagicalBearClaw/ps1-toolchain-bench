import tempfile
import unittest
from pathlib import Path

from ps1bench.runtime import normalize_objdump, section_table, side_by_side
from selftest.test_elfinfo import (SHF_ALLOC, SHF_EXECINSTR, SHF_WRITE, SHT_NOBITS,
                                   SHT_PROGBITS, make_elf)


def table(sections):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.o"
        p.write_bytes(make_elf(sections))
        return section_table(p)


class SectionTableTest(unittest.TestCase):
    def test_lists_loaded_sections_with_flags_alignment_and_size(self):
        rows = table([
            (".start", SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR, bytes(100), 4),
            (".rodata", SHT_PROGBITS, SHF_ALLOC, bytes(16), 4),
            (".bss", SHT_NOBITS, SHF_ALLOC | SHF_WRITE, 8, 16),
        ])
        self.assertEqual(rows, [".bss     AW  align 16  size 8",
                                ".rodata  A   align 4   size 16",
                                ".start   AX  align 4   size 100"])

    def test_skips_empty_sections(self):
        # LLVM's MIPS streamer gives .text, .data and .bss 16-byte alignment;
        # gas does not. That only matters when they have contents.
        rows = table([
            (".text", SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR, b"", 16),
            (".bss", SHT_NOBITS, SHF_ALLOC | SHF_WRITE, 0, 16),
            (".start", SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR, bytes(4), 4),
        ])
        self.assertEqual(rows, [".start  AX  align 4  size 4"])

    def test_skips_unloaded_and_mips_metadata_sections(self):
        rows = table([
            (".comment", SHT_PROGBITS, 0, bytes(10)),
            (".reginfo", SHT_PROGBITS, SHF_ALLOC, bytes(24)),
            (".MIPS.abiflags", SHT_PROGBITS, SHF_ALLOC, bytes(24)),
            (".start", SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR, bytes(4)),
        ])
        self.assertEqual(rows, [".start  AX  align 4  size 4"])


class NormalizeObjdumpTest(unittest.TestCase):
    def test_drops_the_file_name_line(self):
        text = ("\nC:/build/gcc/crt0.o:     file format elf32-tradlittlemips\n\n\n"
                "Disassembly of section .start:\n\n00000000 <_start>:\n")
        self.assertEqual(normalize_objdump(text),
                         "Disassembly of section .start:\n\n00000000 <_start>:\n")


class SideBySideTest(unittest.TestCase):
    def test_marks_only_differing_rows(self):
        out = side_by_side("a\nb\nc\n", "a\nB\nc\n", width=4)
        self.assertEqual(out.splitlines(), ["a      a",
                                            "b    | B",
                                            "c      c"])

    def test_tabs_are_expanded_so_columns_line_up(self):
        out = side_by_side("a\tb\n", "a\tb\n", width=10)
        self.assertEqual(out.splitlines(), ["a       b    a       b"])

    def test_one_side_longer(self):
        out = side_by_side("a\n", "a\nnop\n", width=4)
        self.assertEqual(out.splitlines(), ["a      a",
                                            "     > nop"])


if __name__ == "__main__":
    unittest.main()
