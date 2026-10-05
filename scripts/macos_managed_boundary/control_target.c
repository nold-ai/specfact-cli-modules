/* Fixed replacement image; confinement is inherited, never installed here. */
#include <inttypes.h>
#include <mach/mach.h>
#include <signal.h>
#include <string.h>
#include <time.h>
#include "control_probes.h"

__attribute__((constructor)) static void target_initializer(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) _exit(30);
    uint64_t ns = (uint64_t)now.tv_sec * UINT64_C(1000000000) + (uint64_t)now.tv_nsec;
    if (printf("target-initializer-ns=%" PRIu64 "\n", ns) < 0 || fflush(stdout)) _exit(31);
}

/* Preserve returned send rights while comparing real exception actions. */
struct exception_snapshot { mach_port_t port; exception_behavior_t behavior; thread_state_flavor_t flavor; };
static int exception_snapshot(int thread, mach_port_t self_thread, struct exception_snapshot *snapshot) {
    exception_mask_t masks[EXC_TYPES_COUNT];
    mach_port_t ports[EXC_TYPES_COUNT];
    exception_behavior_t behaviors[EXC_TYPES_COUNT];
    thread_state_flavor_t flavors[EXC_TYPES_COUNT];
    mach_msg_type_number_t count = EXC_TYPES_COUNT;
    kern_return_t result = thread ?
        thread_get_exception_ports(self_thread, EXC_MASK_SOFTWARE, masks, &count, ports, behaviors, flavors) :
        task_get_exception_ports(mach_task_self(), EXC_MASK_SOFTWARE, masks, &count, ports, behaviors, flavors);
    if (result || count > EXC_TYPES_COUNT) return 40;
    memset(snapshot, 0, sizeof(*snapshot));
    for (mach_msg_type_number_t i = 0; i < count; i++) {
        if ((masks[i] & EXC_MASK_SOFTWARE) && ports[i]) {
            if (snapshot->port) return 40;
            snapshot->port = ports[i]; snapshot->behavior = behaviors[i]; snapshot->flavor = flavors[i];
        } else if (ports[i]) mach_port_deallocate(mach_task_self(), ports[i]);
    }
    return 0;
}
static void release_snapshot(struct exception_snapshot *snapshot) {
    if (snapshot->port) mach_port_deallocate(mach_task_self(), snapshot->port);
}
static kern_return_t exception_set(int thread, mach_port_t self_thread, mach_port_t port) {
    return thread ? thread_set_exception_ports(self_thread, EXC_MASK_SOFTWARE, port,
        EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE) :
        task_set_exception_ports(mach_task_self(), EXC_MASK_SOFTWARE, port,
        EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE);
}
static int same_snapshot(struct exception_snapshot *left, struct exception_snapshot *right) {
    return left->port == right->port && left->behavior == right->behavior && left->flavor == right->flavor;
}
/* Return codes alone are insufficient: inspect set, swap and clear results.
 * Positive controls clear between set/swap so each really changes an action. */
static int exception_port_probe(int thread, int denied) {
    mach_port_t port = MACH_PORT_NULL, self_thread = mach_thread_self();
    struct exception_snapshot original, observed;
    if (mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &port) ||
        mach_port_insert_right(mach_task_self(), port, port, MACH_MSG_TYPE_MAKE_SEND) ||
        exception_snapshot(thread, self_thread, &original)) return 40;
    kern_return_t changed = exception_set(thread, self_thread, port);
    if (exception_snapshot(thread, self_thread, &observed)) return 40;
    int installed = observed.port == port;
    if (installed != !denied || (denied && !same_snapshot(&original, &observed))) return 41;
    release_snapshot(&observed);
    printf("exception-port-%s-status=%d-installed=%d\n", thread ? "thread" : "task", changed, installed);
    if (!denied) {
        if (exception_set(thread, self_thread, MACH_PORT_NULL) ||
            exception_snapshot(thread, self_thread, &observed) || observed.port) return 40;
    }
    exception_mask_t masks[EXC_TYPES_COUNT]; mach_port_t ports[EXC_TYPES_COUNT];
    exception_behavior_t behaviors[EXC_TYPES_COUNT]; thread_state_flavor_t flavors[EXC_TYPES_COUNT];
    mach_msg_type_number_t count = EXC_TYPES_COUNT;
    kern_return_t swapped = thread ?
        thread_swap_exception_ports(self_thread, EXC_MASK_SOFTWARE, port,
            EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE, masks, &count, ports, behaviors, flavors) :
        task_swap_exception_ports(mach_task_self(), EXC_MASK_SOFTWARE, port,
            EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE, masks, &count, ports, behaviors, flavors);
    if (swapped != KERN_SUCCESS && swapped != KERN_NO_ACCESS) return 40;
    if (!swapped) {
        if (count > EXC_TYPES_COUNT) return 40;
        for (mach_msg_type_number_t i = 0; i < count; i++) if (ports[i]) mach_port_deallocate(mach_task_self(), ports[i]);
    }
    if (exception_snapshot(thread, self_thread, &observed)) return 40;
    int swap_installed = observed.port == port;
    if (swap_installed != !denied || (denied && !same_snapshot(&original, &observed))) return 41;
    release_snapshot(&observed);
    printf("exception-swap-%s-installed=%d\n", thread ? "thread" : "task", swap_installed);
    (void)exception_set(thread, self_thread, MACH_PORT_NULL);
    if (exception_snapshot(thread, self_thread, &observed)) return 40;
    int preserved = denied ? same_snapshot(&original, &observed) : observed.port == MACH_PORT_NULL;
    printf("exception-clear-%s-preserved=%d\n", thread ? "thread" : "task", preserved);
    release_snapshot(&observed); release_snapshot(&original);
    if (fflush(stdout)) return 40;
    mach_port_deallocate(mach_task_self(), port);
    mach_port_mod_refs(mach_task_self(), port, MACH_PORT_RIGHT_RECEIVE, -1);
    mach_port_deallocate(mach_task_self(), self_thread);
    return preserved ? 0 : 41;
}

int main(int argc, char **argv) {
    if (argc != 2 || strlen(argv[1]) != 1 || argv[1][0] < '0' || argv[1][0] > '7') return 2;
    int mode = argv[1][0] - '0';
    if (!mode) return control_probes(0, "target-positive-ok");
    if (mode == 7) return exception_port_probe(0, 0) || exception_port_probe(1, 0);
    int result = control_probes(1, "target-denials-ok");
    if (result) return result;
    puts("target-entry");
    if (fflush(stdout)) return 5;
    if (mode == 5 || mode == 6) {
        result = exception_port_probe(mode == 6, 1);
        return result ? result : 37;
    }
    if (mode == 1) return 37;
    if (mode == 2) {
        if (signal(SIGTRAP, SIG_DFL) == SIG_ERR || raise(SIGTRAP)) return 3;
        puts("target-trap-was-suppressed");
        return fflush(stdout) ? 5 : 37;
    }
    if (mode == 4) {
        puts("target-second-exec");
        if (fflush(stdout)) return 5;
        /* argv[0] is the compiled fixed target supplied by the trusted worker.
         * The broker must deliver the second exec trap before initializers. */
        execl(argv[0], argv[0], "1", (char *)NULL);
        return 39;
    }
    if (setsid() < 0 || signal(SIGTERM, SIG_IGN) == SIG_ERR) return 4;
    puts("target-ready");
    if (fflush(stdout)) return 5;
    for (;;) pause();
}
