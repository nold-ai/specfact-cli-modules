#include <CoreFoundation/CoreFoundation.h>
#include <Security/Security.h>

#include <errno.h>
#include <limits.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc != 3 || !argv[1][0] || !argv[2][0]) return 64;
    errno = 0;
    char *end = NULL;
    long parsed = strtol(argv[1], &end, 10);
    if (errno || !end || *end || parsed <= 0 || parsed > INT_MAX) return 65;
    pid_t pid = (pid_t)parsed;
    CFNumberRef number = CFNumberCreate(NULL, kCFNumberIntType, &pid);
    CFStringRef text = CFStringCreateWithCString(NULL, argv[2], kCFStringEncodingUTF8);
    if (!number || !text) return 66;
    const void *keys[] = {kSecGuestAttributePid};
    const void *values[] = {number};
    CFDictionaryRef attributes = CFDictionaryCreate(NULL, keys, values, 1,
        &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    SecCodeRef code = NULL;
    SecRequirementRef requirement = NULL;
    OSStatus result = attributes
        ? SecCodeCopyGuestWithAttributes(NULL, attributes, kSecCSDefaultFlags, &code)
        : errSecAllocate;
    if (!result) result = SecRequirementCreateWithString(text, kSecCSDefaultFlags, &requirement);
    if (!result) result = SecCodeCheckValidity(code, kSecCSStrictValidate, requirement);
    if (requirement) CFRelease(requirement);
    if (code) CFRelease(code);
    if (attributes) CFRelease(attributes);
    CFRelease(text);
    CFRelease(number);
    return result == errSecSuccess ? 0 : 67;
}
