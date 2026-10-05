/* Only previously validated simple kernel RPC replies enter this send path. */
#include <mach/mach.h>
static void send_reply(mach_msg_header_t *reply) {
    mach_msg_return_t result = mach_msg(reply, MACH_SEND_MSG | MACH_SEND_TIMEOUT,
        reply->msgh_size, 0, MACH_PORT_NULL, 0, MACH_PORT_NULL);
    if (result == MACH_MSG_SUCCESS) return;
    /* Match Apple's recoverable-send ownership contract. Other errors may
     * already have partially consumed rights: process death cleans them up. */
    if (result == MACH_SEND_INVALID_DEST || result == MACH_SEND_TIMED_OUT ||
        result == MACH_SEND_INTERRUPTED) mach_msg_destroy(reply);
    if (result != MACH_SEND_INVALID_DEST) die();
}
