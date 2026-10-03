/* Invocation-scoped, bounded control experiment; no production admission. */
#include <Security/Security.h>
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <launch.h>
#include <mach/mach.h>
#include <signal.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef FIXED_WORKER
#error "Build requires a fixed signed worker"
#endif
#ifndef WORKER_REQUIREMENT
#error "Build requires a pinned worker CDHash requirement"
#endif
#define WORKERS 8
#define PAYLOAD 52
#define OUTPUT 1024
#define QUEUE 4096

struct worker {
    pid_t pid;
    uint64_t handle;
    double deadline;
    int mode, fd, reaped, status, traced, wait_accepted;
    const char *reason;
    char output[OUTPUT + 1];
    size_t used;
};
static struct worker workers[WORKERS];
static int worker_count, client = -1, authenticated, pending = -1, requests;
static int wakeup[2];
static unsigned char capability[32], input[PAYLOAD + 4], output[QUEUE];
static audit_token_t expected;
static size_t input_used, output_used, output_sent;
static double partial_deadline, session_deadline;

static double now(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value)) _exit(80);
    return value.tv_sec + value.tv_nsec / 1e9;
}

static void die(void) {
    /* Self SIGKILL exercises kernel trace cleanup, including unreaped children. */
    kill(getpid(), SIGKILL);
    _exit(81);
}

static void child_event(int number) {
    (void)number;
    int saved = errno;
    char byte = 0;
    (void)write(wakeup[1], &byte, 1);
    errno = saved;
}

/* Private diagnostic snapshots only; eight workers and 64 requests bound events.
 * Preserve errno and emit no payload, status, handle or authority material. */
static void control_state(const struct worker *item) {
    int saved = errno;
    printf("{\"control_state\":%d,\"wait_accepted\":%s,\"wait_pending\":%s,"
        "\"worker_reaped\":%s,\"output_closed\":%s}\n", item->pid,
        item->wait_accepted ? "true" : "false",
        pending >= 0 && item == &workers[pending] ? "true" : "false",
        item->reaped ? "true" : "false", item->fd < 0 ? "true" : "false");
    fflush(stdout);
    errno = saved;
}

static void nonblocking(int fd) {
    if (fd < 0 || fd >= FD_SETSIZE || fcntl(fd, F_SETFL, O_NONBLOCK) < 0 ||
        fcntl(fd, F_SETFD, FD_CLOEXEC) < 0) die();
}

static int authority(const char *path) {
    int fd = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    struct stat info;
    unsigned char data[64];
    if (fd < 0) return 0;
    int valid = !fstat(fd, &info) && S_ISREG(info.st_mode) && info.st_uid == getuid() &&
        (info.st_mode & 0777) == 0600 && info.st_size == sizeof(data) &&
        read(fd, data, sizeof(data)) == sizeof(data);
    close(fd);
    if (!valid) return 0;
    memcpy(capability, data, 32);
    memcpy(&expected, data + 32, sizeof(expected));
    return expected.val[1] == getuid() && expected.val[5] > 1 && expected.val[7];
}

static int peer(int fd) {
    uid_t uid;
    gid_t gid;
    pid_t pid;
    audit_token_t token;
    socklen_t size = sizeof(token);
    if (getpeereid(fd, &uid, &gid) || uid != getuid() ||
        getsockopt(fd, SOL_LOCAL, LOCAL_PEERTOKEN, &token, &size) || size != sizeof(token)) return 0;
    size = sizeof(pid);
    if (getsockopt(fd, SOL_LOCAL, LOCAL_PEERPID, &pid, &size) || size != sizeof(pid)) return 0;
    return pid == (pid_t)expected.val[5] && !memcmp(&token, &expected, sizeof(token));
}

static int signed_worker(void) {
    CFURLRef url = CFURLCreateFromFileSystemRepresentation(NULL, (const UInt8 *)FIXED_WORKER,
        strlen(FIXED_WORKER), false);
    SecStaticCodeRef code = NULL;
    SecRequirementRef requirement = NULL;
    if (!url) return 0;
    OSStatus result = SecStaticCodeCreateWithPath(url, kSecCSDefaultFlags, &code);
    if (!result) result = SecRequirementCreateWithString(CFSTR(WORKER_REQUIREMENT), kSecCSDefaultFlags, &requirement);
    if (!result) result = SecStaticCodeCheckValidity(code, kSecCSStrictValidate, requirement);
    if (requirement) CFRelease(requirement);
    if (code) CFRelease(code);
    CFRelease(url);
    return result == errSecSuccess;
}

static void queue(const char *json) {
    size_t length = strlen(json);
    if (length > 2048) die();
    if (output_sent) {
        memmove(output, output + output_sent, output_used - output_sent);
        output_used -= output_sent;
        output_sent = 0;
    }
    if (length + 4 > QUEUE - output_used) die();
    uint32_t size = htonl((uint32_t)length);
    memcpy(output + output_used, &size, 4);
    memcpy(output + output_used + 4, json, length);
    output_used += length + 4;
}

static void reject(const char *error) {
    char response[128];
    snprintf(response, sizeof(response), "{\"version\":1,\"ok\":false,\"error\":\"%s\"}", error);
    queue(response);
}

static void result(int index, const char *state) {
    struct worker *item = &workers[index];
    char escaped[OUTPUT * 2 + 1];
    size_t position = 0;
    for (size_t i = 0; i < item->used; i++) {
        unsigned char value = (unsigned char)item->output[i];
        if (value == '\n') { escaped[position++] = '\\'; escaped[position++] = 'n'; }
        else if (value == '"' || value == '\\') { escaped[position++] = '\\'; escaped[position++] = (char)value; }
        else if (value >= 32 && value < 127) escaped[position++] = (char)value;
        else die();
    }
    escaped[position] = 0;
    char response[2300];
    snprintf(response, sizeof(response),
        "{\"version\":1,\"ok\":true,\"handle\":%llu,\"pid\":%d,\"state\":\"%s\","
        "\"deadline_ns\":%llu,\"exit\":%d,\"signal\":%d,\"traced\":%s,\"reason\":\"%s\",\"output\":\"%s\"}",
        (unsigned long long)item->handle, item->pid, state,
        (unsigned long long)(item->deadline * 1e9),
        item->reaped && WIFEXITED(item->status) ? WEXITSTATUS(item->status) : -1,
        item->reaped && WIFSIGNALED(item->status) ? WTERMSIG(item->status) : 0,
        item->traced ? "true" : "false", item->reason, escaped);
    queue(response);
}

#ifndef CONTROL_BSD_TEST
#include "control_mach.inc"
#endif

static void launch(int mode, unsigned int timeout) {
    if (worker_count == WORKERS) { reject("worker-limit"); return; }
    if (!signed_worker()) { reject("signature"); return; }
    int stream[2];
    if (pipe(stream)) die();
    nonblocking(stream[0]);
    posix_spawn_file_actions_t actions;
    posix_spawnattr_t attributes;
    if (posix_spawn_file_actions_init(&actions) || posix_spawnattr_init(&attributes)) die();
    if (posix_spawnattr_setflags(&attributes, POSIX_SPAWN_CLOEXEC_DEFAULT) ||
        posix_spawn_file_actions_addopen(&actions, 0, "/dev/null", O_RDONLY, 0) ||
        posix_spawn_file_actions_adddup2(&actions, stream[1], 1) ||
        posix_spawn_file_actions_adddup2(&actions, stream[1], 2)) die();
    #ifndef CONTROL_BSD_TEST
    exception_spawn(&attributes, worker_count);
    #endif
    char fixture[] = {(char)('0' + mode), 0};
    char *args[] = {FIXED_WORKER, fixture, NULL};
    char *environment[] = {"PATH=/usr/bin:/bin", "LANG=C", NULL};
    struct worker *item = &workers[worker_count];
    int error = posix_spawn(&item->pid, FIXED_WORKER, &actions, &attributes, args, environment);
    posix_spawn_file_actions_destroy(&actions);
    posix_spawnattr_destroy(&attributes);
    close(stream[1]);
    if (error) { close(stream[0]); reject("spawn"); return; }
    item->mode = mode;
    item->fd = stream[0];
    item->deadline = now() + timeout / 1000.0;
    item->reason = "completed";
    item->wait_accepted = 0;
    /* A random handle is invocation-local; retain all handles, including reaped ones. */
    do {
        arc4random_buf(&item->handle, sizeof(item->handle));
        for (int i = 0; i < worker_count; i++) if (workers[i].handle == item->handle) item->handle = 0;
    } while (!item->handle);
    result(worker_count++, "launched");
    control_state(item);
}

static uint64_t integer(const unsigned char *data, size_t size) {
    uint64_t value = 0;
    for (size_t i = 0; i < size; i++) value = (value << 8) | data[i];
    return value;
}

static void request(void) {
    const unsigned char *data = input + 4;
    if (++requests > 64) die();
    if (data[0] != 1) { reject("version"); return; }
    if (data[1] > 4) { reject("opcode"); return; }
    if (integer(data + 2, 2)) { reject("reserved"); return; }
    unsigned int mismatch = 0;
    for (int i = 0; i < 32; i++) mismatch |= data[i + 20] ^ capability[i];
    if (mismatch) { reject("capability"); return; }
    int opcode = data[1];
    uint64_t handle = integer(data + 4, 8);
    unsigned int argument = (unsigned int)integer(data + 12, 4);
    unsigned int timeout = (unsigned int)integer(data + 16, 4);
    if (!authenticated && opcode != 0) { reject("authentication"); return; }
    if (!opcode) {
        if (authenticated || handle || argument || timeout) { reject("arguments"); return; }
        authenticated = 1;
        queue("{\"version\":1,\"ok\":true,\"state\":\"authenticated\"}");
        return;
    }
    if (opcode == 1) {
        if (handle || argument < 1 || argument > 5 || timeout < 50 || timeout > 5000) { reject("arguments"); return; }
        launch((int)argument, timeout);
        return;
    }
    if (timeout || (opcode != 3 && argument) || (opcode == 3 && argument != SIGTERM && argument != SIGKILL)) {
        reject("arguments"); return;
    }
    int index;
    for (index = 0; index < worker_count; index++) if (workers[index].handle == handle) break;
    if (index == worker_count) { reject("handle"); return; }
    struct worker *item = &workers[index];
    if (opcode == 2) {
        if (pending >= 0) { reject("wait-limit"); return; }
        item->wait_accepted = 1;
        if (item->reaped && item->fd < 0) result(index, "exited");
        else pending = index;
        control_state(item); /* Immediate completion already has pending cleared. */
    } else if (item->reaped) result(index, "exited");
    else {
        /* No reuse race: this is the broker's own child, never reaped yet. */
        if (kill(item->pid, opcode == 4 ? SIGKILL : (int)argument) && errno != ESRCH) die();
        #ifndef CONTROL_BSD_TEST
        release_held(index);
        #endif
        item->reason = opcode == 4 ? "cancel" : "signal";
        if (opcode == 4 || argument == SIGKILL) item->deadline = session_deadline;
        result(index, "signalled");
    }
}

static void receive(void) {
    /* One bounded frame per iteration; EOF remains monitored during deferred wait. */
    size_t target = input_used < 4 ? 4 : sizeof(input);
    ssize_t length = recv(client, input + input_used, target - input_used, 0);
    if (length == 0) die();
    if (length < 0) { if (errno != EAGAIN && errno != EINTR) die(); return; }
    if (!input_used) partial_deadline = now() + 1;
    input_used += (size_t)length;
    if (input_used >= 4 && integer(input, 4) != PAYLOAD) die();
    if (input_used == sizeof(input)) {
        request();
        input_used = 0;
        partial_deadline = 0;
    }
}

static void reap(void) {
    for (int i = 0; i < worker_count; i++) {
        struct worker *item = &workers[i];
        if (item->reaped) continue;
        int status;
        pid_t pid;
        do { pid = waitpid(item->pid, &status, WNOHANG | WUNTRACED); } while (pid < 0 && errno == EINTR);
        if (pid < 0) die();
        if (!pid) continue;
        if (WIFSTOPPED(status)) {
            #ifndef CONTROL_BSD_TEST
            /* Mach RPC alone resumes signal stops; never race it with PT_CONTINUE. */
            continue;
            #else
            int stopped = WSTOPSIG(status);
            int initial_stop = !item->traced;
            if (!item->traced) {
                if (stopped != SIGSTOP) die();
                item->traced = 1;
                printf("{\"trace\":%d}\n", item->pid); fflush(stdout);
                if (item->mode == 4) continue;
            }
            if (ptrace(PT_CONTINUE, item->pid, (caddr_t)1,
                initial_stop ? 0 : stopped)) die();
            #endif
        } else {
            item->status = status;
            item->reaped = 1;
            control_state(item);
        }
    }
}

static void drain(struct worker *item) {
    char buffer[256];
    ssize_t count = read(item->fd, buffer, sizeof(buffer));
    if (!count) { close(item->fd); item->fd = -1; control_state(item); return; }
    if (count < 0) { if (errno != EAGAIN && errno != EINTR) die(); return; }
    if ((size_t)count > OUTPUT - item->used) die();
    memcpy(item->output + item->used, buffer, (size_t)count);
    item->used += (size_t)count;
    item->output[item->used] = 0;
    printf("{\"output\":%d,\"bytes\":%zd}\n", item->pid, count); fflush(stdout);
}

static double expire_workers(double current, double deadline) {
    for (int i = 0; i < worker_count; i++) {
        struct worker *item = &workers[i];
        if (item->reaped) continue;
        if (current >= item->deadline) {
            if (kill(item->pid, SIGKILL) && errno != ESRCH) die();
            #ifndef CONTROL_BSD_TEST
            release_held(i);
            #endif
            item->reason = "timeout";
            item->deadline = session_deadline; /* one signal, then wait for SIGCHLD */
        }
        if (item->deadline < deadline) deadline = item->deadline;
    }
    return deadline;
}

/* Signals/output are wakeup hints, not a guarantee of observable child status.
 * Only reconcile registered direct children; kernel cleanup on parent death
 * and all earlier deadlines remain independent of this select sleep bound. */
static double reconcile_deadline(double current, double deadline) {
    for (int i = 0; i < worker_count; i++)
        if (!workers[i].reaped && current + 0.05 < deadline) return current + 0.05;
    return deadline;
}

static void loop(int listener) {
    session_deadline = now() + 30;
    double accept_deadline = now() + 5;
    for (;;) {
        #ifndef CONTROL_BSD_TEST
        exceptions();
        #endif
        reap();
        double current = now(), deadline = session_deadline;
        if (current >= session_deadline || (client < 0 && current >= accept_deadline) ||
            (partial_deadline && current >= partial_deadline)) die();
        if (client < 0 && accept_deadline < deadline) deadline = accept_deadline;
        if (partial_deadline && partial_deadline < deadline) deadline = partial_deadline;
        deadline = reconcile_deadline(current, expire_workers(current, deadline));
        if (pending >= 0 && workers[pending].reaped && workers[pending].fd < 0) {
            struct worker *item = &workers[pending];
            result(pending, "exited"); pending = -1;
            control_state(item);
        }
        fd_set reads, writes;
        FD_ZERO(&reads); FD_ZERO(&writes);
        FD_SET(listener, &reads); FD_SET(wakeup[0], &reads);
        int maximum = listener > wakeup[0] ? listener : wakeup[0];
        if (client >= 0) {
            FD_SET(client, &reads);
            if (output_used > output_sent) FD_SET(client, &writes);
            if (client > maximum) maximum = client;
        }
        for (int i = 0; i < worker_count; i++) if (workers[i].fd >= 0) {
            FD_SET(workers[i].fd, &reads);
            if (workers[i].fd > maximum) maximum = workers[i].fd;
        }
        double delay = deadline - now();
        if (delay < 0) delay = 0;
        struct timeval timeout = {.tv_sec = (time_t)delay, .tv_usec = (suseconds_t)((delay - (time_t)delay) * 1e6)};
        int count = select(maximum + 1, &reads, &writes, NULL, &timeout);
        if (count < 0) { if (errno == EINTR) continue; die(); }
        if (client >= 0 && FD_ISSET(client, &reads)) receive();
        if (client >= 0 && FD_ISSET(client, &writes)) {
            ssize_t sent = send(client, output + output_sent, output_used - output_sent, 0);
            if (sent < 0) { if (errno != EAGAIN && errno != EINTR) die(); }
            else if (!sent) die();
            else { output_sent += (size_t)sent; if (output_sent == output_used) output_sent = output_used = 0; }
        }
        if (FD_ISSET(listener, &reads)) {
            int accepted = accept(listener, NULL, NULL);
            if (accepted >= 0) {
                if (client >= 0 || !peer(accepted)) close(accepted);
                else { client = accepted; nonblocking(client); partial_deadline = now() + 1; }
            } else if (errno != EAGAIN && errno != EINTR) die();
        }
        if (FD_ISSET(wakeup[0], &reads)) { char bytes[128]; while (read(wakeup[0], bytes, sizeof(bytes)) > 0) {} }
        for (int i = 0; i < worker_count; i++) if (workers[i].fd >= 0 && FD_ISSET(workers[i].fd, &reads)) drain(&workers[i]);
    }
}

int main(int argc, char **argv) {
    if (argc != 2 || getuid() == 0 || getuid() != geteuid() || !authority(argv[1])) return 2;
    int *fds = NULL;
    size_t count = 0;
    if (launch_activate_socket("control", &fds, &count) || count != 1) return 3;
    int listener = fds[0]; free(fds);
    nonblocking(listener);
    if (pipe(wakeup)) return 4;
    nonblocking(wakeup[0]); nonblocking(wakeup[1]);
    struct sigaction action = {.sa_handler = child_event};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGCHLD, &action, NULL) || signal(SIGPIPE, SIG_IGN) == SIG_ERR) return 5;
    printf("{\"broker\":%d,\"socket_activated\":true}\n", getpid()); fflush(stdout);
    loop(listener);
    return 0;
}
