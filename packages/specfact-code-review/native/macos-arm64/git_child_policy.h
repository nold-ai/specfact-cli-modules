#ifndef SPECFACT_GIT_CHILD_POLICY_H
#define SPECFACT_GIT_CHILD_POLICY_H

#include "native_protocol.h"
#include "canonical_path.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sys/stat.h>

#define SPECFACT_GIT_FIXED_OPTIONS \
    "--no-pager", "-c", "protocol.allow=never", "-c", "core.hooksPath=/dev/null", \
    "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", \
    "-c", "maintenance.auto=false", "-c", "gc.auto=0", "-c", "log.showSignature=false", \
    "-c", "diff.external=", "-c", "diff.ignoreSubmodules=all", "-c", "submodule.recurse=false"

static inline int specfact_git_private_path(const char *value, const char *cwd,
    const struct specfact_request *request, char selected[SPECFACT_MAX_PATH]) {
    int used = value[0] == '/' ? snprintf(selected, SPECFACT_MAX_PATH, "%s", value)
        : snprintf(selected, SPECFACT_MAX_PATH, "%s/%s", cwd, value);
    struct stat info;
    if (used <= 0 || (size_t)used >= SPECFACT_MAX_PATH || !specfact_canonical_path(selected) || stat(selected, &info) || !S_ISDIR(info.st_mode)) return 0;
    const char *roots[] = {request->project, request->output, request->temporary};
    for (size_t i = 0; i < 3; i++) {
        size_t length = strlen(roots[i]);
        if (!strcmp(selected, roots[i]) || (!strncmp(selected, roots[i], length) && selected[length] == '/')) return 1;
    }
    return 0;
}

static inline int specfact_git_query(uint32_t argc, char *const *argv, const char *cwd,
    const struct specfact_request *request) {
    uint32_t index = 0;
    char working[SPECFACT_MAX_PATH];
    if (strlen(cwd) >= sizeof(working)) return 0;
    strcpy(working, cwd);
    while (index < argc) {
        const char *value = argv[index];
        if (!strcmp(value, "--no-pager")) { index++; continue; }
        if (!strcmp(value, "-c") && index + 1 < argc && !strcmp(argv[index + 1], "log.showSignature=false")) {
            index += 2; continue;
        }
        if (!strcmp(value, "--git-dir") || !strcmp(value, "-C") || !strncmp(value, "--git-dir=", 10)) {
            char selected[SPECFACT_MAX_PATH];
            const char *path;
            if (!strncmp(value, "--git-dir=", 10)) { path = value + 10; index++; }
            else { if (index + 1 >= argc) return 0; path = argv[index + 1]; index += 2; }
            if (!*path || !specfact_git_private_path(path, working, request, selected)) return 0;
            if (!strcmp(value, "-C")) strcpy(working, selected);
            continue;
        }
        break;
    }
    if (index == argc) return 0;
    const char *commands[] = {"--version", "version", "describe", "rev-parse", "rev-list", "log", "status",
        "symbolic-ref", "ls-files", "cat-file", "show-ref", "for-each-ref", "diff", "diff-index", "diff-files"};
    int admitted = 0;
    for (size_t i = 0; i < sizeof(commands) / sizeof(commands[0]); i++)
        if (!strcmp(argv[index], commands[i])) admitted = 1;
    if (!admitted) return 0;
    unsigned positional = 0;
    for (uint32_t i = index + 1; i < argc; i++) {
        if (!strcmp(argv[i], "--broken") || !strncmp(argv[i], "--broken=", 9) ||
            !strcmp(argv[i], "--show-signature") || !strncmp(argv[i], "--show-signature=", 17)) return 0;
        if (!strcmp(argv[index], "symbolic-ref")) {
            if (!strcmp(argv[i], "--delete") || !strcmp(argv[i], "-d")) return 0;
            positional += argv[i][0] != '-';
        }
    }
    return strcmp(argv[index], "symbolic-ref") || positional == 1;
}

#endif
