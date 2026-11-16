        .set noreorder
        .text
        .globl _start
_start:
        la      $s0, msg
1:      lbu     $a0, 0($s0)
        nop
        beqz    $a0, 2f
        addiu   $s0, $s0, 1
        li      $t1, 0x3c          # A(0x3C) putchar
        li      $t0, 0xa0
        jalr    $t0
        nop
        b       1b
        nop
2:      li      $t0, 42            # pcsx_exit(42)
        lui     $t1, 0x1f80
        sh      $t0, 0x2082($t1)   # 16-bit store, as nugget's pcsx_exit
3:      b       3b
        nop
        .data
msg:    .asciz  "hello from asm\n"
