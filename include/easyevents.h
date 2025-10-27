#pragma once

#include <stdlib.h>
#include <stdint.h>

// This file is in charge of modeling the events of CSRs, and system wide
// events. The intended use of this is to call a sample() followed by the
// gathering of new results. To minimize probe effects I avoid overbloating the
// program with buffer of events in case I have multiple sample() calls before
// gathering the events for writes. Therefore it must be assumed that a sample
// must always be followed by a gather, else results will be overwritten by new
// ones. This is not thread-safe and it is thought to be implemented in a simple
// for-loop. So to ensure that the sampling has finished before gathering.

typedef enum event_type_t {
    CSR, // Access CSRs for reading
    SYSTEM // Uses system wide info accessable from /proc/*
} event_type;

typedef uint64_t (*sample_fn)(void);

typedef struct event {
    char *evt_name; // Null terminated string for name of the event
    event_type type; // Type for the event
    sample_fn sample_fn; // Function used to access a given event and store its value
    int enabled; // This is 1 if the event must be traced. (Default: 0)
} event_t;

typedef struct {
    const char *name;
    uint64_t value;
} sample;

// This function enables the event from a standard list. Pass the event by name.
// If the event exists then it returns 0, else -1.
int easyevent_enable(char *name);

// This function returns an array of all enabled events. The sample array is
// allocated by us and freed by the user. The passed array is NULL in the
// beginning.
void easyevent_sample(sample **, size_t *size);
