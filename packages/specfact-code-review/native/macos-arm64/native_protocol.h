#ifndef SPECFACT_NATIVE_PROTOCOL_H
#define SPECFACT_NATIVE_PROTOCOL_H

#include <stdint.h>

#define SPECFACT_MAGIC 0x53464e31u
#define SPECFACT_PROTOCOL_VERSION 1u
#define SPECFACT_MAX_PATH 1024u
#define SPECFACT_MAX_WORKERS 8u
#define SPECFACT_PYTHON_CHILD_PLAN 27u
#define SPECFACT_UV_ACQUISITION_PLAN 28u
#define SPECFACT_UV_CHILD_PLAN 29u
#define SPECFACT_GIT_CHILD_PLAN 30u
#define SPECFACT_MAX_PLAN 30u
#define SPECFACT_WORKER_MAGIC 0x53464d31u
#define SPECFACT_WORKER_PAYLOAD 4096u
#define SPECFACT_WORKER_STREAM 4096u

struct __attribute__((packed)) specfact_worker_request {
    uint32_t magic;
    uint16_t version;
    uint16_t opcode;
    uint32_t handle;
    uint32_t length;
};

struct __attribute__((packed)) specfact_child_envelope {
    uint32_t parent_plan;
    uint32_t length;
};
/* Broker-produced native tool startup: cwd, argv strings, then NAME=value strings.
 * The fixed executable and managed-channel environment are never caller data. */
struct specfact_uv_child_startup {
    uint32_t argc;
    uint32_t envc;
    unsigned char data[SPECFACT_WORKER_PAYLOAD - 2 * sizeof(uint32_t)];
};
#define SPECFACT_MARKER_READY 0x52454144u

enum specfact_opcode { SPECFACT_LAUNCH = 1, SPECFACT_WAIT = 2, SPECFACT_CANCEL = 3 };

struct __attribute__((packed)) specfact_request {
    uint32_t magic;
    uint16_t version;
    uint16_t opcode;
    uint32_t plan;
    uint32_t handle;
    uint32_t timeout_ms;
    uint32_t open_files;
    uint64_t address_space_bytes;
    uint64_t file_size_bytes;
    uint64_t output_bytes;
    char invocation[SPECFACT_MAX_PATH];
    char project[SPECFACT_MAX_PATH];
    char output[SPECFACT_MAX_PATH];
    char temporary[SPECFACT_MAX_PATH];
};

struct __attribute__((packed)) specfact_reply {
    uint32_t magic;
    uint16_t version;
    uint16_t status;
    uint32_t handle;
    int32_t wait_status;
    uint32_t detail;
};

#endif
