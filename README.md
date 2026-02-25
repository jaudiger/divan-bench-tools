# Divan Bench Tools

## Getting Started

This repository provides two Python scripts for processing and comparing [Divan](https://github.com/nvzqz/divan) benchmark results. They are designed to detect performance regressions and generate human-readable reports.

### Scripts

#### `parse_divan.py`

Converts Divan's tree-table benchmark output to JSON format for further processing.

```sh
# From a file
./parse_divan.py bench_output.txt -o results.json

# From stdin
cargo bench 2>&1 | ./parse_divan.py - -o results.json
```

The output JSON contains an array of benchmark results, each with `name`, `fastest`, `slowest`, `median`, `mean`, `samples`, and `iters` fields.

#### `compare_divan.py`

Compares two JSON benchmark files (base vs PR) and generates a markdown report with performance change indicators.

```sh
./compare_divan.py base.json pr.json --title "Benchmark Results" -o report.md
```

Options:

- `--metric`: Metric to compare (`fastest`, `slowest`, `median`, `mean`; default: `mean`)
- `--improvement-threshold`: Threshold for improvement detection (default: `1%`)
- `--warn-threshold`: Threshold for warning indicator (default: `5.0%`)
- `--error-threshold`: Threshold for regression indicator (default: `10.0%`)
- `--subtitle`: Optional subtitle displayed below the title
