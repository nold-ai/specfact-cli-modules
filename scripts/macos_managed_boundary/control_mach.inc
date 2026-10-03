/* SDK MIG decoding, kernel-origin checks and directly owned thread admission. */
#include <mach/mig_errors.h>
#include "mach_exc_server.h"
#include "control_mach_policy.h"

static mach_port_t exception_ports[WORKERS];
static int exception_owner = -1;
static mig_reply_error_t held_replies[WORKERS];
static mach_port_t held_threads[WORKERS];

static int owned_thread(mach_port_t task, mach_port_t thread) {
    thread_act_array_t threads = NULL;
    mach_msg_type_number_t count = 0;
    if (task_threads(task, &threads, &count) != KERN_SUCCESS) return 0;
    int found = 0;
    for (mach_msg_type_number_t i = 0; i < count; i++) {
        if (threads[i] == thread) found = 1;
        mach_port_deallocate(mach_task_self(), threads[i]);
    }
    vm_deallocate(mach_task_self(), (vm_address_t)threads, count * sizeof(*threads));
    return found && count <= 16; /* Fixed fixtures, never arbitrary customer threads. */
}

kern_return_t catch_mach_exception_raise(mach_port_t port, mach_port_t thread,
    mach_port_t task, exception_type_t exception, mach_exception_data_t code,
    mach_msg_type_number_t count, audit_token_t token) {
    pid_t pid = -1;
    int index;
    for (index = 0; index < worker_count; index++) if (exception_ports[index] == port) break;
    if (index == worker_count || pid_for_task(task, &pid) != KERN_SUCCESS ||
        !owned_signal(workers[index].pid, workers[index].reaped, (pid_t)token.val[5],
            pid, exception, code, count) || !owned_thread(task, thread)) die();
    struct worker *item = &workers[index];
    int initial = !item->traced;
    if (initial && code[1] != SIGSTOP) die();
    item->traced = 1;
    if (initial) { printf("{\"trace\":%d}\n", item->pid); fflush(stdout); }
    mach_port_deallocate(mach_task_self(), task);
    if (initial && item->mode == 4) {
        if (held_threads[index]) die();
        held_threads[index] = thread;
        exception_owner = index;
        return MIG_NO_REPLY; /* Preserve the kernel RPC until cancellation/death. */
    }
    if (ptrace(PT_THUPDATE, item->pid, (caddr_t)(uintptr_t)thread,
        initial ? 0 : (int)code[1])) die();
    mach_port_deallocate(mach_task_self(), thread);
    return KERN_SUCCESS;
}

kern_return_t catch_mach_exception_raise_state(mach_port_t port,
    exception_type_t exception, const mach_exception_data_t code,
    mach_msg_type_number_t count, int *flavor, const thread_state_t old,
    mach_msg_type_number_t old_count, thread_state_t new, mach_msg_type_number_t *new_count,
    audit_token_t token) {
    (void)port; (void)exception; (void)code; (void)count; (void)flavor;
    (void)old; (void)old_count; (void)new; (void)new_count; (void)token;
    die(); return KERN_FAILURE;
}

kern_return_t catch_mach_exception_raise_state_identity(mach_port_t port,
    mach_port_t thread, mach_port_t task, exception_type_t exception,
    mach_exception_data_t code, mach_msg_type_number_t count, int *flavor,
    thread_state_t old, mach_msg_type_number_t old_count, thread_state_t new,
    mach_msg_type_number_t *new_count, audit_token_t token) {
    (void)port; (void)thread; (void)task; (void)exception; (void)code;
    (void)count; (void)flavor; (void)old; (void)old_count;
    (void)new; (void)new_count; (void)token;
    die(); return KERN_FAILURE;
}

static void exception_spawn(posix_spawnattr_t *attributes, int index) {
    mach_port_t port;
    if (mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &port) ||
        mach_port_insert_right(mach_task_self(), port, port, MACH_MSG_TYPE_MAKE_SEND) ||
        posix_spawnattr_setexceptionports_np(attributes, EXC_MASK_SOFTWARE, port,
            EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE)) die();
    exception_ports[index] = port;
}

static void release_held(int index) {
    if (!held_threads[index]) return;
    if (ptrace(PT_THUPDATE, workers[index].pid,
        (caddr_t)(uintptr_t)held_threads[index], 0)) die();
    /* The validated initial RPC reply has no complex rights. */
    if (mach_msg(&held_replies[index].Head, MACH_SEND_MSG | MACH_SEND_TIMEOUT,
        held_replies[index].Head.msgh_size, 0, MACH_PORT_NULL, 0, MACH_PORT_NULL)) die();
    mach_port_deallocate(mach_task_self(), held_threads[index]);
    held_threads[index] = MACH_PORT_NULL;
    memset(&held_replies[index], 0, sizeof(held_replies[index]));
}

static void exceptions(void) {
    for (int i = 0; i < worker_count; i++) {
        if (!exception_ports[i]) continue;
        for (int messages = 0; messages < 8; messages++) {
            union { mach_msg_header_t head; unsigned char bytes[4096]; } request, reply;
            memset(&request, 0, sizeof(request)); memset(&reply, 0, sizeof(reply));
            mach_msg_return_t result = mach_msg(&request.head,
                MACH_RCV_MSG | MACH_RCV_TIMEOUT |
                MACH_RCV_TRAILER_TYPE(MACH_MSG_TRAILER_FORMAT_0) |
                MACH_RCV_TRAILER_ELEMENTS(MACH_RCV_TRAILER_AUDIT),
                0, sizeof(request), exception_ports[i], 0, MACH_PORT_NULL);
            if (result == MACH_RCV_TIMED_OUT) break;
            if (result != MACH_MSG_SUCCESS) die();
            exception_owner = -1;
            if (!mach_exc_server(&request.head, &reply.head)) die();
            mig_reply_error_t *answer = (mig_reply_error_t *)&reply;
            if (answer->RetCode == MIG_NO_REPLY) {
                if (exception_owner != i || held_replies[i].Head.msgh_remote_port) die();
                /* Retain the complete simple MIG reply, not merely its header. */
                answer->RetCode = KERN_SUCCESS;
                if (reply.head.msgh_size > sizeof(held_replies[i])) {
                    /* Storage is supplied below by the exact MIG simple reply type. */
                    die();
                }
                memcpy(&held_replies[i], &reply, reply.head.msgh_size);
            } else if (answer->RetCode != KERN_SUCCESS ||
                mach_msg(&reply.head, MACH_SEND_MSG | MACH_SEND_TIMEOUT,
                    reply.head.msgh_size, 0, MACH_PORT_NULL, 0, MACH_PORT_NULL)) die();
        }
    }
}
