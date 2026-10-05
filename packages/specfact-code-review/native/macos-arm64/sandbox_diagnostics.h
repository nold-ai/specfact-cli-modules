/* Numeric-only diagnostics for sealed profile compilation; never admission. */
#ifndef SPECFACT_SANDBOX_DIAGNOSTICS_H
#define SPECFACT_SANDBOX_DIAGNOSTICS_H
#include <stdint.h>
#include <string.h>
static inline uint32_t specfact_sandbox_error_line(const char *error) {
    if (!error) return 0;
    size_t length = 0;
    while (length < 4096 && error[length]) length++;
    for (size_t offset = 0; offset + 5 < length; offset++) {
        if (memcmp(error + offset, "line ", 5)) continue;
        const char *digits = error + offset + 5;
        if (*digits < '0' || *digits > '9') return 0;
        uint32_t value = 0;
        while (digits < error + length && *digits >= '0' && *digits <= '9') {
            value = value * 10 + (uint32_t)(*digits++ - '0');
            if (value > 4096) return 0;
        }
        return value;
    }
    return 0;
}
static inline uint32_t specfact_sandbox_line_marker(uint32_t line) {
    return line && line <= 4096 ? 0x4c000000u | line : 0;
}
static inline uint32_t specfact_sandbox_marker_line(uint32_t marker) {
    uint32_t line = marker & 0x00ffffffu;
    return (marker & 0xff000000u) == 0x4c000000u && line && line <= 4096 ? line : 0;
}
#endif
