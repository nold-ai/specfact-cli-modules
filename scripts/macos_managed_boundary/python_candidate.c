/* Build-owned CPython fixture bootstrap; no worker-selected paths or policy. */
#include <dlfcn.h>
#include <errno.h>
#include <signal.h>
#include <spawn.h>
#include <sys/wait.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ptrace.h>
#include <unistd.h>
#include "python_candidate_policy.h"

#ifndef FIXED_TARGET
#error "FIXED_TARGET must bind the prepared, signed CPython image"
#endif

typedef int (*sandbox_init_fn)(const char *, uint64_t, const char *const [], char **);

int main(int argc, char **argv) {
    if (argc != 2) return 2;
#ifndef CANDIDATE_FIXED_ARGV
    const char *script = NULL;
    if (!strcmp(argv[1], "6")) script = PYTHON_CLEAN;
    else if (!strcmp(argv[1], "7")) script = PYTHON_DEFECTIVE;
    else if (!strcmp(argv[1], "8")) script = PYTHON_REEXEC;
    else if (!strcmp(argv[1], "10")) script = PYTHON_DENIALS;
    else if (!strcmp(argv[1], "11")) script = PYTHON_CLEAN; /* Broker holds replacement. */
    else if (!strcmp(argv[1], "12")) script = PYTHON_TRAP;
    else return 2;
#else
    if (strcmp(argv[1], "6")) return 2;
#endif
    if (ptrace(PT_TRACE_ME, 0, NULL, 0) ||
        ptrace(PT_SIGEXC, 0, NULL, 0) || raise(SIGSTOP)) return 3;
    void *library = dlopen("/usr/lib/libsandbox.dylib", RTLD_NOW | RTLD_LOCAL);
    if (!library) return 20;
    sandbox_init_fn init = (sandbox_init_fn)dlsym(library, "sandbox_init_with_parameters");
    if (!init) return 21;
    const char *params[] = {NULL};
    char *error = NULL;
    if (init(PYTHON_PROFILE, 0, params, &error)) {
        fprintf(stderr, "candidate-profile-failure: %.768s\n", error ? error : "unknown");
        return 22;
    }
#ifdef CANDIDATE_FIXED_ARGV
    char *args[] = CANDIDATE_FIXED_ARGV;
    char *environment[] = CANDIDATE_FIXED_ENV;
    if (chdir(CANDIDATE_CWD) || !freopen(CANDIDATE_STDOUT, "w", stdout) ||
        !freopen(CANDIDATE_STDERR, "w", stderr)) return 40;
#ifdef CANDIDATE_ASSERT_PROCESS_DENIED
    errno = 0;
    pid_t forbidden = fork();
    if (forbidden == 0) _exit(44);
    if (forbidden > 0) {
        kill(forbidden, SIGKILL);
        waitpid(forbidden, NULL, 0);
        return 44;
    }
    if (errno != EPERM) return 44;
    pid_t spawned = -1;
    int spawn_error = posix_spawn(&spawned, FIXED_TARGET, NULL, NULL, args, environment);
    if (!spawn_error) {
        kill(spawned, SIGKILL);
        waitpid(spawned, NULL, 0);
        return 45;
    }
    if (spawn_error != EPERM) return 45;
    fprintf(stderr, "candidate-process-denial=fork:EPERM,spawn:EPERM\n");
#endif
    errno = 0;
    long page_size = sysconf(_SC_PAGESIZE);
    fprintf(stderr, "candidate-page-size=%ld errno=%d getpagesize=%d\n", page_size, errno, getpagesize());
    if (fflush(stderr)) return 41;
#else
    char *args[] = {FIXED_TARGET, "-I", "-S", "-B", (char *)script, NULL};
    char *environment[] = {"PATH=/usr/bin:/bin", "LANG=C", "LC_ALL=C", NULL};
#endif
    execve(FIXED_TARGET, args, environment);
    return 39;
}
