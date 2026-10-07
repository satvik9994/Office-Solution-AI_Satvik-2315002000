"""Unit tests for DAX emitter code generation."""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath('src'))

from parser.parser import Parser
from translator.dax_emitter import DAXEmitter


class TestDAXEmitter(unittest.TestCase):

    def setUp(self):
        self.physical = {"Sales", "Profit", "Cost", "Region", "Date"}
        self.emitter = DAXEmitter(table_name="Table", physical_columns=self.physical)

    def test_simple_sum(self):
        ir = Parser.parse_formula("SUM([Sales])")
        dax = self.emitter.emit(ir)
        self.assertEqual(dax, "SUM(Table[Sales])")

    def test_division_uses_divide(self):
        ir = Parser.parse_formula("SUM([Profit]) / SUM([Sales])")
        dax = self.emitter.emit(ir)
        self.assertEqual(dax, "DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))")

    def test_subtraction(self):
        ir = Parser.parse_formula("SUM([Sales]) - SUM([Cost])")
        dax = self.emitter.emit(ir)
        self.assertEqual(dax, "SUM(Table[Sales]) - SUM(Table[Cost])")

    def test_if_with_string_returns(self):
        ir = Parser.parse_formula("IF SUM([Sales]) > 5000 THEN 'High' ELSE 'Low' END")
        dax = self.emitter.emit(ir)
        self.assertIn("IF(", dax)
        self.assertIn('"High"', dax)
        self.assertIn('"Low"', dax)

    def test_fixed_lod_emits_calculate_allexcept(self):
        ir = Parser.parse_formula("{FIXED [Region]: SUM([Sales])}")
        dax = self.emitter.emit(ir)
        self.assertIn("CALCULATE(", dax)
        self.assertIn("ALLEXCEPT(Table, Table[Region])", dax)
        self.assertEqual(dax, "CALCULATE(SUM(Table[Sales]), ALLEXCEPT(Table, Table[Region]))")

    def test_window_sum_emits_allselected(self):
        ir = Parser.parse_formula("WINDOW_SUM(SUM([Profit]))")
        dax = self.emitter.emit(ir)
        self.assertIn("CALCULATE(", dax)
        self.assertIn("ALLSELECTED(Table)", dax)

    def test_running_sum_emits_filter(self):
        ir = Parser.parse_formula("RUNNING_SUM(SUM([Sales]))")
        dax = self.emitter.emit(ir)
        self.assertIn("CALCULATE(", dax)
        self.assertIn("FILTER(", dax)
        self.assertIn("ALLSELECTED(", dax)

    def test_rank_emits_rankx(self):
        ir = Parser.parse_formula("RANK(SUM([Sales]))")
        dax = self.emitter.emit(ir)
        self.assertIn("RANKX(", dax)
        self.assertIn("ALLSELECTED(", dax)

    def test_complex_nested_kpi(self):
        formula = "IF {FIXED [Region]: SUM([Sales])} > 10000 THEN AVG([Profit]) / SUM([Sales]) ELSE WINDOW_SUM(SUM([Profit])) END"
        ir = Parser.parse_formula(formula)
        dax = self.emitter.emit(ir)
        self.assertIn("IF(", dax)
        self.assertIn("CALCULATE(SUM(Table[Sales]), ALLEXCEPT(Table, Table[Region]))", dax)
        self.assertIn("DIVIDE(AVG(Table[Profit]), SUM(Table[Sales]))", dax)
        self.assertIn("ALLSELECTED(Table)", dax)

    def test_field_reference_non_physical_uses_measure_syntax(self):
        ir = Parser.parse_formula("[Step1] / SUM([Sales])")
        dax = self.emitter.emit(ir)
        self.assertIn("[Step1]", dax)
        self.assertIn("Table[Sales]", dax)

    def test_avg_aggregation(self):
        ir = Parser.parse_formula("AVG([Profit])")
        dax = self.emitter.emit(ir)
        self.assertEqual(dax, "AVG(Table[Profit])")


if __name__ == "__main__":
    unittest.main()
