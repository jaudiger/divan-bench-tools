"""End-to-end tests for parse_divan module."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from parse_divan import parse_divan_output

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseDivanOutput(unittest.TestCase):
    def test_full_output(self) -> None:
        content = (FIXTURES / "divan_output.txt").read_text()
        expected = json.loads((FIXTURES / "parsed_results.json").read_text())

        results = parse_divan_output(content)
        actual = [r.to_dict() for r in results]

        self.assertEqual(actual, expected)

    def test_empty_input(self) -> None:
        results = parse_divan_output("")
        self.assertEqual(results, [])

    def test_whitespace_only_input(self) -> None:
        results = parse_divan_output("   \n\n   \n")
        self.assertEqual(results, [])

    def test_single_group(self) -> None:
        header = "parse        fastest  │ slowest  │ median   │ mean     │ samples │ iters\n"
        data = "╰─ parse_small  1.551 ms │ 1.738 ms │ 1.590 ms │ 1.599 ms │ 100     │ 100\n"
        content = "Timer precision: 41 ns\n" + header + data
        results = parse_divan_output(content)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "parse/parse_small")
        self.assertEqual(results[0].mean.value, 1599000)
        self.assertEqual(results[0].fastest.value, 1551000)
        self.assertEqual(results[0].slowest.value, 1738000)
        self.assertEqual(results[0].median.value, 1590000)
        self.assertEqual(results[0].samples, 100)
        self.assertEqual(results[0].iters, 100)

    def test_result_count(self) -> None:
        content = (FIXTURES / "divan_output.txt").read_text()
        results = parse_divan_output(content)
        self.assertEqual(len(results), 6)

    def test_benchmark_names(self) -> None:
        content = (FIXTURES / "divan_output.txt").read_text()
        results = parse_divan_output(content)
        names = [r.name for r in results]

        self.assertIn("parse/parse_small", names)
        self.assertIn("parse/parse_medium", names)
        self.assertIn("parse/parse_large", names)
        self.assertIn("transform/transform_small", names)
        self.assertIn("transform/transform_medium", names)
        self.assertIn("transform/transform_large", names)

    def test_nanosecond_values(self) -> None:
        header = "fast        fastest │ slowest │ median  │ mean    │ samples │ iters\n"
        data = "╰─ tiny_op  8 ns    │ 30 ns   │ 8 ns    │ 9 ns    │ 100     │ 51200\n"
        content = "Timer precision: 41 ns\n" + header + data
        results = parse_divan_output(content)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].fastest.value, 8)
        self.assertEqual(results[0].slowest.value, 30)
        self.assertEqual(results[0].median.value, 8)
        self.assertEqual(results[0].mean.value, 9)

    def test_second_values(self) -> None:
        header = "slow            fastest  │ slowest  │ median   │ mean     │ samples │ iters\n"
        data = "╰─ heavy_op     1.5 s    │ 2.3 s    │ 1.8 s    │ 1.9 s    │ 10      │ 10\n"
        content = "Timer precision: 41 ns\n" + header + data
        results = parse_divan_output(content)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].fastest.value, 1_500_000_000)
        self.assertEqual(results[0].slowest.value, 2_300_000_000)
        self.assertEqual(results[0].mean.value, 1_900_000_000)
        self.assertEqual(results[0].samples, 10)
        self.assertEqual(results[0].iters, 10)

    def test_no_benchmark_lines(self) -> None:
        content = "Timer precision: 41 ns\nSome random text\n"
        results = parse_divan_output(content)
        self.assertEqual(results, [])

    def test_validation_consistent_result(self) -> None:
        content = (FIXTURES / "divan_output.txt").read_text()
        results = parse_divan_output(content)

        for result in results:
            warnings = result.validate()
            self.assertEqual(warnings, [], f"Unexpected warnings for {result.name}: {warnings}")


if __name__ == "__main__":
    unittest.main()
