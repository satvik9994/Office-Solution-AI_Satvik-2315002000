"""Tests for evidence-based benchmark metrics."""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("src"))

from evaluation.metrics import MetricsCalculator


class FakeVisual:
    def __init__(self, is_match):
        self.is_match = is_match


class TestMetricsCalculator(unittest.TestCase):
    def make_items(self):
        return [
            {
                "id": "calc_1",
                "ground_truth_dax": "DIVIDE(SUM(Profit), SUM(Sales))",
                "baseline_structural_match": False,
                "engine_structural_match": True,
                "baseline_numerical_status": "MISMATCH",
                "engine_numerical_status": "VERIFIED",
                "baseline_numerical_match": False,
                "engine_numerical_match": True,
                "is_flawed_baseline": True,
                "flaw_detected": True,
                "correction_fully_verified": True,
                "baseline_confidence": 0.30,
                "engine_confidence": 1.00,
            },
            {
                "id": "calc_3",
                "ground_truth_dax": "IF(..., ... , FILTER(ALL(Table), ...))",
                "baseline_structural_match": False,
                "engine_structural_match": False,
                "baseline_numerical_status": "MISMATCH",
                "engine_numerical_status": "UNVERIFIABLE_INCOMPLETE_TEMPLATE",
                "baseline_numerical_match": False,
                "engine_numerical_match": False,
                "is_flawed_baseline": True,
                "flaw_detected": True,
                "correction_fully_verified": False,
                "baseline_confidence": 0.30,
                "engine_confidence": 0.77,
            },
            {
                "id": "calc_4",
                "ground_truth_dax": 'IF(SUM(Sales) > 5000, "High", "Low")',
                "baseline_structural_match": False,
                "engine_structural_match": True,
                "baseline_numerical_status": "MISMATCH",
                "engine_numerical_status": "VERIFIED",
                "baseline_numerical_match": False,
                "engine_numerical_match": True,
                "is_flawed_baseline": True,
                "flaw_detected": True,
                "correction_fully_verified": True,
                "baseline_confidence": 0.30,
                "engine_confidence": 1.00,
            },
        ]

    def test_incomplete_ground_truth_is_excluded(self):
        summary = MetricsCalculator.calculate_summary(
            self.make_items(),
            [FakeVisual(True)],
        )
        self.assertEqual(summary.structural_denominator, 2)
        self.assertEqual(summary.baseline_dax_accuracy, 0.0)
        self.assertEqual(summary.engine_dax_accuracy, 100.0)
        self.assertEqual(summary.incomplete_ground_truth_count, 1)

    def test_numerical_metrics_use_actual_results(self):
        summary = MetricsCalculator.calculate_summary(
            self.make_items(),
            [FakeVisual(True)],
        )
        self.assertEqual(summary.baseline_numerical_agreement_rate, 0.0)
        self.assertEqual(summary.numerical_agreement_rate, 100.0)

    def test_correction_rate_does_not_count_unverifiable_item(self):
        summary = MetricsCalculator.calculate_summary(
            self.make_items(),
            [FakeVisual(True)],
        )
        self.assertEqual(summary.correction_success_rate, 66.7)

    def test_normalization_handles_table_qualifiers(self):
        self.assertTrue(
            MetricsCalculator.structural_match(
                "DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))",
                "DIVIDE(SUM(Profit), SUM(Sales))",
            )
        )


if __name__ == "__main__":
    unittest.main()
