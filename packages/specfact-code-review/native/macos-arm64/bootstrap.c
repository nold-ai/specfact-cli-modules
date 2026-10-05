#include "native_protocol.h"
#include "git_child_policy.h"

#include <errno.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <mach/mach.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>

typedef int (*sandbox_init_type)(const char *, uint64_t, const char *const *, char **);

#define SPECFACT_PROFILE_ANCESTORS 16

static int exact_read(int fd, void *buffer, size_t length) {
    unsigned char *cursor = buffer;
    while (length) {
        ssize_t count = read(fd, cursor, length);
        if (count <= 0) return -1;
        cursor += count;
        length -= (size_t)count;
    }
    return 0;
}

static int bounded_path(const char value[SPECFACT_MAX_PATH]) {
    return memchr(value, '\0', SPECFACT_MAX_PATH) != NULL && value[0] == '/' &&
           strstr(value, "/../") == NULL && strstr(value, "/./") == NULL;
}

static int apply_limits(const struct specfact_request *request) {
    struct rlimit limit;
    limit.rlim_cur = limit.rlim_max = request->open_files;
    if (setrlimit(RLIMIT_NOFILE, &limit)) return -1;
    limit.rlim_cur = limit.rlim_max = request->file_size_bytes;
    if (setrlimit(RLIMIT_FSIZE, &limit)) return -1;
    mach_task_basic_info_data_t info;
    mach_msg_type_number_t count = MACH_TASK_BASIC_INFO_COUNT;
    if (task_info(mach_task_self(), MACH_TASK_BASIC_INFO, (task_info_t)&info, &count) != KERN_SUCCESS ||
        count != MACH_TASK_BASIC_INFO_COUNT || UINT64_MAX - info.virtual_size < request->address_space_bytes) return -1;
    limit.rlim_cur = limit.rlim_max = info.virtual_size + request->address_space_bytes;
    return setrlimit(RLIMIT_AS, &limit);
}

static int append_ancestors(
    const char *path,
    char ancestors[SPECFACT_PROFILE_ANCESTORS][SPECFACT_MAX_PATH],
    size_t *count
) {
    size_t length = strlen(path);
    for (size_t offset = 1; offset < length; offset++) {
        if (path[offset] != '/') continue;
        int duplicate = 0;
        for (size_t index = 0; index < *count; index++) {
            if (strlen(ancestors[index]) == offset && !memcmp(ancestors[index], path, offset)) {
                duplicate = 1;
                break;
            }
        }
        if (duplicate) continue;
        if (*count == SPECFACT_PROFILE_ANCESTORS || offset >= SPECFACT_MAX_PATH) return -1;
        memcpy(ancestors[*count], path, offset);
        ancestors[*count][offset] = '\0';
        (*count)++;
    }
    return 0;
}

static char *startup_string(unsigned char **cursor, unsigned char *end) {
    if (*cursor >= end) return NULL;
    unsigned char *terminator = memchr(*cursor, 0, (size_t)(end - *cursor));
    if (!terminator) return NULL;
    char *text = (char *)*cursor;
    *cursor = terminator + 1;
    return text;
}

static int native_child_execute(int fd, const struct specfact_request *request, const char *capsule, const char *tool) {
    struct specfact_child_envelope envelope;
    struct specfact_uv_child_startup startup;
    if (exact_read(fd, &envelope, sizeof(envelope)) || envelope.length <= 2 * sizeof(uint32_t) ||
        envelope.length > sizeof(startup) || exact_read(fd, &startup, envelope.length)) return 76;
    close(fd); /* Project/build code never receives startup configuration. */
    if (!startup.argc || startup.argc > 128 || startup.envc > 128) return 76;
    unsigned char *cursor = startup.data, *end = (unsigned char *)&startup + envelope.length;
    char *cwd = startup_string(&cursor, end), canonical[SPECFACT_MAX_PATH];
    struct stat info;
    if (!cwd || !realpath(cwd, canonical) || strcmp(cwd, canonical) || stat(cwd, &info) || !S_ISDIR(info.st_mode)) return 76;
    const char *roots[] = {request->project, request->output, request->temporary};
    int private_cwd = 0;
    for (size_t i = 0; i < 3; i++) {
        size_t length = strlen(roots[i]);
        if (!strcmp(cwd, roots[i]) || (!strncmp(cwd, roots[i], length) && cwd[length] == '/')) private_cwd = 1;
    }
    if (!private_cwd || chdir(cwd)) return 76;
    char *arguments[130] = {(char *)tool};
    for (uint32_t i = 0; i < startup.argc; i++)
        if (!(arguments[i + 1] = startup_string(&cursor, end))) return 76;
    arguments[startup.argc + 1] = NULL;
    char *environment[146];
    for (uint32_t i = 0; i < startup.envc; i++)
        if (!(environment[i] = startup_string(&cursor, end))) return 76;
    if (cursor != end) return 76;
    if (request->plan == SPECFACT_GIT_CHILD_PLAN) {
        if (!specfact_git_query(startup.argc, arguments + 1, cwd, request)) return 76;
        for (uint32_t i = 0; i < startup.envc; i++)
            if (!strncmp(environment[i], "GIT_", 4) || !strncmp(environment[i], "PATH=", 5) ||
                !strncmp(environment[i], "HOME=", 5) || !strncmp(environment[i], "TMPDIR=", 7) ||
                !strncmp(environment[i], "XDG_CONFIG_HOME=", 16) || !strncmp(environment[i], "LC_ALL=", 7)) return 76;
        char *fixed_options[] = {SPECFACT_GIT_FIXED_OPTIONS};
        size_t option_count = sizeof(fixed_options) / sizeof(fixed_options[0]);
        char *git_arguments[160] = {(char *)tool};
        for (size_t i = 0; i < option_count; i++) git_arguments[i + 1] = fixed_options[i];
        for (uint32_t i = 0; i < startup.argc; i++) git_arguments[1 + option_count + i] = arguments[i + 1];
        git_arguments[1 + option_count + startup.argc] = NULL;
        const char *names[] = {"HOME", "TMPDIR", "XDG_CONFIG_HOME", "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_SYSTEM", "GIT_OPTIONAL_LOCKS", "GIT_TERMINAL_PROMPT", "GIT_NO_LAZY_FETCH",
            "GIT_PROTOCOL_FROM_USER", "GIT_ALLOW_PROTOCOL", "GIT_PAGER", "GIT_EXEC_PATH", "LC_ALL"};
        const char *values[] = {request->temporary, request->temporary, request->temporary, "1", "/dev/null",
            "/dev/null", "0", "0", "1", "0", "", "/dev/null", "/nonexistent/specfact-managed-git", "C"};
        char fixed[14][SPECFACT_MAX_PATH + 40];
        for (size_t i = 0; i < 14; i++) {
            int used = snprintf(fixed[i], sizeof(fixed[i]), "%s=%s", names[i], values[i]);
            if (used <= 0 || (size_t)used >= sizeof(fixed[i])) return 76;
            environment[startup.envc + i] = fixed[i];
        }
        environment[startup.envc + 14] = NULL;
        close(5); close(6); /* Git has no managed child bridge. */
        execve(tool, git_arguments, environment);
        return errno == ENOENT ? 74 : 75;
    }
    char wheelhouse[SPECFACT_MAX_PATH], cache[SPECFACT_MAX_PATH], python[SPECFACT_MAX_PATH];
    int a = snprintf(wheelhouse, sizeof(wheelhouse), "%s/wheelhouse", request->project);
    int b = snprintf(cache, sizeof(cache), "%s/uv-cache", request->temporary);
    int c = snprintf(python, sizeof(python), "%s/python/bin/python3", capsule);
    if (a <= 0 || (size_t)a >= sizeof(wheelhouse) || b <= 0 || (size_t)b >= sizeof(cache) ||
        c <= 0 || (size_t)c >= sizeof(python)) return 76;
    const char *names[] = {"HOME", "TMPDIR", "XDG_CACHE_HOME", "SPECFACT_MANAGED_UV", "SPECFACT_MANAGED_CAPSULE",
        "SPECFACT_MANAGED_PROJECT", "SPECFACT_MANAGED_OUTPUT", "SPECFACT_MANAGED_TEMPORARY", "UV_OFFLINE", "UV_NO_INDEX",
        "UV_FIND_LINKS", "UV_CACHE_DIR", "UV_PYTHON_DOWNLOADS", "UV_KEYRING_PROVIDER", "UV_LINK_MODE", "UV_PYTHON", "HATCH_UV"};
    const char *values[] = {request->temporary, request->temporary, request->temporary, "1", capsule,
        request->project, request->output, request->temporary, "1", "1", wheelhouse, cache, "never", "disabled", "copy", python, tool};
    char fixed[17][SPECFACT_MAX_PATH + 40];
    for (size_t i = 0; i < 17; i++) {
        int used = snprintf(fixed[i], sizeof(fixed[i]), "%s=%s", names[i], values[i]);
        if (used <= 0 || (size_t)used >= sizeof(fixed[i])) return 76;
        environment[startup.envc + i] = fixed[i];
    }
    environment[startup.envc + 17] = NULL;
    execve(tool, arguments, environment);
    return errno == ENOENT ? 74 : 75;
}

int main(int argc, char **argv) {
    if (argc != 5 || strcmp(argv[1], "--request-fd") || strcmp(argv[3], "--marker-fd")) return 64;
    int request_fd = atoi(argv[2]);
    int marker_fd = atoi(argv[4]);
    struct specfact_request request;
    if (request_fd < 3 || marker_fd < 0 || request_fd == marker_fd ||
        exact_read(request_fd, &request, sizeof(request))) return 65;
    if (request.magic != SPECFACT_MAGIC || request.version != SPECFACT_PROTOCOL_VERSION ||
        request.opcode != SPECFACT_LAUNCH || request.plan < 1 || request.plan > SPECFACT_MAX_PLAN ||
        !bounded_path(request.invocation) || !bounded_path(request.project) ||
        !bounded_path(request.output) || !bounded_path(request.temporary)) return 66;
    if (ptrace(PT_TRACE_ME, 0, NULL, 0) || ptrace(PT_SIGEXC, 0, NULL, 0)) return 67;
    if (apply_limits(&request)) return 68;

    const char *capsule = getenv("SPECFACT_CAPSULE_ROOT");
    const char *target_path = getenv("SPECFACT_FIXED_TARGET");
    const char *tool_path = getenv("SPECFACT_FIXED_TOOL");
    const char *profile_path = getenv("SPECFACT_FIXED_PROFILE");
    if (!capsule || !target_path || !tool_path || !profile_path) return 69;
    int profile_fd = open(profile_path, O_RDONLY | O_NOFOLLOW);
    char profile[4096];
    ssize_t profile_size = profile_fd < 0 ? -1 : read(profile_fd, profile, sizeof(profile) - 1);
    if (profile_fd >= 0) close(profile_fd);
    if (profile_size <= 0 || (size_t)profile_size >= sizeof(profile) - 1) return 69;
    profile[profile_size] = '\0';
    const char *parameters[2 * 24 + 1] = {
        "CAPSULE", capsule, "PROJECT", request.project, "OUTPUT", request.output,
        "TEMPORARY", request.temporary, "PYTHON", target_path, "TOOL", tool_path,
        "INVOCATION", request.invocation, NULL,
    };
    char ancestor_names[SPECFACT_PROFILE_ANCESTORS][24];
    char ancestors[SPECFACT_PROFILE_ANCESTORS][SPECFACT_MAX_PATH];
    size_t ancestor_count = 0;
    if (append_ancestors(capsule, ancestors, &ancestor_count) ||
        append_ancestors(request.invocation, ancestors, &ancestor_count)) return 69;
    for (size_t index = 0; index < ancestor_count; index++) {
        snprintf(ancestor_names[index], sizeof(ancestor_names[index]), "ANCESTOR%zu", index);
        parameters[14 + 2 * index] = ancestor_names[index];
        parameters[15 + 2 * index] = ancestors[index];
    }
    while (ancestor_count < SPECFACT_PROFILE_ANCESTORS) {
        snprintf(ancestor_names[ancestor_count], sizeof(ancestor_names[ancestor_count]), "ANCESTOR%zu", ancestor_count);
        parameters[14 + 2 * ancestor_count] = ancestor_names[ancestor_count];
        parameters[15 + 2 * ancestor_count] = "/";
        ancestor_count++;
    }
    parameters[46] = "ACQUISITION";
    parameters[47] = request.plan == 23 || request.plan == SPECFACT_UV_ACQUISITION_PLAN ? "1" : "0";
    parameters[48] = NULL;
    void *sandbox_library = dlopen("/usr/lib/libsandbox.dylib", RTLD_NOW | RTLD_LOCAL);
    sandbox_init_type sandbox_init = sandbox_library ? (sandbox_init_type)dlsym(sandbox_library, "sandbox_init_with_parameters") : NULL;
    if (!sandbox_init) return 70;
    char *error = NULL;
    if (sandbox_init(profile, 0, parameters, &error)) return 70;
    uint32_t marker = SPECFACT_MARKER_READY;
    if (write(marker_fd, &marker, sizeof(marker)) != sizeof(marker)) return 71;
    if (raise(SIGSTOP)) return 72;
    int managed_child = request.plan == SPECFACT_PYTHON_CHILD_PLAN || request.plan == SPECFACT_UV_CHILD_PLAN ||
        request.plan == SPECFACT_GIT_CHILD_PLAN;
    if (!managed_child) close(request_fd);
    close(marker_fd);
    long descriptor_limit = sysconf(_SC_OPEN_MAX);
    if (descriptor_limit < 3 || descriptor_limit > 4096) descriptor_limit = 4096;
    for (int descriptor = 3; descriptor < descriptor_limit; descriptor++)
        if (descriptor != 5 && descriptor != 6 && !(descriptor == 3 && managed_child))
            close(descriptor);
    for (int descriptor = 0; descriptor <= 6; descriptor++) {
        if (descriptor == 4 || (descriptor == 3 && !managed_child)) continue;
        int flags = fcntl(descriptor, F_GETFD);
        if (flags < 0 || fcntl(descriptor, F_SETFD, flags & ~FD_CLOEXEC)) return 73;
    }
    if (chdir(request.project)) return 73;
    if (request.plan == SPECFACT_UV_CHILD_PLAN || request.plan == SPECFACT_GIT_CHILD_PLAN)
        return native_child_execute(request_fd, &request, capsule, tool_path);

    static const char *tools[] = {"ruff", "radon", "semgrep", "basedpyright", "pylint", "crosshair", "pytest"};
    static const char *managers[] = {"pip", "hatch", "uv", "poetry"};
    const char *tool = request.plan >= 12 && request.plan <= 18 ? tools[request.plan - 12] : NULL;
    const char *manager = request.plan >= 19 && request.plan <= 22 ? managers[request.plan - 19] : NULL;
    char *analyzer_target[] = {
        (char *)target_path, "-I", "-B", "-m", "specfact_code_review.run.native_worker",
        (char *)capsule, request.project, request.output, request.temporary, NULL,
    };
    char *tool_target[] = {
        (char *)target_path, "-I", "-B", "-m", "specfact_code_review.run.native_tool_worker",
        (char *)capsule, request.project, request.output, request.temporary, (char *)tool, NULL,
    };
    char *project_target[] = {
        (char *)target_path, "-I", "-B", "-m", "specfact_code_review.run.native_project_manager",
        (char *)capsule, request.project, request.output, request.temporary, (char *)manager, NULL,
    };
    char *pip_target[] = {
        (char *)target_path, "-I", "-B", "-m", "specfact_code_review.run.native_project_pip",
        (char *)capsule, request.project, request.output, request.temporary,
        request.plan == 23 ? "acquire" : request.plan == 26 ? "inspect" : "install", NULL,
    };
    char *build_target[] = {
        (char *)target_path, "-I", "-B", "-m", "specfact_code_review.run.native_project_hooks",
        (char *)capsule, request.project, request.output, request.temporary, NULL,
    };
    char *self_test_target[] = {(char *)target_path, request.temporary, NULL};
    char *child_target[] = {
        (char *)target_path, "-I", "-B", "-m", "specfact_code_review.run.native_child_worker",
        (char *)capsule, request.project, request.output, request.temporary, NULL,
    };
    char *uv_target[] = {
        (char *)target_path, "-I", "-B", "-m", "specfact_code_review.run.native_project_uv",
        (char *)capsule, request.project, request.output, request.temporary, NULL,
    };
    char *const environment[] = {
        "LANG=C.UTF-8", "LC_ALL=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1",
        "PYTHONHASHSEED=0", "PYTHONUTF8=1", NULL,
    };
    char **arguments = request.plan == SPECFACT_UV_ACQUISITION_PLAN ? uv_target : request.plan == 1 ? self_test_target
        : request.plan <= 11 ? analyzer_target : request.plan <= 18 ? tool_target
        : request.plan <= 22 ? project_target : request.plan == 25 ? build_target
        : request.plan == SPECFACT_PYTHON_CHILD_PLAN ? child_target : pip_target;
    execve(target_path, arguments, environment);
    return errno == ENOENT ? 74 : 75;
}
