"""End-to-end tests for compare_divan module."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from compare_divan import (
    BenchmarkComparison,
    ComparisonStatus,
    ComparisonThresholds,
    generate_comparison,
    generate_markdown,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_as_dict(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text())
    return {item["name"]: item for item in data}


class TestGenerateComparison(unittest.TestCase):
    def test_full_comparison(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)

        names = {c.name for c in comparisons}
        self.assertIn("parse/parse_small", names)
        self.assertIn("parse/parse_large", names)
        self.assertIn("transform/transform_small", names)
        self.assertIn("transform/transform_large", names)
        self.assertIn("transform/transform_new", names)

    def test_matching_benchmarks(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        compared = [c for c in comparisons if c.status == ComparisonStatus.COMPARED]

        self.assertEqual(len(compared), 3)
        for c in compared:
            self.assertIsNotNone(c.base)
            self.assertIsNotNone(c.pr)
            self.assertIsNotNone(c.change_pct)

    def test_new_benchmark(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        new = [c for c in comparisons if c.status == ComparisonStatus.NEW]

        self.assertEqual(len(new), 1)
        self.assertEqual(new[0].name, "transform/transform_new")
        self.assertIsNone(new[0].base)
        self.assertEqual(new[0].pr, 500000)
        self.assertEqual(new[0].indicator, "🆕")

    def test_removed_benchmark(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        removed = [c for c in comparisons if c.status == ComparisonStatus.REMOVED]

        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0].name, "transform/transform_large")
        self.assertEqual(removed[0].base, 318000)
        self.assertIsNone(removed[0].pr)
        self.assertEqual(removed[0].indicator, "🗑️")

    def test_regression_indicator(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        by_name = {c.name: c for c in comparisons}

        # parse_large went from 321800 to 360000 = +11.9% -> ❌
        self.assertEqual(by_name["parse/parse_large"].indicator, "❌")

    def test_improvement_indicator(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        by_name = {c.name: c for c in comparisons}

        # parse_small went from 1599000 to 1550000 = -3.1% -> ✅
        self.assertEqual(by_name["parse/parse_small"].indicator, "✅")

    def test_no_change_indicator(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        by_name = {c.name: c for c in comparisons}

        # transform_small is unchanged -> no indicator
        self.assertEqual(by_name["transform/transform_small"].indicator, "")

    def test_custom_thresholds(self) -> None:
        base = {"a": {"mean": {"value": 100}}}
        pr = {"a": {"mean": {"value": 106}}}

        # Default threshold: warn=5 -> 6% is a warning
        comparisons = generate_comparison(base, pr)
        self.assertEqual(comparisons[0].indicator, "⚠️")

        # Custom threshold: warn=10 -> 6% is not a warning
        thresholds = ComparisonThresholds(improvement=-1.0, warn=10.0, error=20.0)
        comparisons = generate_comparison(base, pr, thresholds=thresholds)
        self.assertEqual(comparisons[0].indicator, "")

    def test_empty_benchmarks(self) -> None:
        comparisons = generate_comparison({}, {})
        self.assertEqual(comparisons, [])

    def test_all_new_benchmarks(self) -> None:
        pr = {"a": {"mean": {"value": 100}}, "b": {"mean": {"value": 200}}}
        comparisons = generate_comparison({}, pr)

        self.assertEqual(len(comparisons), 2)
        for c in comparisons:
            self.assertEqual(c.status, ComparisonStatus.NEW)

    def test_all_removed_benchmarks(self) -> None:
        base = {"a": {"mean": {"value": 100}}, "b": {"mean": {"value": 200}}}
        comparisons = generate_comparison(base, {})

        self.assertEqual(len(comparisons), 2)
        for c in comparisons:
            self.assertEqual(c.status, ComparisonStatus.REMOVED)


class TestGenerateMarkdown(unittest.TestCase):
    def test_full_report(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        markdown = generate_markdown(comparisons, "Benchmarks")

        expected = (FIXTURES / "comparison_report.md").read_text()
        self.assertEqual(markdown, expected)

    def test_empty_comparisons(self) -> None:
        markdown = generate_markdown([], "Empty Report")
        self.assertIn("## Empty Report", markdown)
        self.assertIn("No benchmark data available.", markdown)

    def test_title_and_subtitle(self) -> None:
        comparisons = [
            BenchmarkComparison(
                name="group/bench",
                base=100,
                pr=105,
                change_pct=5.0,
                indicator="",
                status=ComparisonStatus.COMPARED,
            ),
        ]
        markdown = generate_markdown(comparisons, "My Title", subtitle="run #42")
        self.assertIn("## My Title", markdown)
        self.assertIn("<sub>run #42</sub>", markdown)

    def test_regression_summary(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        markdown = generate_markdown(comparisons, "Benchmarks")

        self.assertIn("1 potential regression(s)", markdown)
        self.assertIn("1 improvement(s)", markdown)

    def test_grouped_sections(self) -> None:
        base = _load_as_dict(FIXTURES / "base_benchmarks.json")
        pr = _load_as_dict(FIXTURES / "pr_benchmarks.json")

        comparisons = generate_comparison(base, pr)
        markdown = generate_markdown(comparisons, "Benchmarks")

        self.assertIn("### Parse", markdown)
        self.assertIn("### Transform", markdown)


if __name__ == "__main__":
    unittest.main()
