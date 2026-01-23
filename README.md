# Easyperf

Easyperf is a lightweight imitation of the `perf` tool, designed for performance monitoring on RISC-V CVA6 systems and standard Linux environments. It allows direct access to supervisor performance counters on RISC-V systems, bypassing the Linux kernel `perf` framework when it is not supported or overhead is a concern.

## Features

- **RISC-V CVA6 Support**: Direct access to HPM counters (hpmcounter3-8) via CSRs.
- **Linux Support**: Reads system-wide events from `/proc/stat` and `/proc/vmstat`.
- **Customizable**: Enable specific events via configuration file.
- **Simple Output**: CSV output for easy analysis.
- **Process Profiling**: Can spawn and profile a specific process.

## Building

Easyperf is written in C and can be built using `make`.

```bash
make
```

This will generate the `easyperf` executable.

## Usage

```bash
./easyperf [options]
```

### Options

- `-p, --process <path>`: The absolute path to an executable that should be executed alongside the profiling. (Default: None)
- `-t, --time <seconds>`: The total time (in seconds) for the profiling. (Default: 10 seconds)
- `-o, --output <file>`: The output file for the profiling results. (Default: easyperf.csv)
- `-s, --sleep <seconds>`: The sleep interval between samples. (Default: 1s)
- `-c, --config <file>`: The configuration file (a .txt) for the profiling with the enabled events. If none, all available events will be enabled. (Default: None)
- `-h, --help`: Prints the help message.
- `-l, --list`: Lists all the possible events and exits.

### Examples

**Profile a specific command for its duration (or up to 10s):**
```bash
./easyperf --process /bin/ls
```
*Note: If the process finishes before the time limit, easyperf will stop monitoring.*

**Profile system for 20 seconds with 2 second sampling interval:**
```bash
./easyperf --time 20 --sleep 2 --output system_stats.csv
```

**List available events:**
```bash
./easyperf --list
```

**Use a configuration file to select events:**
Create a file `events.txt`:
```
mcycle
minstret
Context Switches
```
Run:
```bash
./easyperf --config events.txt
```

## Output Format

The output is a CSV file where the first row is the header (event names) and subsequent rows are samples. Each sample represents the count of events occurring during the sleep interval.

Example `easyperf.csv`:
```csv
Context Switches,Interrupts,Software Interrupts,Minor Page Fault,Major Page Fault
120,45,2,0,0
110,40,1,0,0
...
```

## Supported Events

### RISC-V (if compiled on RISC-V)
- `mcycle`
- `minstret`
- `l1 dcache_misses`
- `l1 icache_misses`
- `load_accesses`
- `store_accesses`
- `LLC Misses`
- `LLC evictions`

### Linux (System-wide)
- `Context Switches`
- `Interrupts`
- `Software Interrupts`
- `Minor Page Fault`
- `Major Page Fault`
