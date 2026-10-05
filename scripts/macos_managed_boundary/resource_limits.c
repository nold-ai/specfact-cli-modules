/* Bounded maintainer probes, never production resource admission. */
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/event.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <spawn.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <dlfcn.h>
#include <libproc.h>
#include <sys/proc_info.h>
#include <limits.h>

#define MIB (1024ULL * 1024ULL)
#if !defined(RESOURCE_OBSERVER) && !defined(RESOURCE_CONTROL_TEST)
static double seconds(clockid_t clock) {
    struct timespec time;
    if (clock_gettime(clock, &time)) _exit(90);
    return time.tv_sec + time.tv_nsec / 1e9;
}

#endif

#ifdef RESOURCE_CONTROL_TEST
#include "control_resource.h"
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    int limited = !strcmp(argv[1], "limited");
    if (!limited && strcmp(argv[1], "control")) return 2;
    int file = open(argv[2], O_RDWR | O_CREAT | O_EXCL, 0600);
    if (file < 0) return 3;
    struct control_resource_state state = {0};
    if (limited && (control_resource_configure(&state) || control_resource_verify(&state, 0))) return 70;
    int descriptors[129], count = 0;
    while (count < 129) {
        int fd = dup(file);
        if (fd < 0) break;
        descriptors[count++] = fd;
    }
    int fd_errno = count < 129 ? errno : 0;
    for (int i = 0; i < count; ++i) close(descriptors[i]);
    if (signal(SIGXFSZ, SIG_IGN) == SIG_ERR) return 4;
    char byte = 'x';
    ssize_t below = pwrite(file, &byte, 1, CONTROL_RESOURCE_FSIZE_BYTES - 1);
    errno = 0;
    ssize_t above = pwrite(file, &byte, 1, CONTROL_RESOURCE_FSIZE_BYTES);
    int file_errno = errno;
    struct stat status;
    if (fstat(file, &status)) return 5;
    close(file);
    /* Untouched virtual reservation; zero physical pages committed, no RSS claim. */
    size_t reserve = CONTROL_RESOURCE_VM_DELTA_BYTES + 64 * MIB;
    errno = 0;
    void *mapped = mmap(NULL, reserve, PROT_NONE, MAP_PRIVATE | MAP_ANON, -1, 0);
    int vm_errno = mapped == MAP_FAILED ? errno : 0;
    if (mapped != MAP_FAILED) munmap(mapped, reserve);
    mach_vm_address_t address = 0;
    kern_return_t mach_status = mach_vm_allocate(mach_task_self(), &address, reserve, VM_FLAGS_ANYWHERE);
    if (!mach_status) mach_vm_deallocate(mach_task_self(), address, reserve);
    void *small = mmap(NULL, MIB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    int small_ok = small != MAP_FAILED;
    if (small_ok) { memset(small, 1, MIB); munmap(small, MIB); }
    mach_vm_address_t small_address = 0;
    kern_return_t small_mach = mach_vm_allocate(mach_task_self(), &small_address, MIB, VM_FLAGS_ANYWHERE);
    if (!small_mach) mach_vm_deallocate(mach_task_self(), small_address, MIB);
    printf("{\"limited\":%d,\"vm_baseline_bytes\":%llu,\"vm_delta_bytes\":%llu,\"vm_ceiling_bytes\":%llu,"
           "\"nofile\":128,\"fsize_bytes\":16777216,\"duplicates\":%d,\"fd_errno\":%d,"
           "\"file_below\":%ld,\"file_above\":%ld,\"file_errno\":%d,\"file_size\":%lld,"
           "\"mmap_errno\":%d,\"mach_status\":%d,\"small_ok\":%d,\"small_mach\":%d,"
           "\"physical_touch_bytes\":1048576,\"untouched_reservation_bytes\":%llu}\n",
           limited, (unsigned long long)state.loaded_vm_baseline_bytes,
           (unsigned long long)CONTROL_RESOURCE_VM_DELTA_BYTES,
           (unsigned long long)state.address_space_ceiling_bytes,
           count, fd_errno, (long)below, (long)above, file_errno, (long long)status.st_size,
           vm_errno, mach_status, small_ok, small_mach, (unsigned long long)reserve);
    return 0;
}
#elif defined(RESOURCE_OBSERVER)
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    char *end = NULL;
    errno = 0;
    long pid = strtol(argv[1], &end, 10);
    if (errno || !end || *end || pid <= 1 || pid > INT_MAX) return 2;
    struct proc_taskinfo info;
    struct proc_fdinfo descriptors[256];
    int size = proc_pidinfo((int)pid, PROC_PIDTASKINFO, 0, &info, sizeof(info));
    if (size != sizeof(info)) return 3;
    size = proc_pidinfo((int)pid, PROC_PIDLISTFDS, 0, descriptors, sizeof(descriptors));
    if (size <= 0 || (size_t)size >= sizeof(descriptors) || size % sizeof(struct proc_fdinfo)) return 4;
    printf("{\"virtual_bytes\":%llu,\"resident_bytes\":%llu,\"fd_count\":%lu}\n",
           (unsigned long long)info.pti_virtual_size, (unsigned long long)info.pti_resident_size,
           (unsigned long)(size / sizeof(struct proc_fdinfo)));
    return 0;
}
#elif defined(RESOURCE_SUPERVISOR)
extern char **environ;
int main(int argc, char **argv) {
    if (argc != 4 || strcmp(argv[1], FIXED_WORKER) || strcmp(argv[2], "confined")) return 2;
    int wall = !strncmp(argv[3], "wall-", 5);
    int queue = kqueue();
    if (queue < 0) return 3;
    struct kevent timer;
    EV_SET(&timer, 1, EVFILT_TIMER, EV_ADD | EV_ONESHOT, 0, wall ? 1500 : 10000, NULL);
    double started = seconds(CLOCK_MONOTONIC);
    if (kevent(queue, &timer, 1, NULL, 0, NULL)) return 4;
    posix_spawn_file_actions_t actions;
    /* kqueue is not inherited by the child; adding a close action yields EBADF. */
    if (posix_spawn_file_actions_init(&actions)) return 5;
    pid_t child;
    char *args[] = {argv[1], "confined", argv[3], NULL};
    int error = posix_spawn(&child, FIXED_WORKER, &actions, NULL, args, environ);
    posix_spawn_file_actions_destroy(&actions);
    if (error) { fprintf(stderr, "resource-spawn-errno=%d\n", error); return 6; }
    printf("{\"broker\":%d,\"worker\":%d,\"pgid\":%d}\n", getpid(), child, getpgrp());
    fflush(stdout);
    int initial = 0, fired = 0;
    for (;;) {
        int status;
        struct rusage usage = {0};
        pid_t result = wait4(child, &status, WNOHANG | WUNTRACED, &usage);
        if (result < 0 && errno != EINTR) return 7;
        if (result == child) {
            if (WIFSTOPPED(status)) {
                int signal_number = WSTOPSIG(status);
                if (!initial && signal_number == SIGSTOP) { initial = 1; signal_number = 0; }
                if (ptrace(PT_CONTINUE, child, (caddr_t)1, signal_number)) return 8;
            } else {
                double cpu = usage.ru_utime.tv_sec + usage.ru_utime.tv_usec / 1e6 +
                    usage.ru_stime.tv_sec + usage.ru_stime.tv_usec / 1e6;
                printf("{\"type\":\"status\",\"exit\":%d,\"signal\":%d,\"cpu_seconds\":%.6f,"
                       "\"elapsed_seconds\":%.6f,\"timer_fired\":%s,\"safety_timeout\":%s}\n",
                       WIFEXITED(status) ? WEXITSTATUS(status) : -1,
                       WIFSIGNALED(status) ? WTERMSIG(status) : 0, cpu,
                       seconds(CLOCK_MONOTONIC) - started, fired ? "true" : "false",
                       fired && !wall ? "true" : "false");
                fflush(stdout);
                close(queue);
                return 0;
            }
        }
        struct kevent event;
        struct timespec tick = {0, 10000000};
        int count = kevent(queue, NULL, 0, &event, 1, &tick);
        if (count < 0 && errno != EINTR) return 9;
        if (count == 1) {
            if (event.flags & EV_ERROR || event.filter != EVFILT_TIMER || fired) return 10;
            fired = 1;
            printf("{\"type\":\"timer\",\"deadline_ms\":%d,\"issued_seconds\":%.6f,"
                   "\"deadline_monotonic_seconds\":%.9f}\n",
                   wall ? 1500 : 10000, seconds(CLOCK_MONOTONIC) - started,
                   started + (wall ? 1.5 : 10.0));
            fflush(stdout);
            /* Unreaped direct child ownership: no worker-selected PID. */
            if (kill(child, SIGKILL) && errno != ESRCH) return 11;
        }
    }
}
#else
#ifndef RESOURCE_FILE
#error RESOURCE_FILE must bind a private file at build time
#endif

typedef int (*sandbox_init_type)(const char *, uint64_t, const char *const *, char **);

static int limit_record(int which, const char *name, rlim_t value, const char *phase, int install) {
    struct rlimit requested = {value, value}, observed = {0};
    int set_error = 0;
    if (install && setrlimit(which, &requested)) set_error = errno;
    if (getrlimit(which, &observed)) return 21;
    if (set_error) {
        printf("{\"type\":\"limit\",\"resource\":\"%s\",\"phase\":\"%s\",\"value\":%llu,"
               "\"set_errno\":%d,\"raise_errno\":-1,\"soft\":%llu,\"hard\":%llu}\n",
               name, phase, (unsigned long long)value, set_error,
               (unsigned long long)observed.rlim_cur, (unsigned long long)observed.rlim_max);
        return 0; /* Unavailable controls are explicit evidence, not denial proof. */
    }
    struct rlimit raised = {value + 1, value + 1};
    int raise_error = setrlimit(which, &raised) ? errno : 0;
    if (getrlimit(which, &observed)) return 22;
    printf("{\"type\":\"limit\",\"resource\":\"%s\",\"phase\":\"%s\",\"value\":%llu,"
           "\"set_errno\":0,\"raise_errno\":%d,\"soft\":%llu,\"hard\":%llu}\n",
           name, phase, (unsigned long long)value, raise_error,
           (unsigned long long)observed.rlim_cur, (unsigned long long)observed.rlim_max);
    return raise_error == EPERM && observed.rlim_cur == value && observed.rlim_max == value ? 0 : 23;
}

static void observation_hold(void) {
    fflush(stdout);
    struct timespec hold = {0, 300000000};
    nanosleep(&hold, NULL);
}

static int memory_probe(void) {
    /* Each method peaks at 65 MiB; release mmap mappings before Mach VM. */
    void *small = mmap(NULL, MIB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    int positive = small != MAP_FAILED;
    if (positive) memset(small, 1, MIB);
    errno = 0;
    void *large = mmap(NULL, 64 * MIB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    int error = large == MAP_FAILED ? errno : 0;
    if (!error) {
        volatile unsigned char *bytes = large;
        for (size_t offset = 0; offset < 64 * MIB; offset += 4096) bytes[offset] = 1;
    }
    if (positive) munmap(small, MIB);
    if (!error) munmap(large, 64 * MIB);
    mach_vm_address_t small_address = 0, large_address = 0;
    kern_return_t small_result = mach_vm_allocate(mach_task_self(), &small_address, MIB, VM_FLAGS_ANYWHERE);
    if (small_result == KERN_SUCCESS) memset((void *)small_address, 1, MIB);
    kern_return_t large_result = mach_vm_allocate(mach_task_self(), &large_address, 64 * MIB, VM_FLAGS_ANYWHERE);
    if (large_result == KERN_SUCCESS) {
        volatile unsigned char *bytes = (void *)large_address;
        for (size_t offset = 0; offset < 64 * MIB; offset += 4096) bytes[offset] = 1;
    }
    printf("{\"type\":\"probe\",\"positive\":%s,\"over_errno\":%d,"
           "\"mach_positive\":%s,\"mach_over_error\":%d,\"peak_allocation_bytes\":%llu}\n",
           positive ? "true" : "false", error, small_result == KERN_SUCCESS ? "true" : "false",
           large_result, (unsigned long long)(65 * MIB));
    observation_hold();
    if (small_result == KERN_SUCCESS) mach_vm_deallocate(mach_task_self(), small_address, MIB);
    if (large_result == KERN_SUCCESS) mach_vm_deallocate(mach_task_self(), large_address, 64 * MIB);
    return 37;
}

static int fd_probe(void) {
    int descriptors[64], count = 0, error = 0;
    while (count < 64) {
        int descriptor = dup(STDOUT_FILENO);
        if (descriptor < 0) { error = errno; break; }
        descriptors[count++] = descriptor;
    }
    printf("{\"type\":\"probe\",\"positive\":%s,\"over_errno\":%d,\"opened\":%d}\n",
           count > 0 ? "true" : "false", error, count);
    observation_hold();
    for (int index = 0; index < count; index++) close(descriptors[index]);
    return 37;
}

static int file_probe(int descriptor) {
    unsigned char data[4096] = {0};
    if (signal(SIGXFSZ, SIG_IGN) == SIG_ERR) return 31;
    ssize_t first = write(descriptor, data, sizeof(data));
    errno = 0;
    ssize_t extra = write(descriptor, data, 1);
    int error = extra < 0 ? errno : 0;
    struct stat info;
    if (fstat(descriptor, &info)) return 32;
    printf("{\"type\":\"probe\",\"positive\":%s,\"over_errno\":%d,\"file_bytes\":%lld}\n",
           first == 4096 ? "true" : "false", error, (long long)info.st_size);
    observation_hold();
    close(descriptor);
    return 37;
}

static int cpu_probe(const char *name) {
    sigset_t mask;
    sigemptyset(&mask);
    sigaddset(&mask, SIGXCPU);
    if (strstr(name, "ignore") && signal(SIGXCPU, SIG_IGN) == SIG_ERR) return 41;
    if (strstr(name, "block") && sigprocmask(SIG_BLOCK, &mask, NULL)) return 42;
    int death = !strncmp(name, "death-", 6);
    printf("{\"type\":\"cpu-ready\",\"self_completion\":%s}\n", death ? "false" : "true");
    fflush(stdout);
    double current = seconds(CLOCK_PROCESS_CPUTIME_ID);
    volatile uint64_t sum = 0;
    while (current < 3.0) {
        for (int index = 0; index < 65536; index++) sum += (uint64_t)index;
        current = seconds(CLOCK_PROCESS_CPUTIME_ID);
    }
    /* No cooperative exit can compete with the five-second owner-death window. */
    if (death) { for (;;) pause(); }
    sigset_t pending;
    if (sigpending(&pending)) return 43;
    printf("{\"type\":\"cpu\",\"seconds\":%.6f,\"sigxcpu_pending\":%s}\n",
           current, sigismember(&pending, SIGXCPU) ? "true" : "false");
    return 37;
}

int main(int argc, char **argv) {
    if (argc != 3 || strcmp(argv[1], "confined") || geteuid() == 0) return 2;
    const char *name = argv[2];
    const char *allowed[] = {"nofile", "nofile-control", "fsize", "fsize-control", "as", "as-control",
                           "data", "data-control", "cpu-default", "cpu-ignore", "cpu-block", "cpu-control",
                           "wall-ignore", "wall-block", "death-ignore", "death-block", NULL};
    int found = 0;
    for (int index = 0; allowed[index]; index++) if (!strcmp(name, allowed[index])) found = 1;
    if (!found) return 2;
    int file = open(RESOURCE_FILE, O_CREAT | O_TRUNC | O_RDWR, 0600);
    if (file < 0) return 3;
    void *library = dlopen("/usr/lib/libsandbox.dylib", RTLD_NOW | RTLD_LOCAL);
    if (!library) return 4;
    sandbox_init_type init = (sandbox_init_type)dlsym(library, "sandbox_init_with_parameters");
    if (!init) return 5;
    if (ptrace(PT_TRACE_ME, 0, NULL, 0) || raise(SIGSTOP)) return 6;
    /* Fixed trusted bootstrap before this point; no fixture work before tracing. */
    for (int descriptor = 3; descriptor < 256; descriptor++) if (descriptor != file) close(descriptor);
    int which = -1;
    const char *resource = "";
    rlim_t value = 0;
    int control = strstr(name, "control") != NULL;
    if (!strncmp(name, "nofile", 6)) { which = RLIMIT_NOFILE; resource = "NOFILE"; value = 32; }
    else if (!strncmp(name, "fsize", 5)) { which = RLIMIT_FSIZE; resource = "FSIZE"; value = 4096; }
    else if (!strncmp(name, "data", 4)) { which = RLIMIT_DATA; resource = "DATA"; value = 16 * MIB; }
    else if (!strncmp(name, "as", 2)) {
        struct mach_task_basic_info info;
        mach_msg_type_number_t count = MACH_TASK_BASIC_INFO_COUNT;
        if (task_info(mach_task_self(), MACH_TASK_BASIC_INFO, (task_info_t)&info, &count) != KERN_SUCCESS) return 7;
        which = RLIMIT_AS; resource = "AS"; value = info.virtual_size + 32 * MIB;
        printf("{\"type\":\"baseline\",\"virtual_bytes\":%llu,\"resident_bytes\":%llu}\n",
               (unsigned long long)info.virtual_size, (unsigned long long)info.resident_size);
    } else { which = RLIMIT_CPU; resource = "CPU"; value = 1; }
    if (limit_record(RLIMIT_CORE, "CORE", 0, "pre", 1)) return 8;
    if (!control && limit_record(which, resource, value, "pre", 1)) return 9;
    const char *profile = "(version 1)(deny default)(allow signal (target self))"
        "(allow file-write-data (literal (param \"OUTPUT\")))";
    const char *parameters[] = {"OUTPUT", RESOURCE_FILE, NULL};
    char *error = NULL;
    if (init(profile, 0, parameters, &error)) return 10;
    if (limit_record(RLIMIT_CORE, "CORE", 0, "post", 0)) return 11;
    if (!control && limit_record(which, resource, value, "post", 1)) return 12;
    if (fork() != -1 || errno != EPERM) return 13;
    printf("{\"type\":\"ready\",\"case\":\"%s\",\"confined\":true}\n", name);
    fflush(stdout);
    /* Independent observer captures the traced identity before short probes end. */
    struct timespec capture = {0, 200000000};
    nanosleep(&capture, NULL);
    if (!strncmp(name, "nofile", 6)) return fd_probe();
    if (!strncmp(name, "fsize", 5)) return file_probe(file);
    if (!strncmp(name, "as", 2) || !strncmp(name, "data", 4)) return memory_probe();
    return cpu_probe(name);
}
#endif
