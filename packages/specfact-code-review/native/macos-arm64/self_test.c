#include <mach/mach.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int exception_port_probe(const char *directory) {
    char path[1024];
    int length = snprintf(path, sizeof(path), "%s/exception-port-probe", directory);
    if (length < 1 || (size_t)length >= sizeof(path)) return -1;
    if (access(path, F_OK)) return 0;
    exception_mask_t masks[EXC_TYPES_COUNT];
    mach_port_t ports[EXC_TYPES_COUNT];
    exception_behavior_t behaviors[EXC_TYPES_COUNT];
    thread_state_flavor_t flavors[EXC_TYPES_COUNT];
    mach_msg_type_number_t count = EXC_TYPES_COUNT;
    mach_port_t thread = mach_thread_self();
    kern_return_t task_set = task_set_exception_ports(mach_task_self(), EXC_MASK_SOFTWARE,
        MACH_PORT_NULL, EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE);
    kern_return_t task_swap = task_swap_exception_ports(mach_task_self(), EXC_MASK_SOFTWARE,
        MACH_PORT_NULL, EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE,
        masks, &count, ports, behaviors, flavors);
    count = EXC_TYPES_COUNT;
    kern_return_t thread_set = thread_set_exception_ports(thread, EXC_MASK_SOFTWARE,
        MACH_PORT_NULL, EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE);
    kern_return_t thread_swap = thread_swap_exception_ports(thread, EXC_MASK_SOFTWARE,
        MACH_PORT_NULL, EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES, THREAD_STATE_NONE,
        masks, &count, ports, behaviors, flavors);
    mach_port_deallocate(mach_task_self(), thread);
    length = snprintf(path, sizeof(path), "%s/exception-port-results.json", directory);
    if (length < 1 || (size_t)length >= sizeof(path)) return -1;
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (fd < 0) return -1;
    char results[128];
    length = snprintf(results, sizeof(results), "[%d,%d,%d,%d]\n", task_set, task_swap, thread_set, thread_swap);
    int failed = length < 1 || (size_t)length >= sizeof(results) || write(fd, results, (size_t)length) != length;
    close(fd);
    return failed ? -1 : 0;
}

int main(int argc, char **argv) {
    if (argc != 2) return 64;
    if (exception_port_probe(argv[1])) return 62;
    static const char standard_output[] = "specfact-native-stdout-v1\n";
    static const char standard_error[] = "specfact-native-stderr-v1\n";
    ssize_t stdout_count = write(STDOUT_FILENO, standard_output, sizeof(standard_output) - 1);
    int stdout_error = errno;
    ssize_t stderr_count = write(STDERR_FILENO, standard_error, sizeof(standard_error) - 1);
    int stderr_error = errno;
    if (stdout_count != sizeof(standard_output) - 1 || stderr_count != sizeof(standard_error) - 1) {
        char diagnostic_path[1024], diagnostic[128];
        int path_count = snprintf(diagnostic_path, sizeof(diagnostic_path), "%s/descriptor-error", argv[1]);
        int diagnostic_count = snprintf(diagnostic, sizeof(diagnostic), "stdout=%zd:%d stderr=%zd:%d\n",
            stdout_count, stdout_error, stderr_count, stderr_error);
        if (path_count > 0 && (size_t)path_count < sizeof(diagnostic_path) &&
            diagnostic_count > 0 && (size_t)diagnostic_count < sizeof(diagnostic)) {
            int diagnostic_fd = open(diagnostic_path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
            if (diagnostic_fd >= 0) {
                (void)write(diagnostic_fd, diagnostic, (size_t)diagnostic_count);
                close(diagnostic_fd);
            }
        }
        return 63;
    }
    if (strstr(argv[1], "/../") || argv[1][0] != '/') return 65;
    char output[1024];
    int count = snprintf(output, sizeof(output), "%s/native-self-test", argv[1]);
    if (count <= 0 || (size_t)count >= sizeof(output)) return 66;
    int fd = open(output, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (fd < 0) return 67;
    static const char message[] = "specfact-native-self-test-v1\n";
    int result = write(fd, message, sizeof(message) - 1) == sizeof(message) - 1 ? 37 : 68;
    close(fd);
    char pid_path[1024], pid_text[32];
    count = snprintf(pid_path, sizeof(pid_path), "%s/native-self-test.pid", argv[1]);
    int pid_count = snprintf(pid_text, sizeof(pid_text), "%d\n", getpid());
    if (count <= 0 || (size_t)count >= sizeof(pid_path) || pid_count <= 0 ||
        (size_t)pid_count >= sizeof(pid_text)) return 69;
    fd = open(pid_path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (fd < 0 || write(fd, pid_text, (size_t)pid_count) != pid_count) return 70;
    close(fd);
    char hold[1024];
    count = snprintf(hold, sizeof(hold), "%s/hold", argv[1]);
    if (count <= 0 || (size_t)count >= sizeof(hold)) return 71;
    if (!access(hold, F_OK)) {
        signal(SIGTERM, SIG_IGN);
        for (;;) pause();
    }
    return result;
}
