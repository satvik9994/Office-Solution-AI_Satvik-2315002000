"""Unit tests for error detection and numerical validation engines."""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath('src'))

import pandas as pd
from validation.error_detector import ErrorDetector
from validation.numerical_engine import NumericalEngine


class TestErrorDetector(unittest.TestCase):

    def setUp(self):
        self.detector = ErrorDetector()

    def test_inverted_division_detected(self):
        result = self.detector.diagnose_and_correct(
            calc_id="calc_1",
            tableau_formula="SUM([Profit]) / SUM([Sales])",
            legacy_dax="SUM(Sales) / SUM(Profit)",
            generated_dax="DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))",
            ground_truth_dax="DIVIDE(SUM(Profit), SUM(Sales))",
        )
        self.assertTrue(result.is_incorrect)
        self.assertEqual(result.error_category, "inverted_aggregation_and_unsafe_division")

    def test_lod_stripped_detected(self):
        result = self.detector.diagnose_and_correct(
            calc_id="calc_2",
            tableau_formula="{FIXED [Region]: SUM([Sales])}",
            legacy_dax="SUM(Sales)",
            generated_dax="CALCULATE(SUM(Table[Sales]), ALLEXCEPT(Table, Table[Region]))",
            ground_truth_dax="CALCULATE(SUM(Sales), ALLEXCEPT(Table, Table[Region]))",
        )
        self.assertTrue(result.is_incorrect)
        self.assertEqual(result.error_category, "incorrect_lod_conversion")

    def test_expression_truncation_detected(self):
        result = self.detector.diagnose_and_correct(
            calc_id="calc_3",
            tableau_formula="IF {FIXED [Region]: SUM([Sales])} > 10000 THEN AVG([Profit]) / SUM([Sales]) ELSE WINDOW_SUM(SUM([Profit])) END",
            legacy_dax="AVG(Profit)",
            generated_dax="IF(CALCULATE(...), DIVIDE(...),...)",
            ground_truth_dax="IF(CALCULATE(...),...)",
        )
        self.assertTrue(result.is_incorrect)
        self.assertEqual(result.error_category, "expression_truncation")

    def test_return_type_mismatch_detected(self):
        result = self.detector.diagnose_and_correct(
            calc_id="calc_4",
            tableau_formula="IF SUM([Sales]) > 5000 THEN 'High' ELSE 'Low' END",
            legacy_dax="IF(SUM(Sales) > 5000, 1, 0)",
            generated_dax='IF(SUM(Table[Sales]) > 5000, "High", "Low")',
            ground_truth_dax='IF(SUM(Sales) > 5000, "High", "Low")',
        )
        self.assertTrue(result.is_incorrect)
        self.assertEqual(result.error_category, "return_type_mismatch")

    def test_correct_dax_not_flagged(self):
        result = self.detector.diagnose_and_correct(
            calc_id="calc_1",
            tableau_formula="SUM([Profit]) / SUM([Sales])",
            legacy_dax="DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))",
            generated_dax="DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))",
        )
        self.assertFalse(result.is_incorrect)
        self.assertEqual(result.error_category, "none")


class TestNumericalEngine(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame({
            "Region": ["West", "East", "South", "West", "East"],
            "Sales": [12000, 8000, 4000, 15000, 7000],
            "Profit": [3000, 2000, 500, 4000, 1500],
            "Cost": [9000, 6000, 3500, 11000, 5500],
            "Date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"],
        })
        self.engine = NumericalEngine(self.df)

    def test_calc1_correct_verified(self):
        result = self.engine.validate_calc("calc_1", "SUM([Profit]) / SUM([Sales])",
                                           "DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))", is_legacy=False)
        self.assertTrue(result.is_match)
        self.assertEqual(result.status, "VERIFIED")

    def test_calc1_legacy_mismatch(self):
        result = self.engine.validate_calc("calc_1", "SUM([Profit]) / SUM([Sales])",
                                           "SUM(Sales) / SUM(Profit)", is_legacy=True)
        self.assertFalse(result.is_match)
        self.assertEqual(result.status, "MISMATCH")

    def test_calc2_legacy_drops_lod(self):
        result = self.engine.validate_calc("calc_2", "{FIXED [Region]: SUM([Sales])}",
                                           "SUM(Sales)", is_legacy=True)
        self.assertFalse(result.is_match)

    def test_calc2_correct_verified(self):
        result = self.engine.validate_calc("calc_2", "{FIXED [Region]: SUM([Sales])}",
                                           "CALCULATE(SUM(Table[Sales]), ALLEXCEPT(Table, Table[Region]))", is_legacy=False)
        self.assertTrue(result.is_match)

    def test_calc4_type_mismatch(self):
        result = self.engine.validate_calc("calc_4", "IF SUM([Sales]) > 5000 THEN 'High' ELSE 'Low' END",
                                           "IF(SUM(Sales) > 5000, 1, 0)", is_legacy=True)
        self.assertFalse(result.is_match)

    def test_calc4_correct_verified(self):
        result = self.engine.validate_calc("calc_4", "IF SUM([Sales]) > 5000 THEN 'High' ELSE 'Low' END",
                                           'IF(SUM(Table[Sales]) > 5000, "High", "Low")', is_legacy=False)
        self.assertTrue(result.is_match)

    def test_validation_does_not_depend_on_calculation_id(self):
        result = self.engine.validate_calc(
            "new_calculation_99",
            "SUM([Profit]) / SUM([Sales])",
            "DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))",
        )
        self.assertTrue(result.is_match)
        self.assertEqual(result.status, "VERIFIED")

    def test_unknown_calculation_is_not_falsely_verified(self):
        result = self.engine.validate_calc(
            "new_calculation_100",
            "WINDOW_SUM(SUM([Sales]))",
            "CALCULATE(SUM(Table[Sales]), FILTER(ALLSELECTED(Table), Table[Date] <= MAX(Table[Date])))",
        )
        self.assertFalse(result.is_match)
        self.assertEqual(result.status, "UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
