#include <stdio.h>
#include <easyargs.h>
#include <easyevents.h>
#include <easywriter.h>
#include <unistd.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    char *process_name = NULL;
    char *output_file = NULL;
    char *config_file = NULL;
    long int time = 0;
    long int sleep_time = 0;
    uint8_t list = 0;
    pid_t pid;
    sample *samples_start, *samples_end;

    // Initialize to NULL both
    samples_start = samples_end = NULL;
    size_t tot_events = 0;
    

    if (easyargs_parse(argc, argv) != 0) {
        return 1;
    }

    // Check if the user wanted to list the available events
    if (easyargs_getbyname("--list", (void *)&list) == 0) {
        if (list) {
            easyevent_print_all();
            return 0;
        }
    }

    if (easyargs_getbyname("--process", (void *)&process_name) == 0) {
        printf("Process to execute: %s\n", process_name ? process_name : "None");
    }

    if (easyargs_getbyname("--time", (void *)&time) == 0) {
        printf("Time to profile: %li\n", time);
    }

    if (easyargs_getbyname("--sleep", (void *)&sleep_time) == 0) {
        printf("Sleep time: %li\n", sleep_time);
    }

    if (easyargs_getbyname("--output", (void *)&output_file) == 0) {
        printf("Output file to save results to: %s\n", output_file);
    }


    easyargs_getbyname("--config", (void *)&config_file);
    easyevent_enable(config_file);
    printf("Enabled events from config file: %s\n", config_file ? config_file : "None");

    easywriter_init(output_file);
    printf("Initialized writer to output file: %s\n", output_file ? output_file : "None");

    if (process_name != NULL) {
        // Spawn the child
        pid = fork();
        
        if (pid == 0) {
            // I am the child here, run the program
            execlp(process_name, process_name, NULL);
            
            exit(0);
        }
    }

    for (long int t = 0; t < time; t+=sleep_time)
    {
        easyevent_sample(&samples_start, &tot_events);
        
        // Go to sleep
        sleep(sleep_time);

        easyevent_sample(&samples_end, &tot_events);
        
        // Take the diff
        for (size_t i = 0; i < tot_events; i++) {
            samples_end[i].value -= samples_start[i].value;
        }

        easywriter_write(samples_end, tot_events);
    }

    if (process_name != NULL) {
        // Once I am done, kill the process if it is not done yet
        kill(pid, SIGTERM);
        
        int status;
        pid_t r = waitpid(pid, &status, 0);
        if (r == -1) {
            perror("waitpid");
        }
    }

    return 0;
}