/* Native ARM64 per-worker budgets. No CPU/RSS or aggregate-output claim. */
#ifndef CONTROL_RESOURCE_H
#define CONTROL_RESOURCE_H
#include <errno.h>
#include <stdint.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <mach/mach.h>

#define CONTROL_RESOURCE_NOFILE ((rlim_t)128)
#define CONTROL_RESOURCE_FSIZE_BYTES ((rlim_t)(UINT64_C(16) * 1024 * 1024))
#define CONTROL_RESOURCE_VM_DELTA_BYTES (UINT64_C(1024) * 1024 * 1024)
#define CONTROL_RESOURCE_POLICY \
    "(deny process-info-setcontrol)" \
    "(deny syscall-unix (syscall-number SYS_setrlimit) (with errno EPERM))"

struct control_resource_state {
    uint64_t loaded_vm_baseline_bytes;
    rlim_t address_space_ceiling_bytes;
};

static inline int control_resource_exact(int resource, rlim_t expected) {
    struct rlimit observed;
    if (getrlimit(resource, &observed)) return errno;
    return observed.rlim_cur == expected && observed.rlim_max == expected ? 0 : EINVAL;
}

static inline int control_resource_configure(struct control_resource_state *state) {
    if (!state || geteuid() == 0) return EINVAL;
    mach_task_basic_info_data_t info;
    mach_msg_type_number_t count = MACH_TASK_BASIC_INFO_COUNT;
    if (task_info(mach_task_self(), MACH_TASK_BASIC_INFO, (task_info_t)&info, &count) != KERN_SUCCESS ||
        count != MACH_TASK_BASIC_INFO_COUNT) return EIO;
    if (info.virtual_size >= (uint64_t)RLIM_INFINITY - CONTROL_RESOURCE_VM_DELTA_BYTES) return EOVERFLOW;
    state->loaded_vm_baseline_bytes = info.virtual_size;
    state->address_space_ceiling_bytes = info.virtual_size + CONTROL_RESOURCE_VM_DELTA_BYTES;
    const int resources[] = {RLIMIT_NOFILE, RLIMIT_FSIZE, RLIMIT_AS};
    const rlim_t values[] = {CONTROL_RESOURCE_NOFILE, CONTROL_RESOURCE_FSIZE_BYTES, state->address_space_ceiling_bytes};
    for (unsigned index = 0; index < 3; ++index) {
        struct rlimit requested = {values[index], values[index]};
        if (setrlimit(resources[index], &requested)) return errno;
        int error = control_resource_exact(resources[index], values[index]);
        if (error) return error;
    }
    return 0; /* Partial setup failure must abort the bootstrap, never continue. */
}

/* Direct ARM64 syscall proves that libc interception is not the API boundary. */
static inline int control_resource_raw_set(int resource, const struct rlimit *limit) {
#if defined(__aarch64__)
    register unsigned long value __asm("x0") = (unsigned long)resource;
    register const struct rlimit *argument __asm("x1") = limit;
    register unsigned long number __asm("x16") = SYS_setrlimit;
    unsigned int failed;
    __asm__ volatile("svc #0x80\n\tcset %w2, cs"
        : "+r"(value), "+r"(argument), "=r"(failed) : "r"(number) : "memory", "cc");
    return failed ? (int)value : 0;
#else
    (void)resource; (void)limit;
    return ENOTSUP;
#endif
}

static inline int control_resource_verify(const struct control_resource_state *state, int confined) {
    if (!state) return EINVAL;
    const int resources[] = {RLIMIT_NOFILE, RLIMIT_FSIZE, RLIMIT_AS};
    const rlim_t values[] = {CONTROL_RESOURCE_NOFILE, CONTROL_RESOURCE_FSIZE_BYTES, state->address_space_ceiling_bytes};
    for (unsigned index = 0; index < 3; ++index) {
        int error = control_resource_exact(resources[index], values[index]);
        if (error) return error;
        struct rlimit raised = {values[index] + 1, values[index] + 1};
        errno = 0;
        if (setrlimit(resources[index], &raised) != -1 || errno != EPERM ||
            control_resource_raw_set(resources[index], &raised) != EPERM) return EACCES;
        struct rlimit unchanged = {values[index], values[index]};
        if (confined) {
            struct rlimit lowered = {values[index] - 1, values[index]};
            errno = 0;
            if (setrlimit(resources[index], &unchanged) != -1 || errno != EPERM ||
                control_resource_raw_set(resources[index], &unchanged) != EPERM) return EACCES;
            errno = 0;
            if (setrlimit(resources[index], &lowered) != -1 || errno != EPERM ||
                control_resource_raw_set(resources[index], &lowered) != EPERM) return EACCES;
        } else if (setrlimit(resources[index], &unchanged) ||
                   control_resource_raw_set(resources[index], &unchanged)) return EIO;
        error = control_resource_exact(resources[index], values[index]);
        if (error) return error;
    }
    return 0;
}
#endif
