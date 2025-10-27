#include <easyevents.h>
#include <stdio.h>
#include <string.h>
#include <inttypes.h>

#ifdef __riscv
#define CSR_read(reg) \
({ \
	uint64_t __tmp; \
	asm volatile("csrr %0, " #reg : "=r"(__tmp)); \
	__tmp; \
})

static
inline
uint64_t
read_cycles()
{
	uint64_t tmp;

	__asm__ __volatile__("rdcycle %0" : "=r"(tmp));

	return tmp;
}

static 
inline 
uint64_t
read_instret()
{
	uint64_t tmp;

	__asm__ __volatile__("rdinstret %0" : "=r"(tmp));

	return tmp;
}

#define read_hpmcounter(n) \
static uint64_t read_hpmcounter##n(void) { \
	return CSR_read(hpmcounter##n); \
}

read_hpmcounter(3);
read_hpmcounter(4);
read_hpmcounter(5);
read_hpmcounter(6);
read_hpmcounter(7);
read_hpmcounter(8);
#endif

static uint64_t read_ctx_switches(void) {
    const char *filename = "/proc/stat";
    FILE *stat = fopen(filename, "r");
    if (!stat) {
        return 0; // or handle error
    }

    char *line = NULL;
    size_t len = 0;
    uint64_t value = 0;

    while (getline(&line, &len, stat) != -1) {
        if (strncmp(line, "ctxt", 4) == 0) {
            // skip label and whitespace
            const char *p = line + 4;
            while (*p == ' ' || *p == '\t') p++;
            sscanf(p, "%"PRIu64"", &value);
            break;
        }
    }

    free(line);
    fclose(stat);
    return value;
}


// All of the events to sample
event_t events[] = {
    /* Micro-architectural CSR Events */
#ifdef __riscv
    {"mcycle",                CSR,  read_cycles,           0},
    {"minstret",              CSR,  read_instret,         0},
    {"l1 dcache_misses",      CSR,  read_hpmcounter3,      0},
    {"l1 icache_misses",      CSR,  read_hpmcounter4,      0},
    {"l1 dcache_evictions",   CSR,  read_hpmcounter5,      0},
    {"DTLB misses",           CSR,  read_hpmcounter6,      0},
    /* Platform events              */
    {"LLC Misses",            CSR,  read_hpmcounter7,      0},
    {"LLC evictions",         CSR,  read_hpmcounter8,      0},
#endif 
    /* System-wide events             */
#ifdef __linux
    {"Context Switches",       SYSTEM,  read_ctx_switches, 0},
#endif
};

static int enabled_events = 0;


int easyevent_enable(char *name) {
    for (size_t i = 0; i < sizeof(events)/sizeof(events[0]); i++) {
        if (strncmp(events[i].evt_name, name, strlen(events[i].evt_name)) == 0) {
            if (!events[i].enabled) {
                events[i].enabled = 1;
                enabled_events++;
            }
            return 0;
        }
    }

    return -1;
}

void easyevent_sample(sample **array, size_t *size) {

    if (*array == NULL) {
        *array = (sample *) calloc(enabled_events, sizeof(sample));

        if (*array == NULL) {
            fprintf(stderr, "Allocation error in %s!", __func__);
            exit(1);
        }

        *size = enabled_events;
    }

    sample *sampled_events = *array;

    // Iterate over all enabled events
    size_t j = 0;
    for (size_t i = 0; i < sizeof(events)/sizeof(events[0]); i++) {
        uint64_t value = 0;

        // skip non enabled events
        if (!events[i].enabled) {
            continue;
        }

        // Call the sampling function
        value = events[i].sample_fn();

        sampled_events[j].name = events[i].evt_name;
        sampled_events[j].value = value;

        j++;
    }
}