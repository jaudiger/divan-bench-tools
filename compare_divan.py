#!/usr/bin/env python3
"""Compare benchmark results between base and PR branches.

Generates a markdown report showing performance changes with indicators.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

NS_PER_US = 1_000
NS_PER_MS = 1_000_000
NS_PER_S = 1_000_000_000


class ComparisonStatus(Enum):
    """Status of a benchmark comparison."""

    COMPARED = "compared"
    NEW = "new"
    REMOVED = "removed"


@dataclass
class ComparisonThresholds:
    """Thresholds for benchmark comparison indicators."""

    improvement: float = -1.0
    warn: float = 5.0
    error: float = 10.0


@dataclass
class BenchmarkComparison:
    """Result of comparing a benchmark between base and PR."""

    name: str
    base: int | None
    pr: int | None
    change_pct: float | None
    indicator: str
    status: ComparisonStatus


def format_time(ns: int | None) -> str:
    """Format nanoseconds to human-readable time string.

    Handles edge cases:
    - Zero returns "0 ns"
    - Negative values are formatted with a minus sign
    - None returns "N/A"
    """
    if ns is None:
        return "N/A"

    if ns == 0:
        return "0 ns"

    sign = "-" if ns < 0 else ""
    abs_ns = abs(ns)

    if abs_ns >= NS_PER_S:
        return f"{sign}{abs_ns / NS_PER_S:.3f} s"
    if abs_ns >= NS_PER_MS:
        return f"{sign}{abs_ns / NS_PER_MS:.3f} ms"
    if abs_ns >= NS_PER_US:
        return f"{sign}{abs_ns / NS_PER_US:.3f} µs"
    return f"{sign}{abs_ns} ns"


def calculate_change(base: int, pr: int) -> float:
    """Calculate percentage change from base to PR."""
    if base == 0:
        return 0.0
    return ((pr - base) / base) * 100


def get_change_indicator(
    change_pct: float,
    thresholds: ComparisonThresholds | None = None,
) -> str:
    """Get indicator emoji based on change percentage.

    Args:
        change_pct: The percentage change (positive = slower, negative = faster).
        thresholds: Thresholds for change indicators.

    """
    if thresholds is None:
        thresholds = ComparisonThresholds()

    if change_pct <= thresholds.improvement:
        return "✅"
    if change_pct > thresholds.error:
        return "❌"
    if change_pct > thresholds.warn:
        return "⚠️"

    return ""


def validate_benchmark_entry(entry: dict[str, Any], file_path: Path, index: int, metric: str) -> None:
    """Validate a single benchmark entry has required fields.

    Raises:
        ValueError: If required fields are missing.

    """
    if "name" not in entry:
        raise ValueError(f"Entry {index} in '{file_path}' missing required field 'name'")
    if metric not in entry:
        raise ValueError(
            f"Benchmark '{entry.get('name', f'entry {index}')}' in '{file_path}' missing metric '{metric}'"
        )
    if "value" not in entry.get(metric, {}):
        raise ValueError(f"Benchmark '{entry['name']}' in '{file_path}' has metric '{metric}' but no 'value' field")


def load_benchmarks(file_path: str | Path, metric: str) -> dict[str, dict[str, Any]]:
    """Load benchmarks from JSON file and return as dict keyed by name.

    Args:
        file_path: Path to the JSON benchmark file.
        metric: The metric to validate (e.g., "mean", "median").

    Returns:
        Dictionary mapping benchmark names to their data.

    """
    path = Path(file_path)

    if not path.exists():
        print(f"Error: File '{path}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{path}': {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print(
            f"Error: Expected JSON array in '{path}', got {type(data).__name__}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate each entry
    for index, entry in enumerate(data):
        try:
            validate_benchmark_entry(entry, path, index, metric)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    return {item["name"]: item for item in data}


def get_benchmark_group(name: str) -> str:
    """Extract the main group from a benchmark name."""
    return name.split("/")[0] if "/" in name else name


def format_group_name(group: str) -> str:
    """Format group name for section header."""
    return group.replace("_", " ").title()


def get_short_name(name: str) -> str:
    """Get benchmark name without group prefix."""
    parts = name.split("/", 1)
    return parts[1] if len(parts) > 1 else name


def format_table_row(comparison: BenchmarkComparison, display_name: str | None = None) -> str:
    """Format a single comparison as a markdown table row.

    Args:
        comparison: The benchmark comparison data.
        display_name: Optional name to display instead of comparison.name.

    """
    name = display_name if display_name else comparison.name
    base_str = format_time(comparison.base)
    pr_str = format_time(comparison.pr)

    if comparison.change_pct is not None:
        change_str = f"{comparison.change_pct:+.1f}% {comparison.indicator}".strip()
    else:
        change_str = comparison.indicator

    return f"| `{name}` | {base_str} | {pr_str} | {change_str} |"


def generate_comparison(
    base_benchmarks: dict[str, dict[str, Any]],
    pr_benchmarks: dict[str, dict[str, Any]],
    metric: str = "mean",
    thresholds: ComparisonThresholds | None = None,
) -> list[BenchmarkComparison]:
    """Generate comparison data between base and PR benchmarks.

    Args:
        base_benchmarks: Benchmarks from the base branch.
        pr_benchmarks: Benchmarks from the PR branch.
        metric: The metric to compare.
        thresholds: Thresholds for change indicators.

    Returns:
        List of BenchmarkComparison objects.

    """
    if thresholds is None:
        thresholds = ComparisonThresholds()

    comparisons: list[BenchmarkComparison] = []

    all_names = sorted(set(base_benchmarks.keys()) | set(pr_benchmarks.keys()))

    for name in all_names:
        base_data = base_benchmarks.get(name)
        pr_data = pr_benchmarks.get(name)

        if base_data and pr_data:
            base_value = base_data[metric]["value"]
            pr_value = pr_data[metric]["value"]
            change_pct = calculate_change(base_value, pr_value)

            comparisons.append(
                BenchmarkComparison(
                    name=name,
                    base=base_value,
                    pr=pr_value,
                    change_pct=change_pct,
                    indicator=get_change_indicator(change_pct, thresholds),
                    status=ComparisonStatus.COMPARED,
                )
            )
        elif pr_data and not base_data:
            comparisons.append(
                BenchmarkComparison(
                    name=name,
                    base=None,
                    pr=pr_data[metric]["value"],
                    change_pct=None,
                    indicator="🆕",
                    status=ComparisonStatus.NEW,
                )
            )
        elif base_data and not pr_data:
            comparisons.append(
                BenchmarkComparison(
                    name=name,
                    base=base_data[metric]["value"],
                    pr=None,
                    change_pct=None,
                    indicator="🗑️",
                    status=ComparisonStatus.REMOVED,
                )
            )

    return comparisons


def generate_markdown(
    comparisons: list[BenchmarkComparison],
    title: str,
    subtitle: str | None = None,
    thresholds: ComparisonThresholds | None = None,
) -> str:
    """Generate markdown report from comparison data.

    Args:
        comparisons: List of benchmark comparisons.
        title: Title for the report header.
        subtitle: Optional subtitle displayed below the title.
        thresholds: Thresholds for regression/improvement detection.

    Returns:
        Markdown-formatted report string.

    """
    if thresholds is None:
        thresholds = ComparisonThresholds()

    lines: list[str] = []

    # Count regressions and improvements
    regressions = [c for c in comparisons if (c.change_pct or 0) > thresholds.warn]
    improvements = [c for c in comparisons if (c.change_pct or 0) < thresholds.improvement]

    lines.append(f"## {title}")
    if subtitle:
        lines.append("")
        lines.append(f"<sub>{subtitle}</sub>")
    lines.append("")

    if not comparisons:
        lines.append("No benchmark data available.")
        return "\n".join(lines)

    # Summary
    if regressions:
        lines.append(f"**{len(regressions)} potential regression(s)** detected (>{thresholds.warn}% slower)")
    if improvements:
        lines.append(f"**{len(improvements)} improvement(s)** detected")

    # Group benchmarks by category
    groups: dict[str, list[BenchmarkComparison]] = {}
    for c in comparisons:
        group = get_benchmark_group(c.name)
        if group not in groups:
            groups[group] = []
        groups[group].append(c)

    # Sort groups alphabetically
    sorted_groups = sorted(groups.keys())

    # Generate a section for each group
    for group in sorted_groups:
        group_comparisons = groups[group]
        lines.append("")
        lines.append(f"### {format_group_name(group)}")
        lines.append("")
        lines.append("| Benchmark | Base | PR | Change |")
        lines.append("|-----------|------|-----|--------|")

        for c in group_comparisons:
            short_name = get_short_name(c.name)
            lines.append(format_table_row(c, short_name))

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare benchmark results between base and PR",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("base_file", help="Path to base benchmark JSON file")
    parser.add_argument("pr_file", help="Path to PR benchmark JSON file")
    parser.add_argument(
        "--title",
        default="Benchmarks",
        help="Title for the report header",
    )
    parser.add_argument(
        "--subtitle",
        help="Subtitle displayed below the title",
    )
    parser.add_argument(
        "--metric",
        default="mean",
        choices=["fastest", "slowest", "median", "mean"],
        help="Metric to use for comparison",
    )
    parser.add_argument(
        "--improvement-threshold",
        type=float,
        default=1.0,
        help="Threshold for detecting improvements (in %%)",
    )
    parser.add_argument(
        "--warn-threshold",
        type=float,
        default=5.0,
        help="Threshold for warning indicator (in %%)",
    )
    parser.add_argument(
        "--error-threshold",
        type=float,
        default=10.0,
        help="Threshold for error/regression indicator (in %%)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file",
    )

    args = parser.parse_args()

    # Convert improvement threshold to negative
    thresholds = ComparisonThresholds(
        improvement=-abs(args.improvement_threshold),
        warn=args.warn_threshold,
        error=args.error_threshold,
    )

    base_benchmarks = load_benchmarks(args.base_file, args.metric)
    pr_benchmarks = load_benchmarks(args.pr_file, args.metric)

    comparisons = generate_comparison(
        base_benchmarks,
        pr_benchmarks,
        args.metric,
        thresholds=thresholds,
    )
    markdown = generate_markdown(
        comparisons,
        args.title,
        subtitle=args.subtitle,
        thresholds=thresholds,
    )

    if args.output:
        Path(args.output).write_text(markdown)
    else:
        print(markdown)
