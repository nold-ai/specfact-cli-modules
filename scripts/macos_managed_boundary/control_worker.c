/* Fixed benign fixtures. No customer executable, pathname or grant is accepted. */
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

/* Same measured custom-profile ABI as startup_worker; unsupported production API. */
static int confine(void) {
    void *library = dlopen("/usr/lib/libsandbox.dylib", RTLD_NOW | RTLD_LOCAL);
    if (!library) return 20;
    typedef int (*init_function)(const char *, uint64_t, const char *const [], char **);
    init_function init = (init_function)dlsym(library, "sandbox_init_with_parameters");
    if (!init) return 21;
    const char *profile = "(version 1)(deny default)(allow signal (target self))";
    const char *params[] = {NULL};
    char *error = NULL;
    if (init(profile, 0, params, &error)) return 22;
    return 0;
}

static int probes(int denied) {
    pid_t child = fork();
    if (!child) _exit(0);
    if (denied) {
        if (child >= 0 || (errno != EPERM && errno != EACCES)) return 23;
    } else {
        int status;
        if (child < 0 || waitpid(child, &status, 0) != child || status != 0) return 24;
    }
    int fd = open("/etc/hosts", O_RDONLY);
    if (denied) {
        if (fd >= 0 || (errno != EPERM && errno != EACCES)) return 25;
    } else {
        if (fd < 0) return 26;
        close(fd);
    }
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        if (!denied || (errno != EPERM && errno != EACCES)) return 27;
    } else {
        struct sockaddr_in address = {.sin_len = sizeof(address), .sin_family = AF_INET,
            .sin_port = htons(9), .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
        int result = connect(fd, (struct sockaddr *)&address, sizeof(address));
        int saved = errno;
        close(fd);
        if (denied ? (result == 0 || (saved != EPERM && saved != EACCES)) : result != 0) return 28;
    }
    puts(denied ? "control-denials-ok" : "control-positive-ok");
    return fflush(stdout) ? 29 : 0;
}

int main(int argc, char **argv) {
    if (argc != 2 || strlen(argv[1]) != 1 || argv[1][0] < '0' || argv[1][0] > '5') return 2;
    int mode = argv[1][0] - '0';
    if (!mode) return probes(0);
    if (mode == 3) { for (;;) pause(); } /* launchd-owned trusted pretrace */
    if (ptrace(PT_TRACE_ME, 0, NULL, 0) || ptrace(PT_SIGEXC, 0, NULL, 0) || raise(SIGSTOP)) return 3;
    /* Only traced code can leave the launchd group or ignore termination. */
    if (mode == 2 && (setsid() < 0 || signal(SIGTERM, SIG_IGN) == SIG_ERR)) return 4;
    int result = confine();
    if (result) return result;
    result = probes(1);
    if (result) return result;
    puts("control-ready");
    if (fflush(stdout)) return 5;
    if (mode == 5) { raise(SIGTRAP); puts("runtime-trap-was-suppressed"); return 37; }
    if (mode == 1) { puts("control-fixture-output"); return 37; }
    for (;;) pause();
}
