/* Fixed native fork, host-read and loopback controls shared by both images. */
#ifndef CONTROL_PROBES_H
#define CONTROL_PROBES_H

#include <errno.h>
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
