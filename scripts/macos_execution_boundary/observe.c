/* Independent fixture identity observation; never a production containment API. */
#include <libproc.h>
#include <sys/proc_info.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    char *end = NULL;
    errno = 0;
    long value = strtol(argv[1], &end, 10);
    if (errno || !end || *end || value <= 1 || value > INT_MAX) return 2;
    struct proc_bsdinfo info = {0};
    int count = proc_pidinfo((int)value, PROC_PIDTBSDINFO, 0, &info, sizeof(info));
    if (count != sizeof(info)) return errno == ESRCH ? 1 : 3;
    printf("{\"pid\":%u,\"ppid\":%u,\"pgid\":%u,\"status\":%u,\"start_sec\":%llu,\"start_usec\":%llu}\n",
           info.pbi_pid, info.pbi_ppid, info.pbi_pgid, info.pbi_status,
           (unsigned long long)info.pbi_start_tvsec, (unsigned long long)info.pbi_start_tvusec);
    return 0;
}
