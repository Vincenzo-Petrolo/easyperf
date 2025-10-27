#include <easyargs.h>
#include <stdio.h>
#include <unistd.h>
#include <libgen.h>

#define PATH_MAX 300

int is_executable_in_path(const char *cmd) {
    if (!cmd || !*cmd)
        return -1;

    // Get PATH environment variable
    const char *path_env = getenv("PATH");
    if (!path_env || !*path_env)
        path_env = "/bin:/usr/bin"; // reasonable default

    // Duplicate PATH string because strtok_r modifies it
    char *path = strdup(path_env);
    if (!path)
        return -1;

    char *saveptr = NULL;
    for (char *dir = strtok_r(path, ":", &saveptr);
         dir;
         dir = strtok_r(NULL, ":", &saveptr)) {

        char fullpath[PATH_MAX];

        // Construct "<dir>/<cmd>"
        int n = snprintf(fullpath, sizeof(fullpath), "%s/%s", dir, cmd);
        if (n <= 0 || n >= (int)sizeof(fullpath))
            continue; // truncated path, skip

        if (access(fullpath, X_OK) == 0) {
            free(path);
            return 0; // Found and executable
        }
    }

    free(path);
    return -1;
}


static int validate_process(void *arg) {

    const char **proc_name_ptr = (const char **) arg;
    const char *proc_name = *proc_name_ptr;

    // Check if the executable is a path and is accessibe in X mode
    if (access(proc_name, X_OK) == 0) {
        return 0;
    }

    if (is_executable_in_path(proc_name) == 0) {
        return 0;
    }

    return -1;
}

static int validate_time(void *arg) {
    long int *time_ptr = (long int *)arg;
    long int time = *time_ptr;

    if (time <= 0) {
        return -1;
    }

    return 0;
}

static int validate_output(void *arg) {
    int err = 0;
    const char **path_str_ptr = (const char **) arg;
    const char *path_str = *path_str_ptr;

    char *mutable_path_str = (char *) malloc(strlen(path_str));

    // Check if the given path contains a directory with proper write
    // permissions. Else the file creation will fail.
    char *dirpath = dirname(mutable_path_str);

    err = access(dirpath, W_OK);

    free(mutable_path_str);

    return err;
}



static arg_t args[] = {
    {"--process",   "-p",{.svalue = NULL           }, STRING, "The absolute path to an executable that should be executed alongside the profiling. (Default=None)", validate_process},
    {"--time",      "-t",{.ivalue = 10L            }, NUMBER,  "The total time (in seconds) for the processing. (Default=10 seconds)", validate_time },
    {"--output",    "-o",{.svalue="easyperf.csv"   }, STRING,  "The output file for the profiling results. (Default=easyperf.csv)", validate_output },
    {"--sleep",     "-s",{.ivalue=1L               }, NUMBER,  "The sleep interval between samples. (Default=1s)", validate_time }
};



int easyargs_parse(int argc, char *argv[]) {
    // Iterate over the arguments list, arguments are given in this format
    // --process <name>, or -p <name>. 
    // The argument shall be parsed and then validated.

    for (int j = 1; j < argc; j+=2) {
        char *arg = argv[j];
        char *value = argv[j+1];

        for (size_t i = 0; i < sizeof(args)/sizeof(args[0]); i++)
        {
            if (strncmp(args[i].arg, arg, strlen(args[i].arg)) == 0 ||
                strncmp(args[i].shortarg, arg, strlen(args[i].shortarg)) == 0 ) {

                switch (args[i].type)
                {
                case STRING:
                    args[i].svalue = value;
                    break;

                case NUMBER:
                    args[i].ivalue = atol((const char *)value);
                    break;
                
                default:
                    break;
                }
                
                // Validate the argument
                if (args[i].validate) {
                    if (args[i].validate((void *)&(args[i].svalue)) != 0) {
                        fprintf(stderr, "Invalid argument for %s\n", args[i].arg);
                        return -1;
                    }
                }
            }
        }
    }
    

    return 0;
}


int easyargs_getbyname(char *name, void *vvalue) {

    for (size_t i = 0; i < sizeof(args)/sizeof(args[0]); i++) {

        if (strncmp(args[i].arg, name, strlen(args[i].arg)) == 0) {

            switch (args[i].type)
            {
            case STRING:
                *(char **)vvalue = args[i].svalue;
                break;
            
            case NUMBER:
                *(long *)vvalue = args[i].ivalue;
                break;
            
            default:
                break;
            }


            return 0;
        }
    }
    
    return -1;
}
