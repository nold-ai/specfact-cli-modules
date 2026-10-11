/* Private worker RPC. Every launch inherits the registered parent's grants.
 * Requests contain program identities and owned handles, never host PIDs. */
#include "git_child_policy.h"

static uint64_t next_stream_allocation = 1;

static int cf_string(CFTypeRef value, char *output, size_t capacity) {
    if (!value || CFGetTypeID(value) != CFStringGetTypeID()) return 0;
    CFStringRef text = (CFStringRef)value;
    for (CFIndex i = 0; i < CFStringGetLength(text); i++)
        if (!CFStringGetCharacterAtIndex(text, i)) return 0;
    return CFStringGetCString(text, output, (CFIndex)capacity, kCFStringEncodingUTF8);
}

static int inherited_path(const struct worker *owner, const char *path) {
    if (!specfact_canonical_path(path)) return 0;
    const char *roots[] = {owner->grant.project, owner->grant.output, owner->grant.temporary};
    for (size_t i = 0; i < 3; i++)
        if (!strcmp(path, roots[i]) || beneath(path, roots[i])) return 1;
    return 0;
}

static int inherited_python_path(const struct worker *owner, const char *paths) {
    size_t count = 0;
    const char *start = paths;
    do {
        const char *end = strchr(start, ':');
        size_t length = end ? (size_t)(end - start) : strlen(start);
        char path[SPECFACT_MAX_PATH];
        struct stat info;
        if (!length || length >= sizeof(path) || ++count > 128) return 0;
        memcpy(path, start, length); path[length] = 0;
        if (!inherited_path(owner, path) || stat(path, &info) || !S_ISDIR(info.st_mode)) return 0;
        if (!end) return 1;
        start = end + 1;
    } while (*start);
    return 0;
}

static const char *uv_offline_names[] = {"UV_OFFLINE", "UV_NO_INDEX", "UV_FIND_LINKS", "UV_CACHE_DIR",
    "UV_PYTHON_DOWNLOADS", "UV_KEYRING_PROVIDER", "UV_LINK_MODE"};

static int uv_offline_setting(const char *name) {
    for (size_t i = 0; i < sizeof(uv_offline_names) / sizeof(uv_offline_names[0]); i++)
        if (!strcmp(name, uv_offline_names[i])) return 1;
    return 0;
}

static int uv_environment(const struct worker *owner, CFDictionaryRef environment) {
    char wheelhouse[SPECFACT_MAX_PATH], cache[SPECFACT_MAX_PATH], value[SPECFACT_WORKER_PAYLOAD];
    int a = snprintf(wheelhouse, sizeof(wheelhouse), "%s/wheelhouse", owner->grant.project);
    int b = snprintf(cache, sizeof(cache), "%s/uv-cache", owner->grant.temporary);
    struct stat info;
    if (a <= 0 || (size_t)a >= sizeof(wheelhouse) || b <= 0 || (size_t)b >= sizeof(cache) ||
        !inherited_path(owner, wheelhouse) || stat(wheelhouse, &info) || !S_ISDIR(info.st_mode)) return 0;
    const char *expected[] = {"1", "1", wheelhouse, cache, "never", "disabled", "copy"};
    for (size_t i = 0; i < sizeof(uv_offline_names) / sizeof(uv_offline_names[0]); i++) {
        CFStringRef key = CFStringCreateWithCString(NULL, uv_offline_names[i], kCFStringEncodingUTF8);
        int valid = key && cf_string(CFDictionaryGetValue(environment, key), value, sizeof(value)) &&
            !strcmp(value, expected[i]);
        if (key) CFRelease(key);
        if (!valid) return 0;
    }
    CFTypeRef prefix = CFDictionaryGetValue(environment, CFSTR("VIRTUAL_ENV"));
    return !prefix || (cf_string(prefix, value, sizeof(value)) && inherited_path(owner, value) &&
        !stat(value, &info) && S_ISDIR(info.st_mode));
}

static int launch_document(const struct worker *owner, const unsigned char *payload, uint32_t length,
    int *stdin_pipe, int *merge_stderr) {
    int valid = 0;
    CFDataRef data = CFDataCreate(NULL, payload, length);
    CFPropertyListRef document = data ? CFPropertyListCreateWithData(NULL, data, kCFPropertyListImmutable, NULL, NULL) : NULL;
    if (!document || CFGetTypeID(document) != CFDictionaryGetTypeID()) goto done;
    CFDictionaryRef fields = (CFDictionaryRef)document;
    if (CFDictionaryGetCount(fields) != 9) goto done;
    char text[SPECFACT_MAX_PATH];
    if (!cf_string(CFDictionaryGetValue(fields, CFSTR("program")), text, sizeof(text))) goto done;
    int uv = !strcmp(text, "uv");
    int git = !strcmp(text, "git");
    if (!uv && !git && strcmp(text, "python")) goto done;
    if (!cf_string(CFDictionaryGetValue(fields, CFSTR("python_prefix")), text, sizeof(text)) ||
        (*text && !inherited_path(owner, text))) goto done;
    int private_prefix = *text != 0;
    if ((uv || git) && private_prefix) goto done;
    if (!cf_string(CFDictionaryGetValue(fields, CFSTR("python_alias")), text, sizeof(text))) goto done;
    if (private_prefix ? (strcmp(text, "python") && strcmp(text, "python3") && strcmp(text, "python3.11") &&
        strcmp(text, "python3.12") && strcmp(text, "python3.13")) : *text) goto done;
    CFTypeRef input = CFDictionaryGetValue(fields, CFSTR("stdin_pipe"));
    CFTypeRef merge = CFDictionaryGetValue(fields, CFSTR("merge_stderr"));
    if (!input || !merge || CFGetTypeID(input) != CFBooleanGetTypeID() || CFGetTypeID(merge) != CFBooleanGetTypeID())
        goto done;
    *stdin_pipe = CFBooleanGetValue(input);
    *merge_stderr = CFBooleanGetValue(merge);
    if (!cf_string(CFDictionaryGetValue(fields, CFSTR("cwd")), text, sizeof(text))) goto done;
    char cwd[SPECFACT_MAX_PATH];
    const char *root = NULL;
    const char *suffix = strchr(text, '/');
    size_t label = suffix ? (size_t)(suffix - text) : strlen(text);
    if (label == 7 && !memcmp(text, "project", label)) root = owner->grant.project;
    if (label == 9 && !memcmp(text, "temporary", label)) root = owner->grant.temporary;
    if (label == 6 && !memcmp(text, "output", label)) root = owner->grant.output;
    if (!root) goto done;
    int used = snprintf(cwd, sizeof(cwd), "%s%s", root, suffix ? suffix : "");
    struct stat info;
    if (used <= 0 || (size_t)used >= sizeof(cwd) || !inherited_path(owner, cwd) ||
        stat(cwd, &info) || !S_ISDIR(info.st_mode)) goto done;
    CFTypeRef args = CFDictionaryGetValue(fields, CFSTR("argv"));
    CFTypeRef paths = CFDictionaryGetValue(fields, CFSTR("python_paths"));
    if (!args || !paths || CFGetTypeID(args) != CFArrayGetTypeID() || CFGetTypeID(paths) != CFArrayGetTypeID() ||
        CFArrayGetCount(args) > 128 || CFArrayGetCount(paths) > 128) goto done;
    if ((uv || git) && (!CFArrayGetCount(args) || CFArrayGetCount(paths))) goto done;
    char git_text[SPECFACT_WORKER_PAYLOAD], *git_args[128];
    size_t git_used = 0;
    for (CFIndex i = 0; i < CFArrayGetCount(args); i++) {
        char argument[SPECFACT_WORKER_PAYLOAD];
        if (!cf_string(CFArrayGetValueAtIndex(args, i), argument, sizeof(argument))) goto done;
        if (!uv && !git && i == 0 && (!strcmp(argument, "-E") || !strcmp(argument, "-S"))) goto done;
        if (git) {
            size_t count = strlen(argument) + 1;
            if (count > sizeof(git_text) - git_used) goto done;
            git_args[i] = git_text + git_used;
            memcpy(git_args[i], argument, count);
            git_used += count;
        }
    }
    if (git && !specfact_git_query((uint32_t)CFArrayGetCount(args), git_args, cwd, &owner->grant)) goto done;
    for (CFIndex i = 0; i < CFArrayGetCount(paths); i++)
        if (!cf_string(CFArrayGetValueAtIndex(paths, i), text, sizeof(text)) || !inherited_path(owner, text)) goto done;
    CFTypeRef env = CFDictionaryGetValue(fields, CFSTR("environment"));
    if (!env || CFGetTypeID(env) != CFDictionaryGetTypeID() || CFDictionaryGetCount(env) > 128) goto done;
    if (uv && !uv_environment(owner, env)) goto done;
    const void *keys[128], *values[128];
    CFDictionaryGetKeysAndValues(env, keys, values);
    for (CFIndex i = 0; i < CFDictionaryGetCount(env); i++) {
        char value[SPECFACT_WORKER_PAYLOAD];
        if (!cf_string(keys[i], text, sizeof(text)) || !cf_string(values[i], value, sizeof(value)) ||
            !*text || strchr(text, '=') || !strncmp(text, "DYLD_", 5) || !strncmp(text, "LD_", 3) ||
            (!strncmp(text, "PYTHON", 6) && !(!strcmp(text, "PYTHONUTF8") && !strcmp(value, "1")) &&
                !(!strcmp(text, "PYTHONPATH") && inherited_python_path(owner, value))) ||
            !strcmp(text, "PATH") || !strcmp(text, "HOME") || !strcmp(text, "TMPDIR"))
            goto done;
        if (uv && (!strncmp(text, "SPECFACT_", 9) || strcasestr(text, "TOKEN") || strcasestr(text, "PASSWORD") ||
            strcasestr(text, "SECRET") || strcasestr(text, "API_KEY") || strcasestr(text, "PROXY") ||
            !strcmp(text, "PYTHONPATH") ||
            (!strncmp(text, "UV_", 3) && !uv_offline_setting(text) &&
                (strcmp(text, "UV_NO_PROGRESS") || strcmp(value, "1"))))) goto done;
    }
    if (git) {
        for (CFIndex i = 0; i < CFDictionaryGetCount(env); i++) {
            if (!cf_string(keys[i], text, sizeof(text)) || !strncmp(text, "GIT_", 4) ||
                !strncmp(text, "SPECFACT_", 9) || !strncmp(text, "UV_", 3) || !strcmp(text, "PYTHONPATH") ||
                !strcmp(text, "XDG_CONFIG_HOME") || !strcmp(text, "LC_ALL") ||
                strcasestr(text, "TOKEN") || strcasestr(text, "PASSWORD") || strcasestr(text, "SECRET") ||
                strcasestr(text, "API_KEY") || strcasestr(text, "PROXY")) goto done;
        }
    }
    valid = git ? 3 : uv ? 2 : 1;
done:
    if (document) CFRelease(document);
    if (data) CFRelease(data);
    return valid;
}

static int startup_text(struct specfact_uv_child_startup *startup, size_t *used, const char *text) {
    size_t length = strlen(text) + 1;
    if (length > sizeof(startup->data) - *used) return 0;
    memcpy(startup->data + *used, text, length);
    *used += length;
    return 1;
}

static int uv_startup_document(const struct worker *owner, const unsigned char *payload, uint32_t length,
    struct specfact_uv_child_startup *startup, uint32_t *startup_length) {
    int valid = 0;
    memset(startup, 0, sizeof(*startup));
    CFDataRef data = CFDataCreate(NULL, payload, length);
    CFPropertyListRef document = data ? CFPropertyListCreateWithData(NULL, data, kCFPropertyListImmutable, NULL, NULL) : NULL;
    if (!document || CFGetTypeID(document) != CFDictionaryGetTypeID()) goto done;
    CFDictionaryRef fields = (CFDictionaryRef)document;
    char text[SPECFACT_WORKER_PAYLOAD], cwd[SPECFACT_MAX_PATH];
    if (!cf_string(CFDictionaryGetValue(fields, CFSTR("cwd")), text, sizeof(text))) goto done;
    const char *suffix = strchr(text, '/');
    size_t label = suffix ? (size_t)(suffix - text) : strlen(text);
    const char *root = label == 7 && !memcmp(text, "project", label) ? owner->grant.project
        : label == 6 && !memcmp(text, "output", label) ? owner->grant.output
        : label == 9 && !memcmp(text, "temporary", label) ? owner->grant.temporary : NULL;
    int count = root ? snprintf(cwd, sizeof(cwd), "%s%s", root, suffix ? suffix : "") : -1;
    size_t used = 0;
    if (count <= 0 || (size_t)count >= sizeof(cwd) || !startup_text(startup, &used, cwd)) goto done;
    CFArrayRef args = (CFArrayRef)CFDictionaryGetValue(fields, CFSTR("argv"));
    startup->argc = (uint32_t)CFArrayGetCount(args);
    for (CFIndex i = 0; i < CFArrayGetCount(args); i++)
        if (!cf_string(CFArrayGetValueAtIndex(args, i), text, sizeof(text)) || !startup_text(startup, &used, text)) goto done;
    CFDictionaryRef env = (CFDictionaryRef)CFDictionaryGetValue(fields, CFSTR("environment"));
    const void *keys[128], *values[128];
    CFDictionaryGetKeysAndValues(env, keys, values);
    for (CFIndex i = 0; i < CFDictionaryGetCount(env); i++) {
        char key[SPECFACT_WORKER_PAYLOAD], value[SPECFACT_WORKER_PAYLOAD];
        if (!cf_string(keys[i], key, sizeof(key)) || !cf_string(values[i], value, sizeof(value))) goto done;
        if (uv_offline_setting(key) || !strcmp(key, "HATCH_UV")) continue;
        count = snprintf(text, sizeof(text), "%s=%s", key, value);
        if (count <= 0 || (size_t)count >= sizeof(text) || !startup_text(startup, &used, text)) goto done;
        startup->envc++;
    }
    *startup_length = (uint32_t)(2 * sizeof(uint32_t) + used);
    valid = 1;
done:
    if (document) CFRelease(document);
    if (data) CFRelease(data);
    return valid;
}

static void worker_reply(struct worker *owner, uint32_t handle, int status, int detail,
    const unsigned char *payload, uint32_t length) {
    if (owner->reply_used || length > SPECFACT_WORKER_STREAM) die();
    struct specfact_reply response = {
        .magic = SPECFACT_WORKER_MAGIC, .version = 1, .status = detail ? 1 : 0,
        .handle = handle, .wait_status = status, .detail = detail ? (uint32_t)detail : length,
    };
    memcpy(owner->rpc_reply, &response, sizeof(response));
    if (length) memcpy(owner->rpc_reply + sizeof(response), payload, length);
    owner->reply_used = sizeof(response) + length;
    owner->reply_sent = 0;
}

static void child_launch(const char *capsule, int control, struct worker *owner,
    const unsigned char *payload, uint32_t length) {
    int stdin_pipe = 0, merge = 0;
    int program = launch_document(owner, payload, length, &stdin_pipe, &merge);
    if (!program || owner->reaped) {
        worker_reply(owner, 0, -1, EINVAL, NULL, 0); return;
    }
    struct worker *child = free_worker();
    if (!child) { worker_reply(owner, 0, -1, EAGAIN, NULL, 0); return; }
    struct specfact_request request = owner->grant;
    request.plan = program == 3 ? SPECFACT_GIT_CHILD_PLAN : program == 2 ? SPECFACT_UV_CHILD_PLAN : SPECFACT_PYTHON_CHILD_PLAN;
    struct specfact_uv_child_startup startup;
    if (program == 2 || program == 3) {
        uint32_t startup_length = 0;
        if (!uv_startup_document(owner, payload, length, &startup, &startup_length)) {
            worker_reply(owner, 0, -1, EINVAL, NULL, 0); return;
        }
        payload = (const unsigned char *)&startup;
        length = startup_length;
    }
    char stream_name[96];
    if (!next_stream_allocation) die();
    int count = snprintf(stream_name, sizeof(stream_name), ".specfact-managed-%llu",
        (unsigned long long)next_stream_allocation++);
    if (count <= 0 || (size_t)count >= sizeof(stream_name) || mkdirat(owner->temporary_fd, stream_name, 0700)) {
        worker_reply(owner, 0, -1, EINVAL, NULL, 0); return;
    }
    int directory = openat(owner->temporary_fd, stream_name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
    if (directory < 0) { worker_reply(owner, 0, -1, EINVAL, NULL, 0); return; }
    int input[2] = {-1, -1};
    if (stdin_pipe && pipe(input)) {
        close(directory); unlinkat(owner->temporary_fd, stream_name, AT_REMOVEDIR);
        worker_reply(owner, 0, -1, errno, NULL, 0); return;
    }
    int outcome = launch_worker(capsule, control, &request, child, owner->handle, payload, length, input[0], merge, directory);
    close(directory);
    if (input[0] >= 0) close(input[0]);
    if (outcome) {
        if (input[1] >= 0) close(input[1]);
        (void)unlinkat(owner->temporary_fd, stream_name, AT_REMOVEDIR);
        worker_reply(owner, 0, -1, ECHILD, NULL, 0); return;
    }
    child->io_in = input[1];
    if (input[1] >= 0 && fcntl(input[1], F_SETFL, O_NONBLOCK)) die();
    worker_reply(owner, child->handle, -1, 0, NULL, 0);
}

static void worker_operation(const char *capsule, int control, struct worker *owner,
    const struct specfact_worker_request *request, const unsigned char *payload) {
    if (request->opcode == 1) {
        if (request->handle || !request->length) worker_reply(owner, 0, -1, EINVAL, NULL, 0);
        else child_launch(capsule, control, owner, payload, request->length);
        return;
    }
    struct worker *child = find_worker(request->handle);
    if (!child || child->parent != owner->handle) {
        worker_reply(owner, request->handle, -1, ESRCH, NULL, 0); return;
    }
    int status = child->reaped ? child->status : -1;
    if (request->opcode == 2 && !request->length) worker_reply(owner, child->handle, status, 0, NULL, 0);
    else if (request->opcode == 3 && request->length == sizeof(uint32_t)) {
        uint32_t number;
        memcpy(&number, payload, sizeof(number));
        if (number != SIGINT && number != SIGTERM && number != SIGKILL)
            worker_reply(owner, child->handle, status, EINVAL, NULL, 0);
        else {
            if (!child->reaped) (void)kill(child->pid, (int)number);
            worker_reply(owner, child->handle, status, 0, NULL, 0);
        }
    } else if ((request->opcode == 4 || request->opcode == 5) && request->length == sizeof(uint32_t)) {
        uint32_t requested;
        memcpy(&requested, payload, sizeof(requested));
        if (requested > SPECFACT_WORKER_STREAM) { worker_reply(owner, child->handle, status, EINVAL, NULL, 0); return; }
        int stream = request->opcode == 4 ? child->io_out : child->io_err;
        off_t *offset = request->opcode == 4 ? &child->stdout_offset : &child->stderr_offset;
        struct stat out, err;
        if (fstat(child->io_out, &out) || fstat(child->io_err, &err) || out.st_size < 0 || err.st_size < 0 ||
            (uint64_t)out.st_size > child->output_budget ||
            (uint64_t)err.st_size > child->output_budget - (uint64_t)out.st_size) {
            stop_worker(child); worker_reply(owner, request->handle, -1, EFBIG, NULL, 0); return;
        }
        unsigned char bytes[SPECFACT_WORKER_STREAM];
        ssize_t used = pread(stream, bytes, requested, *offset);
        if (used < 0) worker_reply(owner, child->handle, status, errno, NULL, 0);
        else { *offset += used; worker_reply(owner, child->handle, status, 0, bytes, (uint32_t)used); }
    } else if (request->opcode == 6 && request->length && child->io_in >= 0) {
        ssize_t used = write(child->io_in, payload, request->length);
        if (used < 0 && (errno == EAGAIN || errno == EINTR)) used = 0;
        worker_reply(owner, child->handle, used < 0 ? -1 : (int)used, used < 0 ? errno : 0, NULL, 0);
    } else if (request->opcode == 7 && !request->length) {
        if (child->io_in >= 0) close(child->io_in);
        child->io_in = -1;
        worker_reply(owner, child->handle, status, 0, NULL, 0);
    } else if (request->opcode == 8 && !request->length && child->reaped) {
        retire_worker(child);
        worker_reply(owner, request->handle, status, 0, NULL, 0);
    } else worker_reply(owner, child->handle, status, ENOTSUP, NULL, 0);
}

static void service_workers(const char *capsule, int control) {
    for (size_t i = 0; i < SPECFACT_MAX_WORKERS; i++) {
        struct worker *owner = &workers[i];
        if (!owner->active) continue;
        if (!owner->reaped) {
            int status = 0;
            pid_t result = waitpid(owner->pid, &status, WNOHANG);
            if (result == owner->pid && (WIFEXITED(status) || WIFSIGNALED(status))) {
                owner->reaped = 1;
                owner->status = status;
                stop_children(owner->handle);
            } else if (result < 0 && errno != EINTR) die();
        }
        if (owner->reaped) continue;
        if (owner->reply_used) {
            ssize_t used = write(owner->rpc_out, owner->rpc_reply + owner->reply_sent,
                owner->reply_used - owner->reply_sent);
            if (used > 0) owner->reply_sent += (size_t)used;
            else if (used < 0 && errno != EAGAIN && errno != EINTR) { stop_worker(owner); continue; }
            if (owner->reply_sent == owner->reply_used) owner->reply_sent = owner->reply_used = 0;
            continue;
        }
        size_t desired = sizeof(struct specfact_worker_request);
        struct specfact_worker_request request;
        if (owner->rpc_used >= sizeof(request)) {
            memcpy(&request, owner->rpc_buffer, sizeof(request));
            if (request.magic != SPECFACT_WORKER_MAGIC || request.version != 1 ||
                request.opcode < 1 || request.opcode > 8 || request.length > SPECFACT_WORKER_PAYLOAD) {
                stop_worker(owner); continue;
            }
            desired += request.length;
        }
        if (owner->rpc_used < desired) {
            ssize_t used = read(owner->rpc_in, owner->rpc_buffer + owner->rpc_used, desired - owner->rpc_used);
            if (used > 0) owner->rpc_used += (size_t)used;
            else if (!used) { stop_children(owner->handle); continue; }
            else if (errno != EAGAIN && errno != EINTR) { stop_worker(owner); continue; }
        }
        if (owner->rpc_used != desired || owner->rpc_used < sizeof(request)) continue;
        memcpy(&request, owner->rpc_buffer, sizeof(request));
        if (request.magic != SPECFACT_WORKER_MAGIC || request.version != 1 ||
            request.opcode < 1 || request.opcode > 8 || request.length > SPECFACT_WORKER_PAYLOAD) {
            stop_worker(owner); continue;
        }
        if (desired == sizeof(request) && request.length) continue;
        worker_operation(capsule, control, owner, &request, owner->rpc_buffer + sizeof(request));
        owner->rpc_used = 0;
    }
}
