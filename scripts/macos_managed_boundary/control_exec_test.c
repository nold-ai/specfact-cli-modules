/* Safe policy transitions only: no live PID, process signal or task-control operation. */
#include <string.h>
#include "control_exec_policy.h"
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    int intent = 1, admitted = 0, number = SIGTRAP, image = 1;
    enum exec_action expected = EXEC_ADMIT;
    if (!strcmp(argv[1], "admit-image")) {}
    else if (!strcmp(argv[1], "genuine-bootstrap-trap")) { image = 0; expected = EXEC_FORWARD; }
    else if (!strcmp(argv[1], "genuine-target-trap")) { admitted = 1; expected = EXEC_FORWARD; }
    else if (!strcmp(argv[1], "no-exec-intent")) { intent = 0; expected = EXEC_FORWARD; }
    else if (!strcmp(argv[1], "wrong-image")) { image = -1; expected = EXEC_REJECT; }
    else if (!strcmp(argv[1], "wrong-signal")) { number = SIGTERM; expected = EXEC_FORWARD; }
    else if (!strcmp(argv[1], "duplicate-handoff")) { admitted = 1; expected = EXEC_FORWARD; }
    else return 2;
    return exec_transition(intent, admitted, number, image) == expected ? 0 : 3;
}
