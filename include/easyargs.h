#pragma once

#include <stdlib.h>
#include <string.h>

// This file is in charge of doing argument parsing.

typedef enum {
    NUMBER = 0,
    STRING = 1
} arg_type_t;

typedef int (*validate_fn)(void *);

typedef struct arg_t {
    char *arg; // Full name of the argument
    char *shortarg; // Short name for the argument
    union {
        long int ivalue; // integer value if the arg is a value
        char    *svalue; // String pointer if the argument is a string
    };
    arg_type_t type; // Type of the argument
    char *description; // String description for this argument
    validate_fn validate; // Fn used to validate the argument, returns 0 on success, else error. (Can be NULL)
} arg_t;

// This function will parse the arguments given in argv according to the args
// defined in easyargs.c. The function returns 0 on successful parsing, else
// returns -1 on invalid parsing printing the error.
int easyargs_parse(int argc, char *argv[]);


// This function is used to retrieve the value for a given argument. The
// returned value is stored in vvalue pointer opportunely casted to the correct
// type of the value. If the argument is not found, then -1 is returned. Else 0.
int easyargs_getbyname(char *name, void *vvalue);