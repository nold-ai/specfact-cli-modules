/* Benign trusted fixtures only; suspended startup is deliberately untraced. */
#include <signal.h>
#include <errno.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <limits.h>
#include <netinet/in.h>
#include <spawn.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <libproc.h>
#include <sys/proc_info.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <mach/mach_time.h>


extern char **environ;
typedef pid_t (*vfork_function)(void);
static vfork_function fixture_vfork;

/* Direct Darwin ARM64 syscall path; no Python or libc process interception. */
static pid_t raw_process_call(unsigned long number) {
    register unsigned long value __asm("x0") = 0;
    register unsigned long call __asm("x16") = number;
    register unsigned long child __asm("x1");
    unsigned int failed;
    __asm__ volatile("svc #0x80\n\tcset %w2, cs"
                     : "+r"(value), "=r"(child), "=r"(failed) : "r"(call) : "memory", "cc");
    if (failed) { errno = (int)value; return -1; }
    if (child != 0) _exit(0);
    return (pid_t)value;
}

static int child_result(pid_t child, int denied) {
    if (child == 0) _exit(0);
    if (child < 0) return denied && (errno == EPERM || errno == EACCES);
    int status;
    if (waitpid(child, &status, 0) != child) return 0;
    return !denied && WIFEXITED(status) && WEXITSTATUS(status) == 0;
}

static int probes(int denied) {
    char inherited = 0;
    ssize_t inherited_read = read(64, &inherited, 1);
    if (denied ? (inherited_read >= 0 || errno != EBADF) : (inherited_read != 1 || inherited != 'F')) return 32;
    if (!child_result(fork(), denied)) return 11;
    if (!child_result(fixture_vfork(), denied)) return 12;
    if (!child_result(raw_process_call(2), denied)) return 13;
    /* Raw vfork syscall availability is probed separately, never called fork denial. */
    pid_t child;
    char *args[] = {"/usr/bin/true", NULL};
    int error = posix_spawn(&child, args[0], NULL, NULL, args, environ);
    if (denied) { if (error != EPERM && error != EACCES) return 15; }
    else if (error || !child_result(child, 0)) return 16;
    int fd = open("allowed", O_RDONLY);
    if (fd < 0) return 17;
    char value = 0;
    if (read(fd, &value, 1) != 1 || value != 'A') return 18;
    close(fd);
    fd = open("forbidden", O_RDONLY);
    if (denied) { if (fd >= 0 || (errno != EPERM && errno != EACCES)) return 19; }
    else { if (fd < 0) return 20; close(fd); }
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        if (!denied || (errno != EPERM && errno != EACCES)) return 21;
    } else {
        struct sockaddr_in address = {.sin_len = sizeof(address), .sin_family = AF_INET,
            .sin_port = htons(9), .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
        int connected = connect(fd, (struct sockaddr *)&address, sizeof(address));
        int saved = errno;
        close(fd);
        if (denied ? (connected == 0 || (saved != EPERM && saved != EACCES)) : connected != 0) return 22;
    }
    int signalled = kill(getppid(), 0);
    if (denied ? (signalled == 0 || (errno != EPERM && errno != EACCES)) : signalled != 0) return 23;
    puts(denied ? "confinement-probes-ok" : "positive-probes-ok");
    fflush(stdout);
    return 0;
}

static int confine(const char *profile) {
    void *library = dlopen("/usr/lib/libsandbox.dylib", RTLD_NOW | RTLD_LOCAL);
    if (!library) return 24;
    typedef int (*init_function)(const char *, uint64_t, const char *const [], char **);
    init_function init = (init_function)dlsym(library, "sandbox_init_with_parameters");
    if (!init) return 25;
    char directory[PATH_MAX];
    if (!getcwd(directory, sizeof(directory))) return 26;
    const char *params[] = {"ROOT", directory, NULL};
    char *error = NULL;
    /* Only stdio observation streams are authorized fixture descriptors. */
    int length = proc_pidinfo(getpid(), PROC_PIDLISTFDS, 0, NULL, 0);
    if (length <= 0 || length > 65536) return 28;
    struct proc_fdinfo *fds = calloc(1, (size_t)length);
    if (!fds) return 29;
    int actual = proc_pidinfo(getpid(), PROC_PIDLISTFDS, 0, fds, length);
    if (actual <= 0 || actual > length || actual % sizeof(*fds)) { free(fds); return 30; }
    for (int index = 0; index < actual / (int)sizeof(*fds); index++) {
        if (fds[index].proc_fd >= 3) close(fds[index].proc_fd);
    }
    free(fds);
    if (init(profile, 0, params, &error)) {
        fprintf(stderr, "confinement setup failed: %s\n", error ? error : "unknown");
        return 27;
    }
    return probes(1);
}

static void fallback(void) {
    mach_timebase_info_data_t info;
    if (mach_timebase_info(&info) != KERN_SUCCESS) _exit(33);
    uint64_t now = (uint64_t)((__uint128_t)mach_absolute_time() * info.numer / info.denom);
    /* The observer rejects any measured window that can overlap this fallback. */
    alarm(60);
    printf("fallback-deadline=%llu\n", (unsigned long long)(now + 60000000000ULL));
    fflush(stdout);
}

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    if (!strcmp(argv[1], "raw-vfork-control")) {
        pid_t child = raw_process_call(66);
        return child_result(child, 0) ? 37 : 14;
    }
    if (!strcmp(argv[1], "after-exec-trap")) {
        raise(SIGTRAP);
        puts("runtime-trap-was-suppressed");
        return 37;
    }
    fixture_vfork = (vfork_function)dlsym(RTLD_DEFAULT, "vfork");
    if (!fixture_vfork) return 31;
    if (!strcmp(argv[1], "probe-control")) { int result = probes(0); return result ? result : 37; }
    if (!strcmp(argv[1], "normal")) { puts("managed-fixture-output"); return 37; }
    if (!strcmp(argv[1], "pretrace")) {
        fallback();
        puts("ready:pretrace"); fflush(stdout);
        for (;;) pause();
    }
    if (!strcmp(argv[1], "trace-stopped") || !strcmp(argv[1], "traced") || !strcmp(argv[1], "exec") || !strcmp(argv[1], "runtime-trap") || !strcmp(argv[1], "confined")) {
        if (ptrace(PT_TRACE_ME, 0, NULL, 0)) { perror("PT_TRACE_ME"); return 4; }
        if (raise(SIGSTOP)) return 5;
        if (!strcmp(argv[1], "exec") || !strcmp(argv[1], "runtime-trap")) {
            execl(argv[0], argv[0], !strcmp(argv[1], "exec") ? "after-exec" : "after-exec-trap", argv[2], (char *)NULL);
            perror("exec"); return 6;
        }
    } else if (strcmp(argv[1], "running") && strcmp(argv[1], "suspended") && strcmp(argv[1], "after-exec")) return 2;
    if (!strcmp(argv[1], "confined")) { int error = confine(argv[2]); if (error) return error; }
    if (signal(SIGTERM, SIG_IGN) == SIG_ERR) return 3;
    if (!strcmp(argv[1], "traced") || !strcmp(argv[1], "after-exec") || !strcmp(argv[1], "confined")) {
        if (setsid() < 0) return 7;
    }
    fallback();
    printf("ready:%s\n", !strcmp(argv[1], "after-exec") ? "exec" : argv[1]);
    fflush(stdout);
    /* A fallback for running controls; suspended children cannot execute it. */
    for (;;) pause();
}
