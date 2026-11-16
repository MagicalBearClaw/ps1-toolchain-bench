/* Helpers for ps1bench tests. */
#pragma once

#include "common/hardware/pcsxhw.h"
#include "common/syscalls/syscalls.h"

/* End the test: PCSX-Redux (-testmode) exits with this code. */
static inline __attribute__((noreturn)) void bench_exit(int code) {
    pcsx_exit(code);
    for (;;) {
    }
}
