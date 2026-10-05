/* Fixed native fork, host-read and loopback controls shared by both images. */
#ifndef CONTROL_PROBES_H
#define CONTROL_PROBES_H

#include <dlfcn.h>
#include <errno.h>
#include <mach/mach.h>
#include <spawn.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <stdio.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

static int control_wait_child(pid_t child) {
    int status;
    pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
    return waited == child && WIFEXITED(status) && WEXITSTATUS(status) == 0;
}

/* Exercise Darwin ARM64 syscall creation without libc interception. */
static pid_t control_raw_fork(void) {
    register unsigned long value __asm("x0") = 0;
    register unsigned long call __asm("x16") = 2;
    register unsigned long child __asm("x1");
    unsigned int failed;
    __asm__ volatile("svc #0x80\n\tcset %w2, cs"
        : "+r"(value), "=r"(child), "=r"(failed) : "r"(call) : "memory", "cc");
    if (failed) { errno = (int)value; return -1; }
    if (child != 0) _exit(0);
    return (pid_t)value;
}
static int control_creation(pid_t child, int denied) {
    int saved = errno;
    if (!child) _exit(0);
    if (child > 0) return control_wait_child(child) && !denied;
    return denied && (saved == EPERM || saved == EACCES);
}

static int control_probes(int denied, const char *marker) {
    pid_t child = fork();
    int saved = errno;
    if (!child) _exit(0);
    if (denied) {
        /* Reap only this directly owned child if creation unexpectedly succeeds.
         * It exits immediately; never signal a possibly recycled PID. */
        if (child > 0) { (void)control_wait_child(child); return 23; }
        if (child >= 0 || (saved != EPERM && saved != EACCES)) return 23;
    } else {
        if (child < 0 || !control_wait_child(child)) return 24;
    }
    typedef pid_t (*vfork_function)(void);
    vfork_function direct_vfork = (vfork_function)dlsym(RTLD_DEFAULT, "vfork");
    if (!direct_vfork || !control_creation(direct_vfork(), denied) ||
        !control_creation(control_raw_fork(), denied)) return 23;
    char *arguments[] = {"/usr/bin/true", NULL}, *environment[] = {NULL};
    int spawned = posix_spawn(&child, arguments[0], NULL, NULL, arguments, environment);
    if (denied) {
        if (!spawned) { (void)control_wait_child(child); return 23; }
        if (spawned != EPERM && spawned != EACCES) return 23;
    } else if (spawned || !control_wait_child(child)) return 24;
    mach_port_t own_task = MACH_PORT_NULL, broker_task = MACH_PORT_NULL;
    if (!denied) {
        if (task_for_pid(mach_task_self(), getpid(), &own_task) || !own_task) return 24;
        mach_port_deallocate(mach_task_self(), own_task);
    }
    if (denied) {
        int result = task_for_pid(mach_task_self(), getppid(), &broker_task);
        if (!result || broker_task) {
            if (broker_task) mach_port_deallocate(mach_task_self(), broker_task);
            return 25;
        }
        int signalled = kill(getppid(), 0);
        if (!signalled || (errno != EPERM && errno != EACCES)) return 25;
    }
    int fd = open("/etc/hosts", O_RDONLY);
    saved = errno;
    if (denied) {
        if (fd >= 0) { close(fd); return 25; }
        if (saved != EPERM && saved != EACCES) return 25;
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
        saved = errno;
        close(fd);
        if (denied ? (result == 0 || (saved != EPERM && saved != EACCES)) : result != 0) return 28;
    }
    puts(marker);
    return fflush(stdout) ? 29 : 0;
}

#endif
