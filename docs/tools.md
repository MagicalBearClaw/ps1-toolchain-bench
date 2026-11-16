# PS1 reference tools

Installed 2026-11-15 for MIC-7. MIC-9 moved this file here from
`G:\git\ps1-tools\TOOLS.md`; `tools.example.toml` points at these paths.

All tools live under `G:\git\ps1-tools`. Two directories are on the user PATH:

* `G:\git\ps1-tools\mips-gcc-16.2.0\bin` (GCC and binutils, `mipsel-none-elf-*`)
* `G:\git\ps1-tools\bin` (shims and single binaries)

The shims are `.cmd` wrappers so that tool DLLs (ffmpeg, a plain `gdb.exe`) stay off PATH.

## Versions

| Tool | Version | Source | SHA-256 of download |
|---|---|---|---|
| GCC (`mipsel-none-elf`) | 16.2.0 | `https://distrib.app/alias/pcsx-redux/mips-toolchain/g++-mipsel-none-elf-16.2.0.zip` | `CF84960F5624829D44B866C5F194094C21C63B30F7CBB8CF3030F1ABEBD52B75` |
| binutils | 2.47.20260726 | same archive | — |
| gdb-multiarch | 17.2 | `https://distrib.app/alias/pcsx-redux/gdb-multiarch-windows/gdb-multiarch-17.2.zip` | `E441ACB54FED04AFD7371E2AC6F9CF3C276701549ED1004D39066161E5502BF8` |
| PCSX-Redux (CLI) | nightly 31613.20261115.53, commit `34d3f593c25d` | distrib.app project `pcsx-redux/dev-win-cli-x64`, build 865 | `1318AC603940510BA522702DA657372956A2133FFD720EC1F36035F95C812C96` (matches the manifest SHA-1 `e2573472…`) |
| mkpsxiso / dumpsxiso | 2.30 | GitHub `Lameguy64/mkpsxiso` release `v2.30`, `mkpsxiso-2.30-win64.zip` | `7D3963CD322DF365766CEE1DBC3E405EA103BBE4E11C0DB86C9688B32F5A1017` |
| psyq-obj-parser | pcsx-redux `34d3f593c25d` | built from source (see below) | — |
| gh | 2.104.0 | `winget install GitHub.cli` | — |

The GCC archive is the one nugget's `mips.ps1` installs (`mips install 16.2.0`).
It is stock GCC with no PS1 patches. I downloaded it directly so that nothing
is installed under `%APPDATA%\mips` and the user PATH is not rewritten.

## Install steps

```powershell
$t = 'G:\git\ps1-tools'; $d = "$t\dl"

# GCC 16.2.0 + binutils, gdb-multiarch
Invoke-WebRequest https://distrib.app/alias/pcsx-redux/mips-toolchain/g++-mipsel-none-elf-16.2.0.zip -OutFile $d\g++-mipsel-none-elf-16.2.0.zip
Expand-Archive $d\g++-mipsel-none-elf-16.2.0.zip $t\mips-gcc-16.2.0
Invoke-WebRequest https://distrib.app/alias/pcsx-redux/gdb-multiarch-windows/gdb-multiarch-17.2.zip -OutFile $d\gdb-multiarch-17.2.zip
Expand-Archive $d\gdb-multiarch-17.2.zip $t\gdb-multiarch-17.2

# PCSX-Redux CLI: find the newest build, then download its "path"
$m = Invoke-RestMethod https://distrib.app/storage/manifests/pcsx-redux/dev-win-cli-x64/manifest.json
$id = ($m.builds | Sort-Object { [long]$_.createdAt } | Select-Object -Last 1).id
$b = Invoke-RestMethod "https://distrib.app/storage/manifests/pcsx-redux/dev-win-cli-x64/manifest-$id.json"
Invoke-WebRequest ("https://distrib.app" + $b.path) -OutFile $d\pcsx-redux-cli.zip   # check $b.hashes.sha1
Expand-Archive $d\pcsx-redux-cli.zip $t\pcsx-redux-<version>

# mkpsxiso
gh release download v2.30 --repo Lameguy64/mkpsxiso -p mkpsxiso-2.30-win64.zip -D $d
Expand-Archive $d\mkpsxiso-2.30-win64.zip $t\mkpsxiso-2.30
```

### psyq-obj-parser

Build it from the same pcsx-redux commit as the emulator. Only a few
submodules are needed. This uses VS 2026 with the ClangCl toolset, from a
shell after `. ps1\scripts\ps1-env.ps1`.

```powershell
$src = 'G:\git\ps1-tools\src\pcsx-redux'
git init $src; git -C $src remote add origin https://github.com/grumpycoders/pcsx-redux.git
git -C $src fetch --depth 1 origin 34d3f593c25d6baa4b8187cb3c17e78a912d3e1b; git -C $src checkout FETCH_HEAD
git -C $src submodule update --init --depth 1 -- third_party/args third_party/fmt third_party/zlib `
  third_party/ELFIO third_party/magic_enum third_party/expected third_party/PEGTL third_party/ucl `
  third_party/iec-60908b third_party/libuv third_party/uriparser third_party/curl third_party/stb `
  third_party/luv third_party/lua third_party/luajit third_party/libffi third_party/tracy
msbuild $src\vsprojects\pcsx-redux.sln /t:restore /p:RestorePackagesConfig=true
msbuild $src\vsprojects\psyq-obj-parser\psyq-obj-parser.vcxproj /m /p:Configuration=Release /p:Platform=x64 "/p:SolutionDir=$src\vsprojects\"
Copy-Item $src\vsprojects\x64\Release\psyq-obj-parser.exe G:\git\ps1-tools\bin
```

## Headless PCSX-Redux

```powershell
pcsx-redux -cli -stdout -testmode -no-ui -run `
  -bios G:\git\ps1-tools\pcsx-redux-31613\openbios.bin -loadexe program.elf
```

* `-loadexe` accepts ELF, PS-X EXE and CPE files.
* BIOS TTY output (`putchar`, `printf`) goes to stdout.
* With `-testmode`, a 16-bit store to `0x1f802082` (`pcsx_exit(code)` in
  nugget's `common/hardware/pcsxhw.h`) quits the emulator with that exit code.
  Without `-testmode` it only pauses. A byte store (`sb`) does not trigger the exit.
* Pass `-bios` explicitly. The CLI build has no saved config on a fresh machine.

Smoke test: `micro/smoke-asm` in this repo (originally
`G:\git\ps1-tools\smoke\hello.s`) prints `hello from asm` through BIOS
`putchar` and exits with code 42.

## Cycle counting

`ps1bench/lua/cycles.lua` is loaded with `-dofile`. It prints
`PCSX.getCPUCycles()` when the BIOS reaches the shell (`BENCH_SHELL`) and when
the emulator quits (`BENCH_CYCLES`). The harness reports the difference, so
the ~18.2M cycles of BIOS boot are not counted. The interpreter (`-interpreter`)
gives the same count on every run; the dynarec count differs slightly.

## Flags that match nugget

```
-march=mips1 -mabi=32 -EL -fno-pic -mno-shared -mno-abicalls -mfp32
-mno-llsc -mno-gpopt -G0 -fno-reg-struct-return -Os
```

GCC 16.2 output for `a / b`: `bne b,$0,1f; div $0,a,b; break 7; 1: mflo`. The
divide-by-zero check fills the branch delay slot with the `div`.
