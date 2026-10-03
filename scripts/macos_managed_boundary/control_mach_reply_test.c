/* Safe mocks: never send/deallocate actual Mach rights or signal a host PID. */
#include <mach/mach.h>
#include <setjmp.h>
#include <string.h>
#include <unistd.h>
static jmp_buf failed;
static int disposed, sends, deaths;
static mach_msg_return_t result;
static mach_msg_header_t *expected;
static void die(void) { deaths++; longjmp(failed, 1); }
#define mach_msg fixture_send
#define mach_msg_destroy fixture_destroy
mach_msg_return_t fixture_send(mach_msg_header_t *, mach_msg_option_t,
    mach_msg_size_t, mach_msg_size_t, mach_port_name_t, mach_msg_timeout_t, mach_port_name_t);
void fixture_destroy(mach_msg_header_t *);
#include "control_mach_reply.h"
#undef mach_msg
#undef mach_msg_destroy
mach_msg_return_t fixture_send(mach_msg_header_t *reply, mach_msg_option_t options,
    mach_msg_size_t send_size, mach_msg_size_t receive_size, mach_port_name_t receive,
    mach_msg_timeout_t timeout, mach_port_name_t notify) {
    if (reply != expected || options != (MACH_SEND_MSG | MACH_SEND_TIMEOUT) ||
        send_size != sizeof(*reply) || receive_size || receive || timeout || notify) _exit(90);
    sends++; return result;
}
void fixture_destroy(mach_msg_header_t *reply) {
    if (reply != expected || sends != 1 || deaths) _exit(91);
    disposed++;
}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    int want_disposed = 0, want_deaths = 0;
    if (!strcmp(argv[1], "success")) result = MACH_MSG_SUCCESS;
    else if (!strcmp(argv[1], "invalid-destination")) { result = MACH_SEND_INVALID_DEST; want_disposed = 1; }
    else if (!strcmp(argv[1], "timeout")) { result = MACH_SEND_TIMED_OUT; want_disposed = want_deaths = 1; }
    else if (!strcmp(argv[1], "interrupted")) { result = MACH_SEND_INTERRUPTED; want_disposed = want_deaths = 1; }
    else if (!strcmp(argv[1], "invalid-right")) { result = MACH_SEND_INVALID_RIGHT; want_deaths = 1; }
    else return 2;
    mach_msg_header_t reply = {.msgh_size = sizeof(reply)};
    expected = &reply;
    if (!setjmp(failed)) send_reply(&reply);
    return sends == 1 && disposed == want_disposed && deaths == want_deaths ? 0 : 3;
}
