# PS1 runtime

The startup code and linker scripts that test programs link against, for both the GCC and the clang toolchain. They are copied unchanged from [nugget](https://github.com/pcsx-redux/nugget) at commit `0407fbaf`, the commit `third_party/nugget` is pinned to.

nugget is MIT-licensed, © 2019 PCSX-Redux authors. Its licence is in [LICENSE.nugget](LICENSE.nugget), and every file keeps its original header.

| File | nugget path | What it does |
|---|---|---|
| `common/crt0/crt0.s` | `common/crt0/crt0.s` | `_start`: sets the expansion-port bus width, clears `.bss`, calls `main(1, {"PSX.EXE"})` |
| `common/hardware/hwregs.inc` | `common/hardware/hwregs.inc` | Hardware register addresses, included by `crt0.s` |
| `common/syscalls/printf.s` | `common/syscalls/printf.s` | `ramsyscall_printf`, the BIOS A(0x3F) call |
| `ps-exe.ld` | `ps-exe.ld` | Layout for a PS-X EXE: a 2048-byte header, then code and data at `0x80010000` |
| `cpe.ld` | `cpe.ld` | The same layout with a CPE header |
| `nooverlay.ld` | `nooverlay.ld` | Defines `__heap_base` when the program has no overlays |

The directory layout matches nugget's, so `.include "common/hardware/hwregs.inc"` resolves with `-I runtime`.

## Building with clang

```
clang --target=mipsel-sony-psx -I runtime -c runtime/common/crt0/crt0.s -o crt0.o
```

The psx triple supplies the MIPS I, o32, static and no-abicalls defaults that nugget's `common.mk` passes to GCC.

## gas parity

```
python -I bench.py runtime
```

This assembles every `.s` file here with GCC (gas) and with clang's integrated assembler. It then compares the two objects as GNU objdump and nm show them:

- the loaded sections, with flags, alignment and size;
- the disassembly, with relocations;
- the data bytes;
- the symbols.

It prints SAME or DIFF for each file and exits with 1 on any difference. The side-by-side listings go to `build/runtime/`.

Two kinds of difference are not counted:

- **Empty sections.** LLVM's MIPS streamer gives `.text`, `.data` and `.bss` 16-byte alignment even when they are empty, and gas does not.
- **`.reginfo` and `.MIPS.abiflags`.** These describe the object and hold no program code or data.

How lld lays these files out next to GNU ld is MIC-27.

## Updating

Bump `third_party/nugget`, copy the files above again, update the commit here, and run `bench runtime` and `bench run`.
