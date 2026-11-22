# Load delay on the R3000A: the register a load writes still holds its old
# value during the next instruction. Hand-tuned code relies on that inside
# .set noreorder, so the assembler must leave it alone. In reorder mode the
# assembler pads the same pair with a nop, so the new value is read.
# See docs/ps1/hazards.md, H1 and H9, in the LLVM fork.
#
# Exit code: (noreorder result) + (reorder result << 4) = 7 + (42 << 4) = 679.
        .text
        .globl _start
_start:
        la      $s1, value          # holds 42

        li      $t0, 7
        .set noreorder
        lw      $t0, 0($s1)
        addu    $t1, $t0, $zero     # load delay slot: reads the old 7
        .set reorder

        li      $t0, 7
        lw      $t0, 0($s1)
        addu    $t2, $t0, $zero     # padded by the assembler: reads 42

        sll     $t2, $t2, 4
        addu    $t3, $t1, $t2       # pcsx_exit(679)
        lui     $t4, 0x1f80
        sh      $t3, 0x2082($t4)    # 16-bit store, as nugget's pcsx_exit
1:      b       1b

        .data
value:  .word   42
