/* The first harness test: printf through the BIOS and a clean exit. */
#include "bench.h"

int main(void) {
    ramsyscall_printf("hello, PS1\n");
    ramsyscall_printf("6 * 7 = %d\n", 6 * 7);
    bench_exit(0);
}
