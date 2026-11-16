# ps1-toolchain-bench

A differential test and benchmark harness for PlayStation 1 toolchains. It compiles the same C source with nugget's GCC 16.2 and with the [PS1 LLVM fork](https://github.com/MagicalBearClaw/llvm-project-ps1-mips), runs both headless in PCSX-Redux, and compares their output, exit code, size and cycles.

Work is tracked in the Linear project "PS1 MIPS Toolchain (LLVM + Zig)".
