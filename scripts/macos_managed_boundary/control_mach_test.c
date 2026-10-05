/* No host signals or task ports: exercise real admission arithmetic only. */
#include <stdint.h>
#include <string.h>
#include <sys/types.h>
#include "control_mach_policy.h"
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    pid_t sender = 0, child = 1234567, task = child;
    int reaped = 0, accepted = 0;
    exception_type_t exception = EXC_SOFTWARE;
    unsigned int count = 2;
    int64_t code[] = {EXC_SOFT_SIGNAL, SIGSTOP};
    if (!strcmp(argv[1], "initial")) accepted = 1;
    else if (!strcmp(argv[1], "runtime")) { code[1] = SIGKILL; accepted = 1; }
    else if (!strcmp(argv[1], "foreign-sender")) sender = child;
    else if (!strcmp(argv[1], "foreign-child")) task++;
    else if (!strcmp(argv[1], "wrong-kind")) exception = EXC_BAD_ACCESS;
    else if (!strcmp(argv[1], "short-code")) count = 1;
    else if (!strcmp(argv[1], "bad-signal")) code[1] = NSIG;
    else if (!strcmp(argv[1], "reaped")) reaped = 1;
    else return 2;
    return owned_signal(child, reaped, sender, task, exception, code, count) == accepted ? 0 : 3;
}
