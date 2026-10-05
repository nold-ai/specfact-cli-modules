/* Bounded, benign lifecycle probe. Reports are hints for an independent observer. */
#include <errno.h>
#include <inttypes.h>
#include <libproc.h>
#include <mach-o/dyld.h>
#include <signal.h>
#include <spawn.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/proc_info.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

static double monotonic_seconds(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) _exit(70);
    return (double)now.tv_sec + (double)now.tv_nsec / 1e9;
}

static void report(const char *event, const char *role, int error) {
    struct proc_bsdinfo info = {0};
    int bytes = proc_pidinfo(getpid(), PROC_PIDTBSDINFO, 0, &info, sizeof(info));
    bool birth_known = bytes == (int)sizeof(info);
    char line[640];
    int length = snprintf(line, sizeof(line),
        "{\"version\":1,\"event\":\"%s\",\"role\":\"%s\",\"pid\":%d,"
        "\"ppid\":%d,\"pgid\":%d,\"sid\":%d,\"birth_known\":%s,"
        "\"birth_sec\":%" PRIu64 ",\"birth_usec\":%" PRIu64 ",\"errno\":%d}\n",
        event, role, getpid(), getppid(), getpgrp(), getsid(0),
        birth_known ? "true" : "false", info.pbi_start_tvsec, info.pbi_start_tvusec, error);
    if (length > 0 && (size_t)length < sizeof(line)) {
        ssize_t written;
        do { written = write(STDOUT_FILENO, line, (size_t)length); }
        while (written < 0 && errno == EINTR);
    }
}

static int live(const char *role, double deadline, pid_t child) {
    report("ready", role, 0);
    while (monotonic_seconds() < deadline) {
        report("heartbeat", role, 0);
        struct timespec delay = {.tv_sec = 0, .tv_nsec = 100000000};
        while (nanosleep(&delay, &delay) != 0 && errno == EINTR) {}
        if (child > 0 && waitpid(child, NULL, WNOHANG) == child) child = -1;
    }
    report("exit", role, 0);
    return 0;
}

static int detached(double deadline) {
    if (setsid() < 0) { report("error", "child", errno); return 71; }
    return live("child", deadline, -1);
}

int main(int argc, char **argv) {
    signal(SIGPIPE, SIG_IGN);
    /* Also bounds a blocked stdout write; intentionally inherited through exec. */
    alarm(15);
    double deadline = monotonic_seconds() + 15.0;
    if (argc != 2) { report("error", "root", EINVAL); return 64; }
    const char *mode = argv[1];
    if (strcmp(mode, "exec-child") == 0) return detached(deadline);
    if (strcmp(mode, "normal") == 0) return live("root", monotonic_seconds() + 0.3, -1);
    bool fork_mode = strcmp(mode, "child") == 0 || strcmp(mode, "fork-detach") == 0;
    bool double_fork = strcmp(mode, "double-fork") == 0;
    bool spawn_mode = strcmp(mode, "spawn-detach") == 0;
    bool vfork_mode = strcmp(mode, "vfork-detach") == 0;
    if (!fork_mode && !double_fork && !spawn_mode && !vfork_mode) {
        report("error", "root", EINVAL); return 64;
    }
    pid_t child = -1;
    if (fork_mode || double_fork) {
        child = fork();
        if (child == 0) {
            alarm(15); /* fork does not inherit the parent's alarm. */
            if (double_fork) {
                report("ready", "intermediate", 0);
                if (setsid() < 0) { report("error", "intermediate", errno); _exit(71); }
                pid_t grandchild = fork();
                if (grandchild < 0) { report("error", "intermediate", errno); _exit(71); }
                if (grandchild > 0) _exit(0);
                alarm(15);
                return live("child", deadline, -1);
            }
            if (strcmp(mode, "fork-detach") == 0) return detached(deadline);
            return live("child", deadline, -1);
        }
        if (child < 0) { report("error", "root", errno); return 71; }
    } else {
        char executable[4096];
        uint32_t size = sizeof(executable);
        if (_NSGetExecutablePath(executable, &size) != 0) {
            report("error", "root", ENAMETOOLONG); return 71;
        }
        char *child_argv[] = {executable, "exec-child", NULL};
        char **child_env = environ;
        if (spawn_mode) {
            int error = posix_spawn(&child, executable, NULL, NULL, child_argv, child_env);
            if (error != 0) { report("error", "root", error); return 71; }
        } else {
            /* Everything needed by the child is prepared before vfork. */
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
            child = vfork();
#pragma clang diagnostic pop
            if (child == 0) { execve(executable, child_argv, child_env); _exit(127); }
            if (child < 0) { report("error", "root", errno); return 71; }
        }
    }
    return live("root", deadline, child);
}
