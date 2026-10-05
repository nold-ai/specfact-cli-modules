#include "native_protocol.h"
#include "sandbox_diagnostics.h"
#include "git_child_policy.h"
#include "generated_requirements.h"

#include <CoreFoundation/CoreFoundation.h>
#include <Security/Security.h>
#include <mach/mach.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/socket.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

struct worker {
    uint32_t handle;
    pid_t pid;
    int active;
    int mode, fd, reaped, status, traced, wait_accepted, exec_admitted;
    char output[1025];
    char output_root[SPECFACT_MAX_PATH];
    uint64_t output_budget;
    size_t used;
    uint32_t parent;
    struct specfact_request grant;
    int rpc_in, rpc_out, io_in, io_out, io_err, temporary_fd;
    uint64_t deadline_ns;
    unsigned char rpc_buffer[sizeof(struct specfact_worker_request) + SPECFACT_WORKER_PAYLOAD];
    unsigned char rpc_reply[sizeof(struct specfact_reply) + SPECFACT_WORKER_STREAM];
    size_t rpc_used, reply_used, reply_sent;
    off_t stdout_offset, stderr_offset;
};

static struct worker workers[SPECFACT_MAX_WORKERS];
static int worker_count = SPECFACT_MAX_WORKERS;
static uint32_t next_handle = 1;
static void service_workers(const char *capsule, int control);
static void stop_children(uint32_t parent);

#define WORKERS SPECFACT_MAX_WORKERS
#define OUTPUT 1024
#define WORKER_REQUIREMENT SPECFACT_BOOTSTRAP_REQUIREMENT

static const char *target_requirement(const struct worker *item) {
    if (item->mode == SPECFACT_UV_CHILD_PLAN) return SPECFACT_UV_REQUIREMENT;
    if (item->mode == SPECFACT_GIT_CHILD_PLAN) return SPECFACT_GIT_REQUIREMENT;
    if (!item->exec_admitted) return item->mode == 1 ? SPECFACT_SELF_TEST_REQUIREMENT : SPECFACT_PYTHON_REQUIREMENT;
    if (item->mode == 12) return SPECFACT_RUFF_REQUIREMENT;
    if (item->mode == 14) return SPECFACT_SEMGREP_REQUIREMENT;
    if (item->mode == 15) return SPECFACT_NODE_REQUIREMENT;
    if (item->mode == SPECFACT_UV_ACQUISITION_PLAN) return SPECFACT_UV_REQUIREMENT;
    return SPECFACT_PYTHON_REQUIREMENT;
}

static const char *current_requirement(const struct worker *item) {
    return item->exec_admitted ? SPECFACT_PYTHON_REQUIREMENT : SPECFACT_BOOTSTRAP_REQUIREMENT;
}

#define TARGET_REQUIREMENT(item) target_requirement(item)
#define CURRENT_REQUIREMENT(item) current_requirement(item)

static void die(void) { kill(getpid(), SIGKILL); _exit(81); }

#include "control_mach.inc"

static int exact_io(int fd, void *buffer, size_t length, int writing) {
    unsigned char *cursor = buffer;
    while (length) {
        ssize_t count = writing ? write(fd, cursor, length) : read(fd, cursor, length);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return -1;
        cursor += count;
        length -= (size_t)count;
    }
    return 0;
}

static void reply(int fd, uint16_t status, uint32_t handle, int wait_status, uint32_t detail) {
    struct specfact_reply result = {
        .magic = SPECFACT_MAGIC,
        .version = SPECFACT_PROTOCOL_VERSION,
        .status = status,
        .handle = handle,
        .wait_status = wait_status,
        .detail = detail,
    };
    (void)exact_io(fd, &result, sizeof(result), 1);
}

static int valid_path(const char value[SPECFACT_MAX_PATH]) {
    if (!memchr(value, '\0', SPECFACT_MAX_PATH) || value[0] != '/' ||
        strstr(value, "/../") || strstr(value, "/./") || strstr(value, "//")) return 0;
    char current[SPECFACT_MAX_PATH];
    size_t length = strnlen(value, SPECFACT_MAX_PATH);
    if (length >= sizeof(current)) return 0;
    memcpy(current, value, length + 1);
    for (char *cursor = current + 1; ; cursor++) {
        if (*cursor != '/' && *cursor != '\0') continue;
        char saved = *cursor;
        *cursor = '\0';
        struct stat info;
        int invalid = lstat(current, &info) || S_ISLNK(info.st_mode);
        *cursor = saved;
        if (invalid) return 0;
        if (!saved) break;
    }
    struct stat leaf;
    return !lstat(value, &leaf) && leaf.st_uid == getuid();
}

static int beneath(const char *child, const char *parent) {
    size_t length = strlen(parent);
    return !strncmp(child, parent, length) && child[length] == '/';
}

static int overlaps(const char *left, const char *right) {
    return !strcmp(left, right) || beneath(left, right) || beneath(right, left);
}

enum tree_policy { TREE_CAPSULE, TREE_PROJECT, TREE_PRIVATE };

static int valid_tree_fd(int fd, enum tree_policy policy) {
    struct stat root;
    if (fstat(fd, &root) || !S_ISDIR(root.st_mode) || root.st_uid != getuid()) return 0;
    mode_t root_mode = root.st_mode & 0777;
    if ((policy == TREE_CAPSULE || policy == TREE_PRIVATE) && root_mode != 0700) return 0;
    if (policy == TREE_PROJECT && (root_mode & 0222)) return 0;
    int duplicate = dup(fd);
    if (duplicate < 0) return 0;
    DIR *directory = fdopendir(duplicate);
    if (!directory) { close(duplicate); return 0; }
    int valid = 1;
    struct dirent *entry;
    while (valid && (entry = readdir(directory)) != NULL) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        struct stat info;
        if (fstatat(fd, entry->d_name, &info, AT_SYMLINK_NOFOLLOW) || S_ISLNK(info.st_mode) || info.st_uid != getuid()) {
            valid = 0;
        } else if (S_ISDIR(info.st_mode)) {
            int child = openat(fd, entry->d_name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
            valid = child >= 0 && valid_tree_fd(child, policy);
            if (child >= 0) close(child);
        } else if (!S_ISREG(info.st_mode) ||
                   (policy == TREE_CAPSULE && (info.st_mode & 0222)) ||
                   (policy == TREE_PROJECT && (info.st_mode & 0222)) ||
                   (policy == TREE_PRIVATE && info.st_nlink != 1)) {
            valid = 0;
        }
    }
    closedir(directory);
    return valid;
}

static int valid_tree(const char *path, enum tree_policy policy) {
    int fd = open(path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
    if (fd < 0) return 0;
    int valid = valid_tree_fd(fd, policy);
    close(fd);
    return valid;
}

static int exact_private_directory(const char *path) {
    struct stat info;
    return !lstat(path, &info) && S_ISDIR(info.st_mode) && !S_ISLNK(info.st_mode) &&
           info.st_uid == getuid() && (info.st_mode & 0777) == 0700;
}

static int valid_launch_request(const struct specfact_request *request) {
    return request->magic == SPECFACT_MAGIC && request->version == SPECFACT_PROTOCOL_VERSION &&
           request->opcode == SPECFACT_LAUNCH && request->handle == 0 &&
           request->plan >= 1 && request->plan <= SPECFACT_MAX_PLAN &&
           request->plan != SPECFACT_PYTHON_CHILD_PLAN && request->timeout_ms >= 50 &&
           request->plan != SPECFACT_UV_CHILD_PLAN &&
           request->plan != SPECFACT_GIT_CHILD_PLAN &&
           request->timeout_ms <= 900000 && request->open_files >= 32 && request->open_files <= 1024 &&
           request->address_space_bytes >= (UINT64_C(256) << 20) &&
           request->address_space_bytes <= (UINT64_C(16) << 30) &&
           request->file_size_bytes >= (UINT64_C(1) << 20) &&
           request->file_size_bytes <= (UINT64_C(1) << 30) &&
           request->output_bytes >= 1024 && request->output_bytes <= (UINT64_C(64) << 20) &&
           valid_path(request->invocation) && valid_path(request->project) &&
           valid_path(request->output) && valid_path(request->temporary) &&
           exact_private_directory(request->invocation) &&
           beneath(request->project, request->invocation) && beneath(request->output, request->invocation) &&
           beneath(request->temporary, request->invocation) &&
           !overlaps(request->project, request->output) && !overlaps(request->project, request->temporary) &&
           !overlaps(request->output, request->temporary) &&
           getenv("SPECFACT_CAPSULE_ROOT") != NULL &&
           !overlaps(request->invocation, getenv("SPECFACT_CAPSULE_ROOT")) &&
           valid_tree(request->project, TREE_PROJECT) && valid_tree(request->output, TREE_PRIVATE) &&
           valid_tree(request->temporary, TREE_PRIVATE);
}

static int valid_control_request(const struct specfact_request *request) {
    return request->magic == SPECFACT_MAGIC && request->version == SPECFACT_PROTOCOL_VERSION &&
           (request->opcode == SPECFACT_WAIT || request->opcode == SPECFACT_CANCEL) && request->handle != 0 &&
           (request->opcode != SPECFACT_WAIT || (request->timeout_ms >= 1 && request->timeout_ms <= 900000));
}

static int controller_closed(int control) {
    struct pollfd descriptor = {.fd = control, .events = POLLIN | POLLHUP};
    int ready = poll(&descriptor, 1, 0);
    if (ready < 0) return errno != EINTR;
    if (!ready) return 0;
    if (descriptor.revents & (POLLERR | POLLNVAL | POLLHUP)) return 1;
    if (descriptor.revents & POLLIN) {
        char byte;
        ssize_t count = recv(control, &byte, 1, MSG_PEEK | MSG_DONTWAIT);
        return count == 0 || (count < 0 && errno != EAGAIN && errno != EINTR);
    }
    return 0;
}

static int dynamic_identity(pid_t pid, const char *requirement) {
    int ok = 0;
    CFNumberRef number = CFNumberCreate(NULL, kCFNumberIntType, &pid);
    CFStringRef text = CFStringCreateWithCString(NULL, requirement, kCFStringEncodingUTF8);
    if (!number || !text) goto done;
    const void *keys[] = {kSecGuestAttributePid};
    const void *values[] = {number};
    CFDictionaryRef attributes = CFDictionaryCreate(NULL, keys, values, 1,
        &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    SecCodeRef code = NULL;
    SecRequirementRef rule = NULL;
    if (attributes && SecCodeCopyGuestWithAttributes(NULL, attributes, kSecCSDefaultFlags, &code) == errSecSuccess &&
        SecRequirementCreateWithString(text, kSecCSDefaultFlags, &rule) == errSecSuccess &&
        SecCodeCheckValidity(code, kSecCSStrictValidate, rule) == errSecSuccess) ok = 1;
    if (rule) CFRelease(rule);
    if (code) CFRelease(code);
    if (attributes) CFRelease(attributes);
done:
    if (text) CFRelease(text);
    if (number) CFRelease(number);
    return ok;
}

static void retire_worker(struct worker *worker) {
    stop_children(worker->handle);
    int index = (int)(worker - workers);
    if (exception_ports[index]) {
        mach_port_destroy(mach_task_self(), exception_ports[index]);
        exception_ports[index] = MACH_PORT_NULL;
    }
    int descriptors[] = {worker->rpc_in, worker->rpc_out, worker->io_in, worker->io_out, worker->io_err, worker->temporary_fd};
    for (size_t i = 0; i < sizeof(descriptors) / sizeof(descriptors[0]); i++)
        if (descriptors[i] >= 0) close(descriptors[i]);
    memset(worker, 0, sizeof(*worker));
}

static void stop_worker(struct worker *worker) {
    if (!worker->active) return;
    stop_children(worker->handle);
    if (worker->reaped) { retire_worker(worker); return; }
    (void)kill(worker->pid, SIGKILL);
    int index = (int)(worker - workers);
    int status = 0;
    int reaped = 0;
    for (int attempt = 0; attempt < 500; attempt++) {
        exceptions();
        pid_t waited;
        do { waited = waitpid(worker->pid, &status, WNOHANG); } while (waited < 0 && errno == EINTR);
        if (waited == worker->pid && (WIFEXITED(status) || WIFSIGNALED(status))) { reaped = 1; break; }
        if (waited < 0 && errno == ECHILD) { reaped = 1; break; }
        usleep(10000);
    }
    if (!reaped) die();
    if (exception_ports[index]) mach_port_destroy(mach_task_self(), exception_ports[index]);
    exception_ports[index] = MACH_PORT_NULL;
    for (int attempt = 0; attempt < 50; attempt++) {
        pid_t waited;
        do { waited = waitpid(worker->pid, &status, WNOHANG); } while (waited < 0 && errno == EINTR);
        if (waited < 0 && errno == ECHILD) break;
        if (!waited) usleep(10000);
    }
    retire_worker(worker);
}

static void stop_children(uint32_t parent) {
    if (!parent) return;
    for (size_t i = 0; i < SPECFACT_MAX_WORKERS; i++)
        if (workers[i].active && !workers[i].reaped && workers[i].parent == parent) (void)kill(workers[i].pid, SIGKILL);
    for (size_t i = 0; i < SPECFACT_MAX_WORKERS; i++)
        if (workers[i].active && workers[i].parent == parent) stop_worker(&workers[i]);
}

static struct worker *find_worker(uint32_t handle) {
    for (size_t index = 0; index < SPECFACT_MAX_WORKERS; index++)
        if (workers[index].active && workers[index].handle == handle) return &workers[index];
    return NULL;
}

static struct worker *free_worker(void) {
    for (size_t index = 0; index < SPECFACT_MAX_WORKERS; index++)
        if (!workers[index].active) return &workers[index];
    return NULL;
}

static int owner_closed(uint32_t parent) {
    if (!parent) return 0;
    struct worker *owner = find_worker(parent);
    if (!owner || owner->reaped) return 1;
    struct pollfd fd = {.fd = owner->rpc_in, .events = POLLHUP};
    return poll(&fd, 1, 0) > 0 && (fd.revents & (POLLHUP | POLLERR | POLLNVAL));
}

static int startup_failure(uint32_t marker, int marker_fd) {
    uint32_t phase = specfact_startup_failure_phase(marker);
    if (!phase) return 0;
    uint32_t diagnostic = 0;
    ssize_t count = phase == 70 ? read(marker_fd, &diagnostic, sizeof(diagnostic)) : 0;
    uint32_t line = count == sizeof(diagnostic) ? specfact_sandbox_marker_line(diagnostic) : 0;
    fprintf(stderr, "{\"bootstrap_failure_phase\":%u,\"errno\":%u,\"sandbox_profile_line\":%u}\n",
        phase, specfact_startup_failure_errno(marker), line);
    return -(int)phase;
}

static int launch_worker(const char *capsule, int control, const struct specfact_request *request, struct worker *slot,
    uint32_t parent, const unsigned char *child_data, uint32_t child_length, int stdin_fd, int merge_stderr,
    int stream_directory) {
    memset(slot, 0, sizeof(*slot));
    slot->rpc_in = slot->rpc_out = slot->io_in = slot->io_out = slot->io_err = -1;
    slot->temporary_fd = -1;
    slot->parent = parent;
    slot->grant = *request;
    uint32_t marker = 0;
    size_t marker_used = 0;
    char bootstrap[SPECFACT_MAX_PATH], target[SPECFACT_MAX_PATH], tool[SPECFACT_MAX_PATH], profile[SPECFACT_MAX_PATH];
    int written_bootstrap = snprintf(bootstrap, sizeof(bootstrap), "%s/bin/specfact-native-bootstrap", capsule);
    const char *target_format = request->plan == 1 ? "%s/bin/specfact-native-self-test"
        : request->plan == SPECFACT_GIT_CHILD_PLAN ? "%s/tools/git" : "%s/python/bin/python3";
    int written_target = snprintf(target, sizeof(target), target_format, capsule);
    const char *tool_format = "%s/python/bin/python3";
    if (request->plan == 12) tool_format = "%s/tools/ruff";
    else if (request->plan == 14) tool_format = "%s/tools/semgrep-core";
    else if (request->plan == 15) tool_format = "%s/tools/node";
    else if (request->plan == SPECFACT_UV_ACQUISITION_PLAN || request->plan == SPECFACT_UV_CHILD_PLAN)
        tool_format = "%s/tools/uv";
    else if (request->plan == SPECFACT_GIT_CHILD_PLAN) tool_format = "%s/tools/git";
    int written_tool = snprintf(tool, sizeof(tool), tool_format, capsule);
    int written_profile = snprintf(profile, sizeof(profile), "%s/policy/profile.sb", capsule);
    if (written_bootstrap <= 0 || (size_t)written_bootstrap >= sizeof(bootstrap) ||
        written_target <= 0 || (size_t)written_target >= sizeof(target) ||
        written_tool <= 0 || (size_t)written_tool >= sizeof(tool) ||
        written_profile <= 0 || (size_t)written_profile >= sizeof(profile)) return -1;
    int streams = stream_directory < 0 ? open(request->output, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        : fcntl(stream_directory, F_DUPFD_CLOEXEC, 16);
    if (streams < 0) return -2;
    int stdout_fd = openat(streams, "managed-stdout.bin", O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (stdout_fd < 0) { close(streams); return -2; }
    int stderr_fd = openat(streams, "managed-stderr.bin", O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (stderr_fd < 0) { close(stdout_fd); unlinkat(streams, "managed-stdout.bin", 0); close(streams); return -2; }
    int request_pipe[2] = {-1, -1}, marker_pipe[2] = {-1, -1};
    if (pipe(request_pipe)) { close(stdout_fd); close(stderr_fd); unlinkat(streams, "managed-stdout.bin", 0); unlinkat(streams, "managed-stderr.bin", 0); close(streams); return -2; }
    if (pipe(marker_pipe)) { close(request_pipe[0]); close(request_pipe[1]); close(stdout_fd); close(stderr_fd); unlinkat(streams, "managed-stdout.bin", 0); unlinkat(streams, "managed-stderr.bin", 0); close(streams); return -2; }
    int worker_request[2], worker_reply[2];
    if (pipe(worker_request) || pipe(worker_reply)) die();
    /* Redirect only from high-numbered sources, so dup2 destinations 0..6
     * cannot overwrite a source needed by a later file action. */
    int original_sources[] = {stdout_fd, merge_stderr ? stdout_fd : stderr_fd,
        request_pipe[0], marker_pipe[1], worker_request[1], worker_reply[0], stdin_fd};
    int sources[7];
    for (size_t i = 0; i < 7; i++) {
        sources[i] = original_sources[i] < 0 ? -1 : fcntl(original_sources[i], F_DUPFD_CLOEXEC, 16);
        if (original_sources[i] >= 0 && sources[i] < 0) die();
    }
    posix_spawn_file_actions_t actions;
    posix_spawnattr_t attributes;
    if (posix_spawn_file_actions_init(&actions) || posix_spawnattr_init(&attributes) ||
        posix_spawn_file_actions_adddup2(&actions, sources[0], 1) ||
        posix_spawn_file_actions_adddup2(&actions, sources[1], 2) ||
        posix_spawn_file_actions_adddup2(&actions, sources[2], 3) ||
        posix_spawn_file_actions_adddup2(&actions, sources[3], 4) ||
        posix_spawn_file_actions_adddup2(&actions, sources[4], 5) ||
        posix_spawn_file_actions_adddup2(&actions, sources[5], 6)) die();
    if (stdin_fd < 0) {
        if (posix_spawn_file_actions_addopen(&actions, 0, "/dev/null", O_RDONLY, 0)) die();
    } else if (posix_spawn_file_actions_adddup2(&actions, sources[6], 0)) die();
    short flags = POSIX_SPAWN_START_SUSPENDED | POSIX_SPAWN_CLOEXEC_DEFAULT;
    if (posix_spawnattr_setflags(&attributes, flags)) die();
    int index = (int)(slot - workers);
    exception_spawn(&attributes, index);
    char *const arguments[] = {bootstrap, "--request-fd", "3", "--marker-fd", "4", NULL};
    char capsule_value[SPECFACT_MAX_PATH + 32], target_value[SPECFACT_MAX_PATH + 32];
    char tool_value[SPECFACT_MAX_PATH + 32], profile_value[SPECFACT_MAX_PATH + 32];
    int capsule_length = snprintf(capsule_value, sizeof(capsule_value), "SPECFACT_CAPSULE_ROOT=%s", capsule);
    int target_length = snprintf(target_value, sizeof(target_value), "SPECFACT_FIXED_TARGET=%s", target);
    int tool_length = snprintf(tool_value, sizeof(tool_value), "SPECFACT_FIXED_TOOL=%s", tool);
    int profile_length = snprintf(profile_value, sizeof(profile_value), "SPECFACT_FIXED_PROFILE=%s", profile);
    if (capsule_length <= 0 || (size_t)capsule_length >= sizeof(capsule_value) ||
        target_length <= 0 || (size_t)target_length >= sizeof(target_value) ||
        tool_length <= 0 || (size_t)tool_length >= sizeof(tool_value) ||
        profile_length <= 0 || (size_t)profile_length >= sizeof(profile_value)) {
        close(request_pipe[0]); close(request_pipe[1]); close(marker_pipe[0]); close(marker_pipe[1]);
        close(stdout_fd); close(stderr_fd); unlinkat(streams, "managed-stdout.bin", 0); unlinkat(streams, "managed-stderr.bin", 0); close(streams);
        for (size_t i = 0; i < 7; i++) if (sources[i] >= 0) close(sources[i]);
        close(worker_request[0]); close(worker_request[1]); close(worker_reply[0]); close(worker_reply[1]);
        posix_spawn_file_actions_destroy(&actions); posix_spawnattr_destroy(&attributes);
        if (exception_ports[index]) mach_port_destroy(mach_task_self(), exception_ports[index]);
        exception_ports[index] = MACH_PORT_NULL;
        return -1;
    }
    char *const environment[] = {capsule_value, target_value, tool_value, profile_value, "LANG=C", "LC_ALL=C", NULL};
    pid_t pid = 0;
    int error = posix_spawn(&pid, bootstrap, &actions, &attributes, arguments, environment);
    posix_spawn_file_actions_destroy(&actions);
    posix_spawnattr_destroy(&attributes);
    for (size_t i = 0; i < 7; i++) if (sources[i] >= 0) close(sources[i]);
    close(request_pipe[0]);
    close(marker_pipe[1]);
    close(worker_request[1]);
    close(worker_reply[0]);
    if (error) {
        close(request_pipe[1]); close(marker_pipe[0]); close(stdout_fd); close(stderr_fd);
        close(worker_request[0]); close(worker_reply[1]);
        if (exception_ports[index]) mach_port_destroy(mach_task_self(), exception_ports[index]);
        exception_ports[index] = MACH_PORT_NULL;
        unlinkat(streams, "managed-stdout.bin", 0); unlinkat(streams, "managed-stderr.bin", 0); close(streams); return -3;
    }
    slot->pid = pid;
    slot->rpc_in = worker_request[0];
    slot->rpc_out = worker_reply[1];
    slot->io_out = stdout_fd;
    slot->io_err = stderr_fd;
    if (fcntl(slot->rpc_in, F_SETFL, O_NONBLOCK) || fcntl(slot->rpc_out, F_SETFL, O_NONBLOCK)) die();
    slot->mode = (int)request->plan;
    slot->fd = marker_pipe[0];
    slot->temporary_fd = parent ? dup(find_worker(parent)->temporary_fd)
        : open(request->temporary, O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
    if (slot->temporary_fd < 0) die();
    if (strlcpy(slot->output_root, request->output, sizeof(slot->output_root)) >= sizeof(slot->output_root)) {
        error = -4;
        goto failed;
    }
    slot->output_budget = request->output_bytes;
    slot->active = 1;
    int marker_flags = fcntl(marker_pipe[0], F_GETFL);
    if (marker_flags < 0 || fcntl(marker_pipe[0], F_SETFL, marker_flags | O_NONBLOCK) < 0 ||
        !dynamic_identity(pid, SPECFACT_BOOTSTRAP_REQUIREMENT) || exact_io(request_pipe[1], (void *)request, sizeof(*request), 1)) {
        error = -4; goto failed;
    }
    if (child_length) {
        struct specfact_child_envelope envelope = {.parent_plan = parent ? find_worker(parent)->mode : 0, .length = child_length};
        if (exact_io(request_pipe[1], &envelope, sizeof(envelope), 1) ||
            exact_io(request_pipe[1], (void *)child_data, child_length, 1)) { error = -4; goto failed; }
    }
    if (
        kill(pid, SIGCONT)) { error = -4; goto failed; }
    close(request_pipe[1]);
    request_pipe[1] = -1;
    uint64_t startup_deadline = exec_timestamp() + UINT64_C(5000000000);
    slot->deadline_ns = exec_timestamp() + (uint64_t)request->timeout_ms * UINT64_C(1000000);
    if (parent && find_worker(parent)->deadline_ns < slot->deadline_ns)
        slot->deadline_ns = find_worker(parent)->deadline_ns;
    if (slot->deadline_ns < startup_deadline) startup_deadline = slot->deadline_ns;
    while (!slot->traced && exec_timestamp() < startup_deadline && !controller_closed(control) && !owner_closed(parent)) {
        exceptions();
        if (marker_used < sizeof(marker)) {
            ssize_t count = read(marker_pipe[0], (char *)&marker + marker_used, sizeof(marker) - marker_used);
            if (count > 0) marker_used += (size_t)count;
            else if (count < 0 && errno != EAGAIN && errno != EINTR) { error = -6; goto failed; }
        }
        if (marker_used == sizeof(marker)) {
            error = startup_failure(marker, marker_pipe[0]);
            if (error) goto failed;
            if (marker != SPECFACT_MARKER_READY) { error = -6; goto failed; }
        }
        usleep(1000);
    }
    if (!slot->traced) { error = -5; goto failed; }
    while (marker_used < sizeof(marker) && exec_timestamp() < startup_deadline && !controller_closed(control) && !owner_closed(parent)) {
        exceptions();
        struct pollfd descriptor = {.fd = marker_pipe[0], .events = POLLIN | POLLHUP};
        int ready = poll(&descriptor, 1, 10);
        if (ready < 0 && errno != EINTR) break;
        if (!ready || !(descriptor.revents & (POLLIN | POLLHUP))) continue;
        ssize_t count = read(marker_pipe[0], (char *)&marker + marker_used, sizeof(marker) - marker_used);
        if (count > 0) marker_used += (size_t)count;
        else if (!count || (errno != EAGAIN && errno != EINTR)) break;
    }
    if (marker_used == sizeof(marker)) {
        error = startup_failure(marker, marker_pipe[0]);
        if (error) goto failed;
    }
    if (marker_used != sizeof(marker) || marker != SPECFACT_MARKER_READY || controller_closed(control)) {
        error = -6;
        goto failed;
    }
    while (!slot->exec_admitted && exec_timestamp() < startup_deadline && !controller_closed(control) && !owner_closed(parent)) {
        exceptions();
        usleep(1000);
    }
    /* running_image() admitted the exact stopped replacement before its
     * exception reply resumed target execution. */
    if (!slot->exec_admitted || controller_closed(control) || owner_closed(parent)) { error = -7; goto failed; }
    close(marker_pipe[0]);
    slot->fd = -1;
    slot->handle = next_handle++;
    if (!next_handle) next_handle = 1;
    slot->active = 1;
    close(streams);
    return 0;
failed:
    if (request_pipe[1] >= 0) close(request_pipe[1]);
    close(marker_pipe[0]);
    slot->fd = -1;
    stop_worker(slot);
    unlinkat(streams, "managed-stdout.bin", 0);
    unlinkat(streams, "managed-stderr.bin", 0);
    close(streams);
    return error;
}

enum { WAIT_CONTROLLER_CLOSED = -4 };

#include "managed_workers.inc"

static int wait_bounded(int control, pid_t pid, uint32_t timeout_ms, int *status) {
    uint64_t deadline = exec_timestamp() + (uint64_t)timeout_ms * UINT64_C(1000000);
    for (size_t index = 0; index < SPECFACT_MAX_WORKERS; index++)
        if (workers[index].active && workers[index].pid == pid) {
            if (workers[index].deadline_ns < deadline) deadline = workers[index].deadline_ns;
            workers[index].deadline_ns = deadline;
        }
    while (exec_timestamp() <= deadline) {
        if (controller_closed(control)) return WAIT_CONTROLLER_CLOSED;
        /* Traced runtime signals and exit transitions arrive through the owned
         * Mach port; drain and forward them before checking terminal status. */
        exceptions();
        service_workers(getenv("SPECFACT_CAPSULE_ROOT"), control);
        if (exec_timestamp() > deadline) return 1;
        struct worker *observed = NULL;
        for (size_t index = 0; index < SPECFACT_MAX_WORKERS; index++)
            if (workers[index].active && workers[index].pid == pid) observed = &workers[index];
        if (observed && observed->reaped) { *status = observed->status; return 0; }
        pid_t result;
        do { result = waitpid(pid, status, WNOHANG); } while (result < 0 && errno == EINTR);
        if (result == pid) {
            if (WIFEXITED(*status) || WIFSIGNALED(*status)) return 0;
            return -2;
        }
        if (result < 0) return -1;
        usleep(2000);
    }
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 5 || strcmp(argv[1], "--control-fd") || strcmp(argv[3], "--capsule-root")) return 64;
    if (raise(SIGSTOP)) return 66;
    if (signal(SIGPIPE, SIG_IGN) == SIG_ERR) return 66;
    int control = atoi(argv[2]);
    const char *capsule = argv[4];
    if (control < 3 || !capsule || !valid_path(capsule) || !valid_tree(capsule, TREE_CAPSULE)) return 65;
    for (;;) {
        struct specfact_request request;
        if (exact_io(control, &request, sizeof(request), 0)) break;
        if (request.opcode == SPECFACT_LAUNCH) {
            if (!valid_launch_request(&request)) { reply(control, 1, 0, 0, EINVAL); continue; }
            struct worker *slot = free_worker();
            int launch_result = slot ? launch_worker(capsule, control, &request, slot, 0, NULL, 0, -1, 0, -1) : -8;
            if (launch_result) reply(control, 1, 0, 0, (uint32_t)(100 - launch_result));
            else reply(control, 0, slot->handle, 0, 0);
        } else if (request.opcode == SPECFACT_WAIT) {
            if (!valid_control_request(&request)) { reply(control, 1, request.handle, 0, EINVAL); continue; }
            struct worker *worker = find_worker(request.handle);
            int status = 0;
            int outcome = worker ? wait_bounded(control, worker->pid, request.timeout_ms, &status) : -1;
            if (outcome == WAIT_CONTROLLER_CLOSED) break;
            if (!outcome) {
                char stdout_path[SPECFACT_MAX_PATH], stderr_path[SPECFACT_MAX_PATH];
                struct stat stdout_info, stderr_info;
                int stdout_length = snprintf(stdout_path, sizeof(stdout_path), "%s/managed-stdout.bin", worker->output_root);
                int stderr_length = snprintf(stderr_path, sizeof(stderr_path), "%s/managed-stderr.bin", worker->output_root);
                if (stdout_length <= 0 || (size_t)stdout_length >= sizeof(stdout_path) ||
                    stderr_length <= 0 || (size_t)stderr_length >= sizeof(stderr_path) ||
                    lstat(stdout_path, &stdout_info) || lstat(stderr_path, &stderr_info) ||
                    !S_ISREG(stdout_info.st_mode) || !S_ISREG(stderr_info.st_mode) ||
                    stdout_info.st_uid != getuid() || stderr_info.st_uid != getuid() ||
                    stdout_info.st_nlink != 1 || stderr_info.st_nlink != 1 ||
                    (uint64_t)stdout_info.st_size > worker->output_budget ||
                    (uint64_t)stderr_info.st_size > worker->output_budget - (uint64_t)stdout_info.st_size)
                    outcome = -3;
            }
            if (outcome) {
                if (worker) stop_worker(worker);
                reply(control, 1, request.handle, 0, outcome > 0 ? ETIMEDOUT : ECHILD);
            }
            else { retire_worker(worker); reply(control, 0, request.handle, status, 0); }
        } else if (request.opcode == SPECFACT_CANCEL) {
            if (!valid_control_request(&request)) { reply(control, 1, request.handle, 0, EINVAL); continue; }
            struct worker *worker = find_worker(request.handle);
            if (!worker) reply(control, 1, request.handle, 0, ESRCH);
            else { stop_worker(worker); reply(control, 0, request.handle, 0, 0); }
        } else reply(control, 1, 0, 0, ENOTSUP);
    }
    for (size_t index = 0; index < SPECFACT_MAX_WORKERS; index++) stop_worker(&workers[index]);
    return 0;
}
