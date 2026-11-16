import struct
import tempfile
import unittest
from pathlib import Path

from ps1bench.elfinfo import section_sizes

SHT_PROGBITS, SHT_STRTAB, SHT_NOBITS = 1, 3, 8
SHF_WRITE, SHF_ALLOC, SHF_EXECINSTR = 1, 2, 4


def make_elf(sections):
    """A minimal little-endian ELF32.

    sections: (name, type, flags, contents), where contents is bytes, or an
    int size for NOBITS sections.
    """
    ehsize, shentsize = 52, 40
    names = b"\0.shstrtab\0"
    headers, data = [], bytearray()
    for name, sh_type, flags, contents in sections:
        name_off = len(names)
        names += name.encode() + b"\0"
        if isinstance(contents, int):
            headers.append((name_off, sh_type, flags, 0, contents))
        else:
            headers.append((name_off, sh_type, flags, ehsize + len(data), len(contents)))
            data += contents
    strtab_off = ehsize + len(data)
    data += names
    shoff = ehsize + len(data)
    shnum = len(sections) + 2  # the null section and .shstrtab
    ident = b"\x7fELF" + bytes([1, 1, 1]) + bytes(9)
    header = ident + struct.pack("<HHIIIIIHHHHHH", 2, 8, 1, 0, 0, shoff, 0,
                                 ehsize, 0, 0, shentsize, shnum, shnum - 1)
    shdrs = struct.pack("<10I", *([0] * 10))
    for name_off, sh_type, flags, off, size in headers:
        shdrs += struct.pack("<10I", name_off, sh_type, flags, 0, off, size, 0, 0, 4, 0)
    shdrs += struct.pack("<10I", 1, SHT_STRTAB, 0, 0, strtab_off, len(names), 0, 0, 1, 0)
    return header + bytes(data) + shdrs


def sizes(elf):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.elf"
        p.write_bytes(elf)
        return section_sizes(p)


class SectionSizesTest(unittest.TestCase):
    def test_text_data_bss_split(self):
        elf = make_elf([
            (".text", SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR, bytes(16)),
            (".rodata", SHT_PROGBITS, SHF_ALLOC, bytes(8)),
            (".data", SHT_PROGBITS, SHF_ALLOC | SHF_WRITE, bytes(4)),
            (".bss", SHT_NOBITS, SHF_ALLOC | SHF_WRITE, 32),
            (".comment", SHT_PROGBITS, 0, bytes(10)),
        ])
        self.assertEqual(sizes(elf), {"text": 16, "data": 12, "bss": 32})

    def test_psx_exe_header_is_not_counted(self):
        elf = make_elf([
            (".PSX_EXE_Header", SHT_PROGBITS, SHF_ALLOC, bytes(2048)),
            (".text", SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR, bytes(8)),
        ])
        self.assertEqual(sizes(elf), {"text": 8, "data": 0, "bss": 0})

    def test_nugget_padding_at_end_of_data_is_not_counted(self):
        # ps-exe.ld pads .data to a multiple of 2048 bytes with "PADD",
        # starting right after the last real byte.
        data = b"\x11\x22\x33" + (b"PADD" * 10)[:37]
        elf = make_elf([(".data", SHT_PROGBITS, SHF_ALLOC | SHF_WRITE, data)])
        self.assertEqual(sizes(elf)["data"], 3)

    def test_data_that_is_only_padding(self):
        elf = make_elf([(".data", SHT_PROGBITS, SHF_ALLOC | SHF_WRITE, b"PADD" * 8)])
        self.assertEqual(sizes(elf)["data"], 0)

    def test_rejects_non_elf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.bin"
            p.write_bytes(b"PS-X EXE" + bytes(100))
            with self.assertRaises(ValueError):
                section_sizes(p)


if __name__ == "__main__":
    unittest.main()
