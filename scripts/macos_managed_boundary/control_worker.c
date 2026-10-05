/* Fixed benign fixtures. No customer executable, pathname or grant is accepted. */
#include <dlfcn.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <string.h>
#include <sys/ptrace.h>
#include "control_probes.h"
#include "control_resource.h"

#ifndef FIXED_TARGET
#error "FIXED_TARGET must be the build-owned absolute target path C string"
#endif

/* Older kernels use the same unconditional RPC denial as the capsule. */
#define CONTROL_EXCEPTION_PORT_POLICY \
    "(deny syscall-mig (kernel-mig-routine task_set_exception_ports task_swap_exception_ports " \
    "thread_set_exception_ports thread_swap_exception_ports))" \
    "(when (defined? 'mach-task-exception-port-set)(deny mach-task-exception-port-set))"

/* Same measured custom-profile ABI as startup_worker; unsupported production API. */
typedef int (*init_function)(const char *, uint64_t, const char *const [], char **);

static int confine_exec(init_function init) {
    /* No data-volume subtree aliases: only Apple library roots and exact metadata.
     * TARGET and every target ancestor come exclusively from the compiled path. */
    static const char base_profile[] =
        "(version 1)(deny default)" CONTROL_EXCEPTION_PORT_POLICY "(allow signal (target self))"
        CONTROL_RESOURCE_POLICY
        "(allow file-read* (literal \"/\"))" /* dyld libignition opens root for openat; no descendants. */
        "(allow file-read* file-map-executable process-exec (literal (param \"TARGET\")))"
        "(allow file-read* file-map-executable"
        " (subpath \"/System/Library\") (subpath \"/usr/lib\")"
        " (subpath \"/System/Cryptexes/OS/System/Library\")"
        " (subpath \"/System/Cryptexes/OS/usr/lib\")"
        " (subpath \"/System/Volumes/Preboot/Cryptexes/OS/System/Library\")"
        " (subpath \"/System/Volumes/Preboot/Cryptexes/OS/usr/lib\"))"
        "(allow file-read-metadata"
        " (literal \"/\") (literal \"/System\") (literal \"/usr\")"
        " (literal \"/System/Cryptexes\") (literal \"/System/Cryptexes/OS\")"
        " (literal \"/System/Cryptexes/OS/System\")"
        " (literal \"/System/Cryptexes/OS/usr\")"
        " (literal \"/System/Volumes\") (literal \"/System/Volumes/Preboot\")"
        " (literal \"/System/Volumes/Preboot/Cryptexes\")"
        " (literal \"/System/Volumes/Preboot/Cryptexes/OS\")"
        " (literal \"/System/Volumes/Preboot/Cryptexes/OS/System\")"
        " (literal \"/System/Volumes/Preboot/Cryptexes/OS/usr\")";
    enum { MAX_ANCESTORS = 64 };
    const char target[] = FIXED_TARGET;
    size_t length = strlen(target);
    if (length < 2 || length >= PATH_MAX || target[0] != '/' || target[length - 1] == '/') return 22;
    char profile[16384];
    char ancestors[MAX_ANCESTORS][PATH_MAX];
    char names[MAX_ANCESTORS][24];
    const char *params[2 * MAX_ANCESTORS + 3] = {"TARGET", target, NULL};
    size_t used = sizeof(base_profile) - 1;
    memcpy(profile, base_profile, used + 1);
    unsigned count = 0;
    size_t component = 1;
    for (size_t i = 1; i <= length; ++i) {
        if (target[i] != '/' && target[i] != '\0') continue;
        size_t size = i - component;
        if (!size || (size == 1 && target[component] == '.') ||
            (size == 2 && target[component] == '.' && target[component + 1] == '.')) return 22;
        component = i + 1;
        if (i == length) break;
        if (count == MAX_ANCESTORS) return 22;
        memcpy(ancestors[count], target, i);
        ancestors[count][i] = '\0';
        int written = snprintf(names[count], sizeof(names[count]), "ANCESTOR%u", count);
        if (written < 0 || (size_t)written >= sizeof(names[count])) return 22;
        written = snprintf(profile + used, sizeof(profile) - used,
            " (literal (param \"%s\"))", names[count]);
        if (written < 0 || (size_t)written >= sizeof(profile) - used) return 22;
        used += (size_t)written;
        params[2 + 2 * count] = names[count];
        params[3 + 2 * count] = ancestors[count];
        ++count;
    }
    if (used + 2 > sizeof(profile)) return 22;
    profile[used++] = ')';
    profile[used] = '\0';
    params[2 + 2 * count] = NULL;
    char *error = NULL;
    return init(profile, 0, params, &error) ? 22 : 0;
}

static int confine(int mode, struct control_resource_state *resources) {
    void *library = dlopen("/usr/lib/libsandbox.dylib", RTLD_NOW | RTLD_LOCAL);
    if (!library) return 20;
    init_function init = (init_function)dlsym(library, "sandbox_init_with_parameters");
    if (!init) return 21;
    int resource_error = control_resource_configure(resources);
    if (resource_error || control_resource_verify(resources, 0)) return 70;
    if (mode >= 6) return confine_exec(init);
    const char *profile = "(version 1)(deny default)" CONTROL_EXCEPTION_PORT_POLICY "(allow signal (target self))"
        CONTROL_RESOURCE_POLICY;
    const char *params[] = {NULL};
    char *error = NULL;
    return init(profile, 0, params, &error) ? 22 : 0;
}

static int exec_target(int mode) {
    if (mode == 8) {
        if (signal(SIGTRAP, SIG_DFL) == SIG_ERR || raise(SIGTRAP)) return 3;
        puts("runtime-trap-was-suppressed");
        return fflush(stdout) ? 5 : 37; /* Never enter the target after this trap. */
    }
    if (mode == 9) {
        execl(FIXED_TARGET "-missing", FIXED_TARGET "-missing", "1", (char *)NULL);
        int saved = errno;
        if (saved != ENOENT && saved != EPERM && saved != EACCES) return 39;
        puts("exec-failed");
        return fflush(stdout) ? 5 : 38;
    }
    const char *argument = mode == 7 ? "2" : mode == 10 ? "3" : mode == 12 ? "4" : mode == 14 ? "5" : mode == 15 ? "6" : "1";
    /* Mode 11 is held by the broker at its verified replacement stop. */
    execl(FIXED_TARGET, FIXED_TARGET, argument, (char *)NULL);
    return 39;
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    int mode;
    if (strlen(argv[1]) == 1 && argv[1][0] >= '0' && argv[1][0] <= '9') mode = argv[1][0] - '0';
    else if (!strcmp(argv[1], "10")) mode = 10;
    else if (!strcmp(argv[1], "11")) mode = 11;
    else if (!strcmp(argv[1], "12")) mode = 12;
    else if (!strcmp(argv[1], "13")) mode = 13;
    else if (!strcmp(argv[1], "14")) mode = 14;
    else if (!strcmp(argv[1], "15")) mode = 15;
    else return 2;
    if (!mode) return control_probes(0, "control-positive-ok");
    if (mode == 3) { for (;;) pause(); } /* launchd-owned trusted pretrace */
    if (ptrace(PT_TRACE_ME, 0, NULL, 0)) return 3;
    /* The held identity-swap fixture may ignore termination only after kernel tracing. */
    if (mode == 13 && signal(SIGTERM, SIG_IGN) == SIG_ERR) return 4;
    if (ptrace(PT_SIGEXC, 0, NULL, 0) || raise(SIGSTOP)) return 3;
    /* Only traced code can leave the launchd group or ignore termination. */
    if (mode == 2 && (setsid() < 0 || signal(SIGTERM, SIG_IGN) == SIG_ERR)) return 4;
    struct control_resource_state resources;
    int result = confine(mode, &resources);
    if (result) return result;
    if (control_resource_verify(&resources, 1)) return 71;
    printf("resource-bounds vm-baseline=%llu vm-delta=%llu vm-ceiling=%llu nofile=128 fsize=16777216 api-denied=1\n",
        (unsigned long long)resources.loaded_vm_baseline_bytes,
        (unsigned long long)CONTROL_RESOURCE_VM_DELTA_BYTES,
        (unsigned long long)resources.address_space_ceiling_bytes);
    result = control_probes(1, "control-denials-ok");
    if (result) return result;
    puts("control-ready");
    if (fflush(stdout)) return 5;
    if (mode >= 6) return exec_target(mode);
    if (mode == 5) { raise(SIGTRAP); puts("runtime-trap-was-suppressed"); return 37; }
    if (mode == 1) { puts("control-fixture-output"); return 37; }
    for (;;) pause();
}
