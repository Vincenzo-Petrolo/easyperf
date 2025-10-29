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

#ifdef __linux

static uint64_t parse_kernel_stat(const char *stat) {
    const char *filename = "/proc/stat";
    FILE *stat_fp = fopen(filename, "r");
    if (!stat_fp) {
        return 0; // or handle error
    }

    char *line = NULL;
    size_t len = 0;
    uint64_t value = 0;

    while (getline(&line, &len, stat_fp) != -1) {
        if (strncmp(line, stat, strlen(stat)) == 0) {
            // skip label and whitespace
            const char *p = line + strlen(stat);
            while (*p == ' ' || *p == '\t') p++;
            sscanf(p, "%"PRIu64"", &value);
            break;
        }
    }

    free(line);
    fclose(stat_fp);
    return value;
}

static uint64_t parse_kernel_vmstat(const char *stat) {
    const char *filename = "/proc/vmstat";
    FILE *stat_fp = fopen(filename, "r");
    if (!stat_fp) {
        return 0; // or handle error
    }

    char *line = NULL;
    size_t len = 0;
    uint64_t value = 0;

    while (getline(&line, &len, stat_fp) != -1) {
        if (strncmp(line, stat, strlen(stat)) == 0) {
            // skip label and whitespace
            const char *p = line + strlen(stat);
            while (*p == ' ' || *p == '\t') p++;
            sscanf(p, "%"PRIu64"", &value);
            break;
        }
    }

    free(line);
    fclose(stat_fp);
    return value;
}

static uint64_t read_ctx_switches(void) {
    return parse_kernel_stat("ctxt");
}

static uint64_t read_interrupts(void) {
    return parse_kernel_stat("intr");
}

static uint64_t read_softirq(void) {
    return parse_kernel_stat("softirq");
}

static uint64_t read_minor_page_fault(void) {
    return parse_kernel_stat("pgfault");
}
static uint64_t read_major_page_fault(void) {
    return parse_kernel_vmstat("pgmajfault");
}


#endif

// All of the events to sample
event_t events[] = {
    /* Micro-architectural CSR Events */
#ifdef __riscv
    {"mcycle",                CSR,  read_cycles,           0},
    {"minstret",              CSR,  read_instret,          0},
    {"l1 dcache_misses",      CSR,  read_hpmcounter3,      0},
    {"l1 icache_misses",      CSR,  read_hpmcounter4,      0},
    {"load_accesses",         CSR,  read_hpmcounter5,      0},
    {"store_accesses",        CSR,  read_hpmcounter6,      0},
    /* Platform events              */
    {"LLC Misses",            CSR,  read_hpmcounter7,      0},
    {"LLC evictions",         CSR,  read_hpmcounter8,      0},
#endif 
    /* System-wide events             */
#ifdef __linux
    {"Context Switches",       SYSTEM,  read_ctx_switches, 0},
    {"Interrupts",             SYSTEM,  read_interrupts,   0},
    {"Software Interrupts",    SYSTEM,  read_softirq,      0},
    {"Minor Page Fault",       SYSTEM,  read_minor_page_fault,0},
    {"Major Page Fault",       SYSTEM,  read_major_page_fault,0},
#endif
};

static int enabled_events = 0;


static int enable_by_name(char *name) {
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

int easyevent_enable(char *filename) {

    // If filename is NULL, enable all events
    if (filename == NULL) {
        for (size_t i = 0; i < sizeof(events)/sizeof(events[0]); i++) {
            events[i].enabled = 1;
        }
        enabled_events = sizeof(events)/sizeof(events[0]);
        return 0;
    }

    FILE *file = fopen(filename, "r");
    if (file == NULL) {
        fprintf(stderr, "Error opening event config file: %s\n", filename);
        return -1;
    }

    char line[256];
    while (fgets(line, sizeof(line), file)) {
        // Remove newline character
        line[strcspn(line, "\n")] = 0;

        if (enable_by_name(line) != 0) {
            fprintf(stderr, "Warning: Event '%s' not found.\n", line);
        }
    }

    fclose(file);
    return 0;
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

void easyevent_print_all(void) {
    printf("Available Events:\n");
    for (size_t i = 0; i < sizeof(events)/sizeof(events[0]); i++) {
        printf(" - %s\n", events[i].evt_name);
    }
}