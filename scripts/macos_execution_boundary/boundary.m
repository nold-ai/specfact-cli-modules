/* Compile twice with ARC/Foundation; define SERVICE for the embedded XPC service.
 * Bundle resource: fixture. Override BOUNDARY_SERVICE_NAME to match its bundle ID.
 * Signing/entitlements belong to the build runner, never to this source.
 */
#import <Foundation/Foundation.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef BOUNDARY_SERVICE_NAME
#define BOUNDARY_SERVICE_NAME "ai.nold.specfact.boundary.runner"
#endif

@protocol BoundaryEvents
- (void)finished:(NSDictionary *)receipt;
@end

@protocol BoundaryV1
- (void)start:(NSString *)mode output:(NSFileHandle *)output
    directory:(NSString *)directory timeout:(BOOL)timeout
    reply:(void (^)(NSDictionary *))reply;
- (void)cancel:(void (^)(NSDictionary *))reply;
@end

#ifndef SERVICE
static void printJSON(NSDictionary *record) {
    NSData *data = [NSJSONSerialization dataWithJSONObject:record options:0 error:NULL];
    if (!data) return;
    NSMutableData *line = [data mutableCopy];
    [line appendBytes:"\n" length:1];
    ssize_t result;
    do { result = write(STDOUT_FILENO, line.bytes, line.length); }
    while (result < 0 && errno == EINTR);
}

#endif

static NSDictionary *failure(NSString *reason, int error) {
    return @{ @"version": @1, @"event": @"error", @"ok": @NO,
              @"reason": reason, @"errno": @(error), @"pid": @(getpid()) };
}

#ifdef SERVICE

@interface BoundaryService : NSObject <BoundaryV1>
@property(nonatomic, strong) NSXPCConnection *connection;
@property(nonatomic, strong) dispatch_queue_t queue;
@property(nonatomic, strong) dispatch_source_t timer;
@property(nonatomic) BOOL started;
@property(nonatomic) pid_t root;
@property(nonatomic) uint64_t deadline;
@property(nonatomic, strong) NSDictionary *receipt;
- (void)disconnected;
@end

@implementation BoundaryService
- (instancetype)init {
    self = [super init];
    if (self) _queue = dispatch_queue_create("org.specfact.boundary.state", DISPATCH_QUEUE_SERIAL);
    return self;
}

- (NSDictionary *)finish:(NSString *)reason status:(int)status error:(int)error reaped:(BOOL)reaped {
    if (self.receipt) return self.receipt;
    self.receipt = @{ @"version": @1, @"event": @"receipt", @"reason": reason,
        @"ok": (error == 0 && (![reason isEqualToString:@"exit"] || status == 0)) ? @YES : @NO, @"errno": @(error), @"service_pid": @(getpid()),
        @"root_pid": @(self.root), @"wait_status": @(status),
        @"root_reaped": @(reaped), @"descendants_guaranteed": @NO };
    self.root = 0;
    if (self.timer) { dispatch_source_cancel(self.timer); self.timer = nil; }
    return self.receipt;
}

- (NSDictionary *)stop:(NSString *)reason {
    if (self.receipt) return self.receipt;
    if (self.root <= 0) return failure(@"not_started", EINVAL);
    /* The direct child has not been reaped: its PID cannot have been reused.
     * This addresses only the original group; detached descendants may survive. */
    int error = 0;
    if (killpg(self.root, SIGKILL) != 0 && errno != ESRCH) error = errno;
    if (kill(self.root, SIGKILL) != 0 && errno != ESRCH && error == 0) error = errno;
    int status = 0;
    pid_t waited;
    do { waited = waitpid(self.root, &status, 0); } while (waited < 0 && errno == EINTR);
    if (waited < 0) error = errno;
    return [self finish:reason status:status error:error reaped:(waited > 0)];
}

- (void)notify:(NSDictionary *)receipt {
    id<BoundaryEvents> peer = [self.connection remoteObjectProxyWithErrorHandler:^(NSError *error) {
        (void)error; /* An independent observer must notice a missing receipt. */
    }];
    [peer finished:receipt];
}

- (void)start:(NSString *)mode output:(NSFileHandle *)output
    directory:(NSString *)directory timeout:(BOOL)timeout
    reply:(void (^)(NSDictionary *))reply {
    dispatch_async(self.queue, ^{
        if (self.started) { reply(failure(@"second_start", EALREADY)); return; }
        self.started = YES;
        NSSet *modes = [NSSet setWithArray:@[@"normal", @"child", @"fork-detach",
            @"double-fork", @"spawn-detach", @"vfork-detach"]];
        if (![modes containsObject:mode] || !directory.isAbsolutePath || !output) {
            reply(failure(@"invalid_request", EINVAL)); return;
        }
        NSString *fixture = [[NSBundle mainBundle] pathForResource:@"fixture" ofType:nil];
        if (!fixture) { reply(failure(@"missing_bundled_fixture", ENOENT)); return; }
        NSString *home = [@"HOME=" stringByAppendingString:directory];
        NSString *temporary = [@"TMPDIR=" stringByAppendingString:directory];
        char *environment[] = {"PATH=/usr/bin:/bin", (char *)home.UTF8String,
            (char *)temporary.UTF8String, NULL};
        char *arguments[] = {(char *)fixture.fileSystemRepresentation, (char *)mode.UTF8String, NULL};
        posix_spawnattr_t attributes;
        posix_spawn_file_actions_t actions;
        int error = posix_spawnattr_init(&attributes);
        if (error) { reply(failure(@"spawnattr_init", error)); return; }
        error = posix_spawn_file_actions_init(&actions);
        if (error) { posix_spawnattr_destroy(&attributes); reply(failure(@"actions_init", error)); return; }
        /* Darwin's CLOEXEC_DEFAULT is the SDK-supported closefrom equivalent:
         * descriptors survive only when explicitly named by spawn actions. */
        error = posix_spawnattr_setflags(&attributes, POSIX_SPAWN_SETPGROUP | POSIX_SPAWN_CLOEXEC_DEFAULT);
        if (!error) error = posix_spawnattr_setpgroup(&attributes, 0);
        int descriptor = output.fileDescriptor;
        if (!error) error = posix_spawn_file_actions_adddup2(&actions, descriptor, STDOUT_FILENO);
        if (!error) error = posix_spawn_file_actions_adddup2(&actions, descriptor, STDERR_FILENO);
        if (!error && descriptor > STDERR_FILENO)
            error = posix_spawn_file_actions_addclose(&actions, descriptor);
        if (!error) error = posix_spawn_file_actions_addopen(&actions, STDIN_FILENO, "/dev/null", O_RDONLY, 0);
        pid_t child = 0;
        if (!error) error = posix_spawn(&child, fixture.fileSystemRepresentation, &actions,
                                      &attributes, arguments, environment);
        posix_spawn_file_actions_destroy(&actions);
        posix_spawnattr_destroy(&attributes);
        if (error) { reply(failure(@"posix_spawn", error)); return; }
        self.root = child;
        self.deadline = timeout ? clock_gettime_nsec_np(CLOCK_MONOTONIC) + NSEC_PER_SEC : 0;
        reply(@{ @"version": @1, @"event": @"started", @"ok": @YES,
                 @"service_pid": @(getpid()), @"root_pid": @(child), @"pgid": @(child) });
        self.timer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, self.queue);
        __weak BoundaryService *weakSelf = self;
        dispatch_source_set_timer(self.timer, dispatch_time(DISPATCH_TIME_NOW, 50000000), 50000000, 1000000);
        dispatch_source_set_event_handler(self.timer, ^{
            BoundaryService *service = weakSelf;
            if (!service || service.root <= 0) return;
            if (service.deadline && clock_gettime_nsec_np(CLOCK_MONOTONIC) >= service.deadline) {
                [service notify:[service stop:@"timeout"]]; return;
            }
            int status = 0;
            pid_t result = waitpid(service.root, &status, WNOHANG);
            if (result > 0) [service notify:[service finish:@"exit" status:status error:0 reaped:YES]];
            else if (result < 0 && errno != EINTR)
                [service notify:[service finish:@"waitpid_error" status:0 error:errno reaped:NO]];
        });
        dispatch_resume(self.timer);
    });
}

- (void)cancel:(void (^)(NSDictionary *))reply {
    dispatch_async(self.queue, ^{ reply([self stop:@"cancel"]); });
}

- (void)disconnected {
    dispatch_async(self.queue, ^{
        if (self.root > 0) [self stop:@"client_disconnected"];
        self.connection = nil;
    });
}
@end

@interface BoundaryListener : NSObject <NSXPCListenerDelegate>
@end
@implementation BoundaryListener
- (BOOL)listener:(NSXPCListener *)listener shouldAcceptNewConnection:(NSXPCConnection *)connection {
    (void)listener;
    BoundaryService *service = [BoundaryService new];
    service.connection = connection;
    connection.exportedInterface = [NSXPCInterface interfaceWithProtocol:@protocol(BoundaryV1)];
    connection.exportedObject = service;
    connection.remoteObjectInterface = [NSXPCInterface interfaceWithProtocol:@protocol(BoundaryEvents)];
    __weak BoundaryService *weakService = service;
    connection.invalidationHandler = ^{ [weakService disconnected]; };
    connection.interruptionHandler = ^{ [weakService disconnected]; };
    [connection resume];
    return YES;
}
@end

int main(void) {
    @autoreleasepool {
        signal(SIGPIPE, SIG_IGN);
        BoundaryListener *delegate = [BoundaryListener new];
        NSXPCListener *listener = [NSXPCListener serviceListener];
        listener.delegate = delegate;
        [listener resume];
        dispatch_main();
    }
}

#else

@interface ClientEvents : NSObject <BoundaryEvents>
@end
@implementation ClientEvents
- (void)finished:(NSDictionary *)receipt {
    printJSON(receipt);
    exit([receipt[@"ok"] boolValue] ? 0 : 1);
}
@end

int main(int argc, const char **argv) {
    @autoreleasepool {
        signal(SIGPIPE, SIG_IGN);
        if (argc != 4) {
            printJSON(failure(@"usage: client outputdir mode hold|cancel|timeout", EINVAL)); return 64;
        }
        NSString *directory = [[NSString stringWithUTF8String:argv[1]] stringByStandardizingPath];
        NSString *mode = [NSString stringWithUTF8String:argv[2]];
        NSString *action = [NSString stringWithUTF8String:argv[3]];
        if (!directory.isAbsolutePath || ![@[@"hold", @"cancel", @"timeout"] containsObject:action]) {
            printJSON(failure(@"invalid_client_arguments", EINVAL)); return 64;
        }
        NSError *error = nil;
        if (![[NSFileManager defaultManager] createDirectoryAtPath:directory withIntermediateDirectories:YES
            attributes:@{NSFilePosixPermissions: @0700} error:&error]) {
            printJSON(failure(error.localizedDescription, (int)error.code)); return 1;
        }
        NSXPCConnection *connection = [[NSXPCConnection alloc] initWithServiceName:@BOUNDARY_SERVICE_NAME];
        connection.remoteObjectInterface = [NSXPCInterface interfaceWithProtocol:@protocol(BoundaryV1)];
        connection.exportedInterface = [NSXPCInterface interfaceWithProtocol:@protocol(BoundaryEvents)];
        connection.exportedObject = [ClientEvents new];
        connection.invalidationHandler = ^{ printJSON(failure(@"connection_invalidated", ECONNRESET)); exit(1); };
        connection.interruptionHandler = ^{ printJSON(failure(@"connection_interrupted", ECONNRESET)); exit(1); };
        [connection resume];
        id<BoundaryV1> service = [connection remoteObjectProxyWithErrorHandler:^(NSError *remoteError) {
            printJSON(failure(remoteError.localizedDescription, (int)remoteError.code)); exit(1);
        }];
        [service start:mode output:[NSFileHandle fileHandleWithStandardOutput] directory:directory
            timeout:[action isEqualToString:@"timeout"] reply:^(NSDictionary *reply) {
            printJSON(reply);
            if (![reply[@"ok"] boolValue]) exit(1);
            if ([action isEqualToString:@"cancel"]) {
                dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 300000000), dispatch_get_main_queue(), ^{
                    [service cancel:^(NSDictionary *receipt) {
                        printJSON(receipt); exit([receipt[@"ok"] boolValue] ? 0 : 1);
                    }];
                });
            }
        }];
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 20 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
            printJSON(failure(@"client_watchdog_no_receipt", ETIMEDOUT)); exit(1);
        });
        dispatch_main();
    }
}
#endif
