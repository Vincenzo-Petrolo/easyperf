#include <easywriter.h>
#include <stdio.h>
#include <string.h>

static FILE *fp = NULL;
static char *filename = NULL;

static int write_csv(sample *samples, size_t len) {
    static int first_time = 1;

    if (first_time) {
        fp = fopen(filename, "w");
    } else {
        fp = fopen(filename, "a");
    }

    if (fp == NULL) {
        fprintf(stderr, "Error opening output file: %s\n", filename);
        return -1;
    }

    if (first_time) {
        // Add the header for the first time write
        for (size_t i = 0; i < len; i++) {
            fputs(samples[i].name, fp);

        if (i != len-1) {
            fputc(',', fp);
        } 
        }
        fputc('\n', fp);

        first_time = 0;
    }

    // Store all the samples in the file
    for (size_t i = 0; i < len; i++) {
        fprintf(fp, "%lu", samples[i].value);

       if (i != len-1) {
        fputc(',', fp);
       } 
    }

    fputc('\n', fp);

    fclose(fp);

    return 0;
}


// Using CSV as backend for this writer, could choose this from the extension
// of the file and fallback to csv. For now always fallback to csv.
static easywriter writer = {
    .write_fn = write_csv
};



int easywriter_init(char *pathname) {
    filename = strdup(pathname);
    return 0;
}

int easywriter_write(sample *samples, size_t len) {
    return writer.write_fn(samples, len);
}