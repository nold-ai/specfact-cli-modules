/* Deterministic request/timer logic; mock signaling never targets host PIDs. */
#define CONTROL_BSD_TEST 1
#define FIXED_WORKER "/unused-fixed-worker"
#define WORKER_REQUIREMENT "false"
#define main broker_fixture_main
#define kill fixture_signal
#include "control_broker.c"
#undef main
#undef kill

static int signals_sent;
int fixture_signal(pid_t pid, int signal_number) {
    (void)pid;
    (void)signal_number;
    signals_sent++;
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    int mode = atoi(argv[1]);
    if (mode < 1 || mode > 3) return 2;
    authenticated = 1;
    worker_count = 1;
    session_deadline = now() + 30;
    workers[0] = (struct worker){.pid = 1234567, .handle = 1,
        .deadline = now() - 1, .reason = "completed", .fd = -1};
    input[4] = 1;
    input[5] = mode == 1 ? 4 : 3;
    input[15] = 1;  /* big-endian handle */
    input[19] = mode == 3 ? SIGTERM : mode == 2 ? SIGKILL : 0;
    request();
    expire_workers(now(), session_deadline);
    const char *reason = mode == 1 ? "cancel" : mode == 2 ? "signal" : "timeout";
    int expected_signals = mode == 3 ? 2 : 1;
    if (strcmp(workers[0].reason, reason) || signals_sent != expected_signals) return 3;
    return 0;
}
