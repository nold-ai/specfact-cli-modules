/* Fixed native Semgrep fixture bootstrap; no customer command interface. */
#include <sys/ptrace.h>
#include <sys/proc_info.h>
#include <libproc.h>
#include <dlfcn.h>
#include <signal.h>
#include <errno.h>
#include <fcntl.h>
#include <spawn.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <limits.h>
#include <string.h>
#include <unistd.h>
#ifndef SF_CORE_PATH
#error SF_CORE_PATH must identify the digest-verified fixed native core
#endif
extern char **environ;

static int close_descriptors(void) {
    int size = proc_pidinfo(getpid(), PROC_PIDLISTFDS, 0, NULL, 0);
    if (size <= 0 || size > 65536) return 1;
    struct proc_fdinfo *fds = calloc(1, (size_t)size);
    if (!fds) return 1;
    int actual = proc_pidinfo(getpid(), PROC_PIDLISTFDS, 0, fds, size);
    if (actual <= 0 || actual > size || actual % sizeof(*fds)) { free(fds); return 1; }
    for (int index = 0; index < actual / (int)sizeof(*fds); index++)
        if (fds[index].proc_fd >= 3) close(fds[index].proc_fd);
    free(fds);
    return 0;
}

static int denied(int result) { return result < 0 && (errno == EPERM || errno == EACCES); }

static int profile_probes(char **environment) {
    int fd = open(SF_DENIED_PATH, O_RDONLY);
    if (!denied(fd)) { if (fd >= 0) close(fd); return 10; }
    char inherited = 0;
    if (read(64, &inherited, 1) >= 0 || errno != EBADF) return 11;
    pid_t child = fork();
    if (child == 0) _exit(0);
    if (!denied(child)) { if (child > 0) waitpid(child, NULL, 0); return 12; }
    char *args[] = {SF_CORE_PATH, NULL};
    int error = posix_spawn(&child, SF_CORE_PATH, NULL, NULL, args, environment);
    if (error != EPERM && error != EACCES) { if (!error) waitpid(child, NULL, 0); return 13; }
    if (!denied(kill(getppid(), 0))) return 14;
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) { if (!denied(fd)) return 15; }
    else {
        struct sockaddr_in address = {.sin_len = sizeof(address), .sin_family = AF_INET,
            .sin_port = htons(9), .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
        int result = connect(fd, (struct sockaddr *)&address, sizeof(address));
        int blocked = denied(result);
        close(fd);
        if (!blocked) return 16;
    }
    puts("sealed-profile-probes-ok"); fflush(stdout);
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 3 || strcmp(argv[1], "normal")) return 2;
    puts("sealed-phase:starting"); fflush(stdout);
    if (ptrace(PT_TRACE_ME, 0, NULL, 0) || raise(SIGSTOP)) return 3;
    puts("sealed-phase:traced"); fflush(stdout);
    char directory[PATH_MAX], home[PATH_MAX], temporary[PATH_MAX], ca[PATH_MAX];
    if (!getcwd(directory, sizeof(directory))) return 4;
    if (snprintf(home, sizeof(home), "%s/home", directory) >= (int)sizeof(home) ||
        snprintf(temporary, sizeof(temporary), "%s/tmp", directory) >= (int)sizeof(temporary) ||
        snprintf(ca, sizeof(ca), "%s/ca.pem", directory) >= (int)sizeof(ca)) return 4;
    char home_env[PATH_MAX + 8], tmp_env[PATH_MAX + 8], ca_env[PATH_MAX + 20];
    if (snprintf(home_env, sizeof(home_env), "HOME=%s", home) >= (int)sizeof(home_env) ||
        snprintf(tmp_env, sizeof(tmp_env), "TMPDIR=%s", temporary) >= (int)sizeof(tmp_env) ||
        snprintf(ca_env, sizeof(ca_env), "SSL_CERT_FILE=%s", ca) >= (int)sizeof(ca_env)) return 5;
    char *environment[] = {home_env, tmp_env, ca_env, "PATH=/nonexistent", "LANG=C", "SEMGREP_SEND_METRICS=off", NULL};
    puts("sealed-phase:environment"); fflush(stdout);
    void *library = dlopen("/usr/lib/libsandbox.dylib", RTLD_NOW | RTLD_LOCAL);
    if (!library) return 6;
    typedef int (*init_function)(const char *, uint64_t, const char *const [], char **);
    init_function init = (init_function)dlsym(library, "sandbox_init_with_parameters");
    if (!init || close_descriptors()) return 7;
    puts("sealed-phase:descriptors"); fflush(stdout);
    const char *params[] = {"ROOT", directory, "CORE", SF_CORE_PATH, "LIBS", SF_LIB_DIR, NULL};
    char *error = NULL;
    if (init(argv[2], 0, params, &error)) {
        fprintf(stderr, "confinement setup failed: %s\n", error ? error : "unknown");
        return 8;
    }
    puts("sealed-boundary-established"); fflush(stdout);
    int proof = profile_probes(environment);
    if (proof) return proof;
    char *args[] = {"osemgrep", "scan", "--experimental", "--oss-only", "--jobs=1", "--metrics=off",
        "--disable-version-check", "--novcs", "--no-git-ignore", "--project-root", directory,
        "--disable-nosem", "--json", "--config", "rules.yaml", "fixture.py", NULL};
    execve(SF_CORE_PATH, args, environment);
    perror("sealed core exec");
    return 9;
}
