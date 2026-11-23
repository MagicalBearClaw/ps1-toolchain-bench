"""Section sizes of a linked ELF, independent of which toolchain built it."""

import struct
from dataclasses import dataclass
from pathlib import Path

SHT_NOBITS = 8
SHF_WRITE, SHF_ALLOC, SHF_EXECINSTR = 1, 2, 4

# nugget's ps-exe.ld: a 2048-byte PS-X EXE header section, and .data padded to
# a multiple of 2048 bytes (for CD-ROM loading) with this fill pattern, which
# starts right after the last real byte. Neither is program content, and
# counting them would hide any real size difference.
EXE_HEADER_SECTION = ".PSX_EXE_Header"
PAD_SECTION = ".data"
PAD_FILL = b"PADD"


def _strip_padding(contents: bytes) -> int:
    """Length of contents without trailing nugget padding.

    The padding is the longest suffix that is a prefix of PADD repeated.
    Data that itself ends in the bytes of "PADD" would be undercounted by
    those bytes; real programs do not end .data that way.
    """
    pattern = PAD_FILL * (len(contents) // len(PAD_FILL) + 1)
    for start in range(len(contents) + 1):
        tail = contents[start:]
        if pattern.startswith(tail):
            return start
    return len(contents)


@dataclass
class Section:
    name: str
    type: int
    flags: int
    align: int
    size: int
    contents: bytes  # empty for NOBITS sections


def read_sections(path: Path) -> list[Section]:
    """The sections of a little-endian ELF32 file, null section excluded."""
    raw = Path(path).read_bytes()
    if raw[:4] != b"ELF" or raw[4] != 1 or raw[5] != 1:
        raise ValueError(f"{path}: not a little-endian ELF32 file")
    shoff, = struct.unpack_from("<I", raw, 32)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", raw, 46)
    headers = [struct.unpack_from("<10I", raw, shoff + i * shentsize) for i in range(shnum)]
    strtab = headers[shstrndx][4]

    def name_of(off: int) -> str:
        start = strtab + off
        return raw[start:raw.index(b"\0", start)].decode("ascii", "replace")

    return [Section(name_of(h[0]), h[1], h[2], h[8], h[5],
                    b"" if h[1] == SHT_NOBITS else raw[h[4]:h[4] + h[5]])
            for h in headers[1:]]


def section_sizes(path: Path) -> dict[str, int]:
    """Sum the allocated sections of a little-endian ELF32 file.

    text: executable sections. data: other loaded sections (.rodata, .data,
    .sdata, ...). bss: NOBITS sections (.bss, .sbss).
    """
    sizes = {"text": 0, "data": 0, "bss": 0}
    for sec in read_sections(path):
        if not sec.flags & SHF_ALLOC or sec.name == EXE_HEADER_SECTION:
            continue
        if sec.type == SHT_NOBITS:
            sizes["bss"] += sec.size
        elif sec.flags & SHF_EXECINSTR:
            sizes["text"] += sec.size
        elif sec.name == PAD_SECTION:
            sizes["data"] += _strip_padding(sec.contents)
        else:
            sizes["data"] += sec.size
    return sizes
