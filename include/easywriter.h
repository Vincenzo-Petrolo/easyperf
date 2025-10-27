#pragma once

#include <easyevents.h>


typedef int (*write_fn)(sample *samples, size_t len);


// Abstracts the backend for writing the results
typedef struct writer {
    write_fn write_fn; // Function that writes the samples in the file.
} easywriter;


int easywriter_init(char *pathname);
int easywriter_write(sample *samples, size_t len);

