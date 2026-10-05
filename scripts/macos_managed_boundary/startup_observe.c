/* Independent fixture observation and kernel pid-version-bound signaling. */
#include <libproc.h>
#include <sys/proc_info.h>
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach/task_info.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <string.h>

static uint64_t monotonic_ns(void) {
    mach_timebase_info_data_t info;
    if (mach_timebase_info(&info) != KERN_SUCCESS) return 0;
    return (uint64_t)((__uint128_t)mach_absolute_time() * info.numer / info.denom);
}

static int token_for_pid(int pid, audit_token_t *token) {
    mach_port_t name = MACH_PORT_NULL;
    kern_return_t result = task_name_for_pid(mach_task_self(), pid, &name);
    if (result != KERN_SUCCESS) return 3;
    mach_msg_type_number_t count = TASK_AUDIT_TOKEN_COUNT;
    result = task_info(name, TASK_AUDIT_TOKEN, (task_info_t)token, &count);
    mach_port_deallocate(mach_task_self(), name);
    return result == KERN_SUCCESS && count == TASK_AUDIT_TOKEN_COUNT ? 0 : 3;
}

static int signal_token(int argc, char **argv) {
    if (argc != 10) return 2;
    audit_token_t token = {0};
    for (int index = 0; index < 8; index++) {
        char *end = NULL;
        errno = 0;
        unsigned long long value = strtoull(argv[index + 2], &end, 10);
        if (errno || !end || *end || argv[index + 2][0] == '-' || value > UINT32_MAX) return 2;
        token.val[index] = (uint32_t)value;
    }
    if (token.val[5] <= 1 || token.val[5] > INT_MAX || !token.val[7]) return 2;
    uint64_t before = monotonic_ns();
    if (!before) return 3;
    int error = proc_signal_with_audittoken(&token, SIGKILL);
    uint64_t after = monotonic_ns();
    if (error) return error == ESRCH ? 1 : 3;
    if (!after) return 3;
    printf("{\"before_ns\":%llu,\"after_ns\":%llu}\n", (unsigned long long)before, (unsigned long long)after);
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 2 && !strcmp(argv[1], "--signal")) return signal_token(argc, argv);
    if (argc != 2) return 2;
    char *end = NULL;
    errno = 0;
    long value = strtol(argv[1], &end, 10);
    if (errno || !end || *end || value <= 1 || value > INT_MAX) return 2;
    struct proc_bsdinfo info = {0};
    int count = proc_pidinfo((int)value, PROC_PIDTBSDINFO, 0, &info, sizeof(info));
    if (count != sizeof(info)) return errno == ESRCH ? 1 : 3;
    audit_token_t first = {0}, second = {0};
    if (token_for_pid((int)value, &first)) {
        count = proc_pidinfo((int)value, PROC_PIDTBSDINFO, 0, &info, sizeof(info));
        return count != sizeof(info) && errno == ESRCH ? 1 : 3;
    }
    count = proc_pidinfo((int)value, PROC_PIDTBSDINFO, 0, &info, sizeof(info));
    if (count != sizeof(info)) return errno == ESRCH ? 1 : 3;
    if (token_for_pid((int)value, &second)) {
        count = proc_pidinfo((int)value, PROC_PIDTBSDINFO, 0, &info, sizeof(info));
        return count != sizeof(info) && errno == ESRCH ? 1 : 3;
    }
    if (memcmp(&first, &second, sizeof(first)) || first.val[5] != value) return 3;
    printf("{\"pid\":%u,\"ppid\":%u,\"pgid\":%u,\"status\":%u,\"flags\":%u,\"start_sec\":%llu,\"start_usec\":%llu,\"audit_token\":[",
           info.pbi_pid, info.pbi_ppid, info.pbi_pgid, info.pbi_status, info.pbi_flags,
           (unsigned long long)info.pbi_start_tvsec, (unsigned long long)info.pbi_start_tvusec);
    for (int index = 0; index < 8; index++) printf("%s%u", index ? "," : "", first.val[index]);
    puts("]}");
    return 0;
}
