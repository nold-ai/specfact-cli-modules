/* Contract: complete private snapshots on launch, accepted wait, terminal reap,
 * EOF and completed wait; stopped/transient/rejected paths emit no false terminal
 * evidence. No policy change or payload/status/authority data in these snapshots.
 * Include the real broker; no child is spawned or host PID signalled by this test. */
#include <setjmp.h>
#define FIXED_WORKER "/unused-fixed-worker"
#define WORKER_REQUIREMENT "false"
#define main broker_fixture_main
#define posix_spawn fixture_spawn
#define waitpid fixture_waitpid
#define ptrace fixture_ptrace
#define read fixture_read
#define select fixture_select
#define kill fixture_signal
#define clock_gettime fixture_clock_gettime
#define SecStaticCodeCreateWithPath fixture_code
#define SecRequirementCreateWithString fixture_requirement
#define SecStaticCodeCheckValidity fixture_validity
#include "control_broker.c"
#undef main
#undef posix_spawn
#undef waitpid
#undef ptrace
#undef read
#undef select
#undef kill
#undef clock_gettime
#undef SecStaticCodeCreateWithPath
#undef SecRequirementCreateWithString
#undef SecStaticCodeCheckValidity

static jmp_buf loop_done;
static int next_status, status_ready, wait_interrupt, read_error, continuations;
static int last_signal, signals_sent, reconcile_mode, select_calls;

int fixture_clock_gettime(clockid_t clock, struct timespec *value) {
    if (clock != CLOCK_MONOTONIC) _exit(94);
    value->tv_sec = 100; value->tv_nsec = 0;
    return 0;
}

OSStatus fixture_code(CFURLRef url, SecCSFlags flags, SecStaticCodeRef *code) {
    (void)url; (void)flags;
    *code = NULL;
    return errSecSuccess;
}
OSStatus fixture_requirement(CFStringRef text, SecCSFlags flags, SecRequirementRef *requirement) {
    (void)text; (void)flags;
    *requirement = NULL;
    return errSecSuccess;
}
OSStatus fixture_validity(SecStaticCodeRef code, SecCSFlags flags, SecRequirementRef requirement) {
    (void)code; (void)flags; (void)requirement;
    return errSecSuccess;
}
int fixture_spawn(pid_t *pid, const char *path, const posix_spawn_file_actions_t *actions,
    const posix_spawnattr_t *attributes, char *const args[], char *const environment[]) {
    (void)path; (void)actions; (void)attributes; (void)args; (void)environment;
    *pid = 1234567 + worker_count;
    return 0;
}
pid_t fixture_waitpid(pid_t pid, int *status, int options) {
    if (options != (WNOHANG | WUNTRACED)) _exit(90);
    if (wait_interrupt) { wait_interrupt = 0; errno = EINTR; return -1; }
    if (!status_ready) return 0;
    status_ready = 0;
    *status = next_status;
    return pid;
}
int fixture_ptrace(int operation, pid_t pid, caddr_t address, int signal_number) {
    (void)pid;
    if (operation != PT_CONTINUE || address != (caddr_t)1) _exit(91);
    continuations++;
    last_signal = signal_number;
    return 0;
}
ssize_t fixture_read(int fd, void *buffer, size_t size) {
    (void)fd; (void)buffer; (void)size;
    if (read_error) { errno = read_error; read_error = 0; return -1; }
    return 0;
}
int fixture_select(int count, fd_set *reads, fd_set *writes, fd_set *errors, struct timeval *timeout) {
    (void)count; (void)errors;
    if (reconcile_mode) {
        double delay = timeout->tv_sec + timeout->tv_usec / 1e6;
        int active = 0;
        for (int i = 0; i < worker_count; i++) if (!workers[i].reaped) active = 1;
        if ((active && delay > 0.050001) || (!active && delay < 1)) _exit(93);
        if (reconcile_mode == 6 && delay > 0.010001) _exit(95);
        if (reconcile_mode == 4 && select_calls++ < 2) {
            FD_ZERO(reads); FD_ZERO(writes); /* No signal-handler pipe byte. */
            status_ready = 1;
            next_status = select_calls == 1 ? W_STOPCODE(SIGKILL) : SIGKILL;
            if (select_calls == 2) FD_SET(workers[0].fd, reads);
            return select_calls == 2 ? 1 : 0; /* Status wake, then output EOF. */
        }
    }
    longjmp(loop_done, 1); /* Inspect one actual loop completion, without blocking. */
}
int fixture_signal(pid_t pid, int signal_number) {
    (void)pid; (void)signal_number;
    signals_sent++;
    return 0;
}

static void control_request(unsigned char opcode, uint64_t handle) {
    memset(input, 0, sizeof(input));
    input[4] = 1;
    input[5] = opcode;
    for (int i = 0; i < 8; i++) input[8 + i] = (unsigned char)(handle >> (56 - i * 8));
    memcpy(input + 24, capability, sizeof(capability));
    request();
}
static void wait_request(uint64_t handle) { control_request(2, handle); }
static void terminal_reap(void) {
    next_status = SIGKILL;
    status_ready = 1;
    reap();
}
static void complete_wait(void) {
    client = 100;
    if (!setjmp(loop_done)) loop(101);
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "reconcile-empty")) {
        reconcile_mode = 1;
        complete_wait();
        return worker_count == 0 ? 0 : 12;
    }
    authenticated = 1;
    memset(capability, 's', sizeof(capability));
    launch(!strcmp(argv[1], "held-stop") || !strcmp(argv[1], "reconcile-held") ? 4 : 2, 5000);
    if (worker_count != 1 || workers[0].pid != 1234567) return 3;
    struct worker *item = &workers[0];
    item->handle = 1;
    strcpy(item->output, "private-worker-payload");
    item->used = strlen(item->output);
    item->reason = "private-reason";

    if (!strncmp(argv[1], "reconcile-", 10)) {
        if (!strcmp(argv[1], "reconcile-reaped")) {
            terminal_reap(); drain(item); reconcile_mode = 2;
        } else if (!strcmp(argv[1], "reconcile-active")) reconcile_mode = 3;
        else if (!strcmp(argv[1], "reconcile-earlier")) {
            item->deadline = now() + 0.01; reconcile_mode = 6;
        }
        else if (!strcmp(argv[1], "reconcile-lost")) {
            item->traced = 1; session_deadline = now() + 30;
            control_request(4, item->handle); /* Real cancellation handling. */
            output_sent = output_used = 0; /* Client consumed launch/cancel replies. */
            reconcile_mode = 4;
        } else if (!strcmp(argv[1], "reconcile-later")) {
            terminal_reap(); drain(item); launch(2, 5000);
            workers[1].handle = 2; reconcile_mode = 7;
        } else if (!strcmp(argv[1], "reconcile-held")) {
            next_status = W_STOPCODE(SIGSTOP); status_ready = 1; reap(); reconcile_mode = 5;
        } else return 13;
        wait_request(reconcile_mode == 7 ? 2 : 1); complete_wait();
        if (reconcile_mode == 4) {
            uint32_t size; memcpy(&size, output, sizeof(size));
            size_t length = ntohl(size);
            if (length > 2048 || output_used != length + 4) return 16;
            char reply[2049]; memcpy(reply, output + 4, length); reply[length] = 0;
            if (!strstr(reply, "\"state\":\"exited\"") || !strstr(reply, "\"signal\":9,") ||
                !strstr(reply, "\"reason\":\"cancel\"") || !strstr(reply, "private-worker-payload")) return 17;
            return pending == -1 && item->reaped && item->fd < 0 &&
                continuations == 1 && last_signal == SIGKILL && signals_sent == 1 ? 0 : 14;
        }
        if (reconcile_mode == 7 && (pending != 1 || workers[1].reaped)) return 18;
        return signals_sent == 0 && continuations == 0 ? 0 : 15;
    }
    if (!strcmp(argv[1], "launch")) return 0;
    if (!strcmp(argv[1], "rejected")) {
        wait_request(99);
        wait_request(1);
        wait_request(1); /* Rejected wait-limit must not emit acceptance. */
        return pending == 0 ? 0 : 4;
    }
    if (!strcmp(argv[1], "immediate")) {
        terminal_reap();
        drain(item);
        wait_request(1);
        return pending == -1 ? 0 : 5;
    }
    if (!strcmp(argv[1], "stopped") || !strcmp(argv[1], "held-stop")) {
        next_status = W_STOPCODE(SIGSTOP);
        status_ready = 1;
        reap();
        wait_request(1);
        int expected = item->mode == 4 ? 0 : 1;
        if (item->reaped || continuations != expected || last_signal) return 6;
        if (expected) {
            next_status = W_STOPCODE(SIGTRAP);
            status_ready = 1;
            reap();
            if (continuations != 2 || last_signal != SIGTRAP || item->reaped) return 7;
        }
        return 0;
    }
    if (!strcmp(argv[1], "bounds")) {
        for (int i = 1; i < WORKERS; i++) launch(2, 5000);
        launch(2, 5000); /* Existing worker limit; no extra snapshot. */
        for (int i = 0; i < WORKERS; i++) {
            status_ready = 1;
            next_status = SIGKILL;
            reap();
            drain(&workers[i]);
        }
        for (int i = 0; i < 64; i++) {
            output_sent = output_used = 0; /* Simulate the client consuming replies. */
            wait_request(1);
        }
        return worker_count == WORKERS && requests == 64 && signals_sent == 0 ? 0 : 8;
    }
    wait_request(1);
    if (!strcmp(argv[1], "pending")) {
        reap(); reap();
        read_error = EAGAIN;
        drain(item);
        return pending == 0 && !item->reaped ? 0 : 9;
    }
    if (!strcmp(argv[1], "eof-first")) {
        drain(item);
        terminal_reap();
    } else if (!strcmp(argv[1], "reap-first") || !strcmp(argv[1], "transient")) {
        wait_interrupt = !strcmp(argv[1], "transient");
        terminal_reap();
        if (!strcmp(argv[1], "transient")) {
            read_error = EAGAIN; drain(item);
            read_error = EINTR; drain(item);
        }
        drain(item);
    } else return 10;
    complete_wait();
    return pending == -1 && item->reaped && item->fd == -1 && signals_sent == 0 ? 0 : 11;
}
