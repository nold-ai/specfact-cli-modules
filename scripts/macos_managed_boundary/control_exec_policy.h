/* Kernel ownership is checked before this policy; image comes from dynamic validation. */
#include <signal.h>
enum exec_action { EXEC_REJECT = -1, EXEC_FORWARD = 0, EXEC_ADMIT = 1 };
static enum exec_action exec_transition(int intent, int admitted, int signal, int image) {
    if (!intent || admitted || signal != SIGTRAP) return EXEC_FORWARD;
    if (image == 0) return EXEC_FORWARD; /* Recognized bootstrap: a genuine trap. */
    if (image != 1) return EXEC_REJECT;
    return EXEC_ADMIT;
}
