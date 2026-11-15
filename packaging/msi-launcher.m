#import <Foundation/Foundation.h>
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>

static void fatal(NSString *text) {
    fprintf(stderr, "%s\n", text.UTF8String);
    exit(1);
}

int main(int argc, char **argv) {
    @autoreleasepool {
        NSBundle *bundle = NSBundle.mainBundle;
        NSDictionary *info = bundle.infoDictionary;
        NSString *contents = [bundle.bundlePath stringByAppendingPathComponent:@"Contents"];
        NSString *resources = [contents stringByAppendingPathComponent:@"Resources"];
        NSString *name = info[@"MSIVariant"];
        NSString *original = [contents stringByAppendingPathComponent:
            [@"MacOS" stringByAppendingPathComponent:info[@"MSIOriginalExecutable"]]];
        NSString *runtime = [resources stringByAppendingPathComponent:@"msi-runtime"];
        NSString *abi = info[@"MSISoapyABI"];
        NSString *modules = [runtime stringByAppendingPathComponent:
            [@"lib/SoapySDR/modules" stringByAppendingString:abi]];
        NSFileManager *fm = NSFileManager.defaultManager;
        if (![fm isExecutableFileAtPath:original] || ![fm fileExistsAtPath:modules])
            fatal(@"Faltan componentes de la integración MSI. Vuelve a copiar la aplicación completa.");

        NSString *base = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/MSI-SDR"];
        NSString *profile = [base stringByAppendingPathComponent:name];
        NSError *error = nil;
        if (![fm createDirectoryAtPath:profile withIntermediateDirectories:YES attributes:nil error:&error])
            fatal(error.localizedDescription);
        // Keep a profile from being written by both copies of the same application.
        int lockFD = open([[profile stringByAppendingPathComponent:@"instance.lock"] fileSystemRepresentation], O_CREAT|O_RDWR, 0600);
        if (lockFD < 0 || flock(lockFD, LOCK_EX|LOCK_NB)) {
            fprintf(stderr, "Esta versión de %s ya está abierta.\n", name.UTF8String);
            return 0;
        }

        NSString *logs = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Logs/MSI-SDR"];
        [fm createDirectoryAtPath:logs withIntermediateDirectories:YES attributes:nil error:nil];
        NSString *logFile = [logs stringByAppendingPathComponent:[name stringByAppendingString:@".log"]];
        int logFD = open(logFile.fileSystemRepresentation, O_CREAT|O_WRONLY|O_APPEND, 0600);
        if (logFD >= 0) { dup2(logFD, STDOUT_FILENO); dup2(logFD, STDERR_FILENO); close(logFD); }
        fprintf(stderr, "\nMSI integration start: %s / %s\n", NSDate.date.description.UTF8String, bundle.bundlePath.UTF8String);
        setenv("SOAPY_SDR_ROOT", runtime.fileSystemRepresentation, 1);
        setenv("SOAPY_SDR_PLUGIN_PATH", modules.fileSystemRepresentation, 1);

        NSMutableArray<NSString *> *arguments = [NSMutableArray arrayWithObject:original];
        if ([info[@"MSIApplicationKind"] isEqualToString:@"sdrpp"]) {
            NSString *configPath = [profile stringByAppendingPathComponent:@"config.json"];
            NSData *data = [NSData dataWithContentsOfFile:configPath];
            BOOL firstLaunch = data == nil;
            if (!data) data = [NSData dataWithContentsOfFile:[resources stringByAppendingPathComponent:@"msi-defaults/config.json"]];
            NSMutableDictionary *config = data ? [NSJSONSerialization JSONObjectWithData:data options:NSJSONReadingMutableContainers error:&error] : nil;
            if (!config) fatal(error.localizedDescription ?: @"No se pudo leer la configuración de SDR++.");
            config[@"modulesDirectory"] = [contents stringByAppendingPathComponent:@"Plugins"];
            config[@"resourcesDirectory"] = resources;
            if (firstLaunch) config[@"source"] = @"SoapySDR";
            NSData *updated = [NSJSONSerialization dataWithJSONObject:config options:NSJSONWritingPrettyPrinted error:&error];
            if (![updated writeToFile:configPath options:NSDataWritingAtomic error:&error]) fatal(error.localizedDescription);
            NSString *soapyPath = [profile stringByAppendingPathComponent:@"soapy_source_config.json"];
            if (![fm fileExistsAtPath:soapyPath]) {
                NSString *seed = [resources stringByAppendingPathComponent:@"msi-defaults/soapy_source_config.json"];
                if (![fm copyItemAtPath:seed toPath:soapyPath error:&error]) fatal(error.localizedDescription);
            }
            [arguments addObjectsFromArray:@[@"--root", profile]];
        } else {
            [arguments addObject:@"--soapy"];
        }
        for (int i = 1; i < argc; ++i) [arguments addObject:[NSString stringWithUTF8String:argv[i]]];
        char **childArgs = calloc(arguments.count + 1, sizeof(char *));
        for (NSUInteger i = 0; i < arguments.count; ++i) childArgs[i] = strdup(arguments[i].UTF8String);
        // Framework resources and executable-relative loads remain inside this bundle.
        chdir([[contents stringByAppendingPathComponent:@"MacOS"] fileSystemRepresentation]);
        execv(original.fileSystemRepresentation, childArgs);
        perror("No se pudo abrir la aplicación");
        return 1;
    }
}
