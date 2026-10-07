"""Unit tests for visual mapping and confidence scoring."""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath('src'))

from visual_mapping.visual_mapper import VisualMapper
from intelligence.scorer import ConfidenceScorer
from ingestion.models import VisualItem


class TestVisualMapper(unittest.TestCase):

    def setUp(self):
        self.mapper = VisualMapper()

    def test_bar_to_clustered_column(self):
        result = self.mapper.map_visual("vis_1", "bar", ["Region"], ["Profit_Ratio"], "clustered column chart")
        self.assertEqual(result.predicted_powerbi, "clustered column chart")
        self.assertTrue(result.is_match)
        self.assertGreaterEqual(result.confidence, 0.90)

    def test_line_with_temporal_dimension(self):
        result = self.mapper.map_visual("vis_2", "line", ["Date"], ["RunningSales"], "line chart")
        self.assertEqual(result.predicted_powerbi, "line chart")
        self.assertTrue(result.is_match)
        self.assertGreaterEqual(result.confidence, 0.95)

    def test_line_without_temporal(self):
        result = self.mapper.map_visual("vis_x", "line", ["Category"], ["Sales"], None)
        self.assertEqual(result.predicted_powerbi, "line chart")
        self.assertGreaterEqual(result.confidence, 0.80)

    def test_bar_no_dimensions_maps_to_card(self):
        result = self.mapper.map_visual("vis_x", "bar", [], ["Sales"], None)
        self.assertEqual(result.predicted_powerbi, "card")

    def test_pie_to_donut(self):
        result = self.mapper.map_visual("vis_x", "pie", ["Region"], ["Sales"], None)
        self.assertEqual(result.predicted_powerbi, "donut chart")

    def test_text_to_table(self):
        result = self.mapper.map_visual("vis_x", "text", ["Region"], ["Sales"], None)
        self.assertEqual(result.predicted_powerbi, "table")

    def test_unknown_visual_fallback(self):
        result = self.mapper.map_visual("vis_x", "gantt", ["Region"], ["Sales"], None)
        self.assertEqual(result.predicted_powerbi, "table")
        self.assertLessEqual(result.confidence, 0.50)

    def test_extract_visual_context(self):
        items = [
            VisualItem(id="vis_2", tableau_visual="line", dimensions=["Date"], measures=["RunningSales"]),
        ]
        context = self.mapper.extract_visual_context_for_measures(items)
        self.assertIn("RunningSales", context)
        self.assertEqual(context["RunningSales"]["visual_type"], "line")
        self.assertIn("Date", context["RunningSales"]["order_by"])

    def test_is_temporal_dimension(self):
        self.assertTrue(self.mapper.is_temporal_dimension("Date"))
        self.assertTrue(self.mapper.is_temporal_dimension("OrderMonth"))
        self.assertFalse(self.mapper.is_temporal_dimension("Region"))


class TestConfidenceScorer(unittest.TestCase):

    def setUp(self):
        self.scorer = ConfidenceScorer()

    def test_perfect_simple_calc(self):
        result = self.scorer.calculate(numerical_match=True)
        self.assertEqual(result.overall_score, 1.0)

    def test_syntax_error_zeroes_confidence(self):
        result = self.scorer.calculate(has_syntax_error=True)
        self.assertEqual(result.overall_score, 0.0)

    def test_circular_dependency_zeroes_confidence(self):
        result = self.scorer.calculate(has_circular_dependency=True)
        self.assertEqual(result.overall_score, 0.0)

    def test_lod_reduces_semantic(self):
        result = self.scorer.calculate(has_lod=True, numerical_match=True)
        self.assertLess(result.overall_score, 1.0)
        self.assertGreater(result.overall_score, 0.90)

    def test_table_calc_without_context_penalized(self):
        result = self.scorer.calculate(has_table_calc=True, has_visual_context=False, numerical_match=True)
        self.assertLessEqual(result.overall_score, 0.85)

    def test_table_calc_with_context_boosted(self):
        result = self.scorer.calculate(has_table_calc=True, has_visual_context=True, numerical_match=True)
        self.assertGreater(result.overall_score, 0.80)

    def test_numerical_mismatch_capped(self):
        result = self.scorer.calculate(numerical_match=False)
        self.assertLessEqual(result.overall_score, 0.30)

    def test_template_ellipsis_reduces_validation(self):
        result = self.scorer.calculate(numerical_match=True, is_template_ellipsis=True)
        self.assertLess(result.overall_score, 1.0)

    def test_unsupported_functions_reduce_semantic(self):
        result = self.scorer.calculate(unsupported_functions_count=2, numerical_match=True)
        self.assertLess(result.semantic_score, 0.50)


if __name__ == "__main__":
    unittest.main()
