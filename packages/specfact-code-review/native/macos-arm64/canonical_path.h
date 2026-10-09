#ifndef SPECFACT_CANONICAL_PATH_H
#define SPECFACT_CANONICAL_PATH_H

#include "native_protocol.h"
#include <stdlib.h>
#include <string.h>

/* Protocol bounds do not determine the system realpath allocation size. */
static inline int specfact_canonical_path(const char *path) {
    if (!path || path[0] != '/' || strlen(path) >= SPECFACT_MAX_PATH) return 0;
    char *canonical = realpath(path, NULL);
    if (!canonical) return 0;
    int matches = !strcmp(path, canonical);
    free(canonical);
    return matches;
}

#endif
