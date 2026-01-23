# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2024-10-24

### Added
- Initial release of Easyperf.
- RISC-V CVA6 support for hardware performance counters.
- Linux support for system-wide events.
- Process profiling support.
- CSV output format.
- Documentation (README).
- CI workflow with tests.
- `--version` flag.

### Fixed
- Fixed argument parsing bug where flags would consume the subsequent argument.
- Fixed integer formatting in output to use `PRIu64` for better portability.
