"""Unit tests for dependency resolution and topological sorting."""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath('src'))

from resolver.dependency_graph import (
    DependencyResolver,
    CircularDependencyError,
    MissingDependencyError,
)
from ingestion.models import CalculationItem


class TestDependencyResolver(unittest.TestCase):

    def setUp(self):
        self.physical_columns = {"Sales", "Profit", "Cost", "Region", "Date"}
        self.resolver = DependencyResolver(self.physical_columns)

    def test_extract_identifiers(self):
        formula = "[Step1] / SUM([Sales])"
        ids = self.resolver.extract_identifiers(formula)
        self.assertEqual(ids, {"Step1", "Sales"})

    def test_simple_chain_topological_order(self):
        calcs = {
            "Step1": "SUM([Sales]) - SUM([Cost])",
            "Step2": "[Step1] / SUM([Sales])",
            "FinalMetric": "IF [Step2] > 0.2 THEN 'High' ELSE 'Low' END",
        }
        sorted_nodes = self.resolver.topological_sort(calcs)
        names = [n.name for n in sorted_nodes]
        self.assertEqual(names, ["Step1", "Step2", "FinalMetric"])

    def test_reversed_input_still_resolves(self):
        calcs = {
            "FinalMetric": "IF [Step2] > 0.2 THEN 'High' ELSE 'Low' END",
            "Step2": "[Step1] / SUM([Sales])",
            "Step1": "SUM([Sales]) - SUM([Cost])",
        }
        sorted_nodes = self.resolver.topological_sort(calcs)
        names = [n.name for n in sorted_nodes]
        self.assertLess(names.index("Step1"), names.index("Step2"))
        self.assertLess(names.index("Step2"), names.index("FinalMetric"))

    def test_no_dependencies(self):
        calcs = {
            "A": "SUM([Sales])",
            "B": "SUM([Profit])",
        }
        sorted_nodes = self.resolver.topological_sort(calcs)
        self.assertEqual(len(sorted_nodes), 2)

    def test_circular_dependency_detection(self):
        calcs = {
            "A": "[B] + SUM([Sales])",
            "B": "[A] + SUM([Profit])",
        }
        with self.assertRaises(CircularDependencyError):
            self.resolver.topological_sort(calcs)

    def test_self_referential_dependency(self):
        calcs = {
            "A": "[A] + SUM([Sales])",
        }
        with self.assertRaises(CircularDependencyError):
            self.resolver.topological_sort(calcs)

    def test_missing_dependency_raises_error(self):
        calcs = {
            "A": "[Unknown_Field] + SUM([Sales])",
        }
        with self.assertRaises(MissingDependencyError):
            self.resolver.topological_sort(calcs)

    def test_resolve_items_preserves_objects(self):
        items = [
            CalculationItem(id="dep_Step1", name="Step1", formula="SUM([Sales]) - SUM([Cost])"),
            CalculationItem(id="dep_Step2", name="Step2", formula="[Step1] / SUM([Sales])"),
            CalculationItem(id="dep_Final", name="FinalMetric", formula="IF [Step2] > 0.2 THEN 'High' ELSE 'Low' END"),
        ]
        sorted_items = self.resolver.resolve_items(items)
        self.assertEqual([it.name for it in sorted_items], ["Step1", "Step2", "FinalMetric"])

    def test_case_insensitive_column_matching(self):
        resolver = DependencyResolver({"sales", "profit"})
        calcs = {"A": "SUM([Sales]) + SUM([Profit])"}
        sorted_nodes = resolver.topological_sort(calcs)
        self.assertEqual(len(sorted_nodes), 1)


if __name__ == "__main__":
    unittest.main()
