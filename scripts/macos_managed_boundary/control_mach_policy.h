/* Pure admission checks shared by the real decoder and safe native unit fixture. */
#include <mach/exception_types.h>
#include <signal.h>
static int owned_signal(pid_t child, int reaped, pid_t sender, pid_t task,
    exception_type_t exception, const int64_t *code, unsigned int count) {
    return child > 1 && !reaped && sender == 0 && task == child &&
        exception == EXC_SOFTWARE && count == 2 && code[0] == EXC_SOFT_SIGNAL &&
        code[1] > 0 && code[1] < NSIG;
}
