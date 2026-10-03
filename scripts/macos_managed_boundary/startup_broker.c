/* Fixed startup fixture broker; never accepts customer code or launch requests. */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <sys/ptrace.h>
#include <unistd.h>

extern char **environ;

int main(int argc, char **argv) {
    if (argc != 4 || argv[1][0] != '/') return 2;
    int suspended = strcmp(argv[2], "suspended") == 0;
    if (!suspended && strcmp(argv[2], "running") && strcmp(argv[2], "normal") &&
        strcmp(argv[2], "pretrace") && strcmp(argv[2], "trace-stopped") &&
        strcmp(argv[2], "traced") && strcmp(argv[2], "exec") &&
        strcmp(argv[2], "confined") && strcmp(argv[2], "runtime-trap") && strcmp(argv[2], "probe-control") && strcmp(argv[2], "raw-vfork-control")) return 2;
    posix_spawnattr_t attr;
    if (posix_spawnattr_init(&attr)) return 3;
    if (suspended && posix_spawnattr_setflags(&attr, POSIX_SPAWN_START_SUSPENDED)) return 3;
    posix_spawn_file_actions_t actions;
    if (posix_spawn_file_actions_init(&actions)) return 10;
    if (posix_spawn_file_actions_addopen(&actions, 64, "forbidden", O_RDONLY, 0)) return 10;
    char *args[] = {argv[1], argv[2], argv[3], NULL};
    pid_t worker = 0;
    int error = posix_spawn(&worker, argv[1], &actions, &attr, args, environ);
    posix_spawnattr_destroy(&attr);
    posix_spawn_file_actions_destroy(&actions);
    if (error) { fprintf(stderr, "spawn errno=%d\n", error); return 4; }
    printf("{\"broker\":%d,\"worker\":%d,\"pgid\":%d}\n", getpid(), worker, getpgrp());
    fflush(stdout);
    int status = 0;
    pid_t waited;
    int startup_stop = 0, exec_stop = 0;
    int expects_exec = !strcmp(argv[2], "exec") || !strcmp(argv[2], "normal") || !strcmp(argv[2], "runtime-trap");
    for (;;) {
        do { waited = waitpid(worker, &status, WUNTRACED); } while (waited < 0 && errno == EINTR);
        if (waited != worker || !WIFSTOPPED(status)) break;
        if (!strcmp(argv[2], "suspended")) { for (;;) pause(); }
        int stopped = WSTOPSIG(status);
        int control_stop = (stopped == SIGSTOP && !startup_stop) ||
            (stopped == SIGTRAP && startup_stop && !exec_stop && expects_exec);
        if (!control_stop) {
            fprintf(stderr, "forwarding-worker-signal=%d\n", WSTOPSIG(status));
            if (ptrace(PT_CONTINUE, worker, (caddr_t)1, WSTOPSIG(status))) return 8;
            continue;
        }
        if (stopped == SIGSTOP) startup_stop = 1;
        else exec_stop = 1;
        printf("trace-confirmed:%s\n", argv[2]);
        fflush(stdout);
        if (!strcmp(argv[2], "trace-stopped")) { for (;;) pause(); }
        if (ptrace(PT_CONTINUE, worker, (caddr_t)1, 0)) return 9;
    }
    if (waited != worker) return 5;
    if (!WIFEXITED(status)) { printf("worker-signal=%d\n", WTERMSIG(status)); fflush(stdout); return 6; }
    printf("worker-exit=%d\n", WEXITSTATUS(status));
    fflush(stdout);
    return WEXITSTATUS(status) == 37 ? 0 : 7;
}
