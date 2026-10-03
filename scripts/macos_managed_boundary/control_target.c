/* Fixed replacement image; confinement is inherited, never installed here. */
#include <inttypes.h>
#include <signal.h>
#include <string.h>
#include <time.h>
#include "control_probes.h"

__attribute__((constructor)) static void target_initializer(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) _exit(30);
    uint64_t ns = (uint64_t)now.tv_sec * UINT64_C(1000000000) + (uint64_t)now.tv_nsec;
    if (printf("target-initializer-ns=%" PRIu64 "\n", ns) < 0 || fflush(stdout)) _exit(31);
}

int main(int argc, char **argv) {
    if (argc != 2 || strlen(argv[1]) != 1 || argv[1][0] < '0' || argv[1][0] > '4') return 2;
    int mode = argv[1][0] - '0';
    if (!mode) return control_probes(0, "target-positive-ok");
    int result = control_probes(1, "target-denials-ok");
    if (result) return result;
    puts("target-entry");
    if (fflush(stdout)) return 5;
    if (mode == 1) return 37;
    if (mode == 2) {
        if (signal(SIGTRAP, SIG_DFL) == SIG_ERR || raise(SIGTRAP)) return 3;
        puts("target-trap-was-suppressed");
        return fflush(stdout) ? 5 : 37;
    }
    if (mode == 4) {
        puts("target-second-exec");
        if (fflush(stdout)) return 5;
        /* argv[0] is the compiled fixed target supplied by the trusted worker.
         * The broker must deliver the second exec trap before initializers. */
        execl(argv[0], argv[0], "1", (char *)NULL);
        return 39;
    }
    if (setsid() < 0 || signal(SIGTERM, SIG_IGN) == SIG_ERR) return 4;
    puts("target-ready");
    if (fflush(stdout)) return 5;
    for (;;) pause();
}
