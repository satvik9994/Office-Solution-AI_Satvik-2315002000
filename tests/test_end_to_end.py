"""End-to-end integration tests running the full pipeline against real data."""

import unittest
import sys, os
import json
sys.path.insert(0, os.path.abspath('src'))

from ingestion.file_reader import (
    load_calculations, load_dependencies, load_tableau_xml,
    load_incorrect_dax, load_ground_truth, load_visuals, load_sample_data,
)
from resolver.dependency_graph import DependencyResolver
from parser.parser import Parser
from translator.dax_emitter import DAXEmitter
from validation.error_detector import ErrorDetector
from validation.numerical_engine import NumericalEngine
from visual_mapping.visual_mapper import VisualMapper
from intelligence.scorer import ConfidenceScorer
from evaluation.metrics import MetricsCalculator


class TestEndToEndPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.calcs = load_calculations("data/tableau_calculations.json")
        cls.deps = load_dependencies("data/tableau_dependencies.json")
        cls.xml_calcs = load_tableau_xml("data/tableau_xml.xml")
        cls.incorrect_map = load_incorrect_dax("data/incorrect_dax.json")
        cls.gt_map = load_ground_truth("data/ground_truth.json")
        cls.visuals = load_visuals("data/visuals.json")
        cls.df = load_sample_data("data/sample_data.csv")
        cls.physical = set(cls.df.columns)
        cls.emitter = DAXEmitter(table_name="Table", physical_columns=cls.physical)
        cls.detector = ErrorDetector()

    def test_all_calcs_parse_without_error(self):
        for c in self.calcs:
            ir = Parser.parse_formula(c.formula)
            self.assertIsNotNone(ir)

    def test_all_calcs_emit_dax_without_error(self):
        for c in self.calcs:
            ir = Parser.parse_formula(c.formula)
            dax = self.emitter.emit(ir)
            self.assertIsInstance(dax, str)
            self.assertGreater(len(dax), 0)

    def test_xml_calcs_parse_and_emit(self):
        for c in self.xml_calcs:
            ir = Parser.parse_formula(c.formula)
            dax = self.emitter.emit(ir)
            self.assertIsNotNone(dax)
            self.assertGreater(len(dax), 0)

    def test_dependency_resolution(self):
        resolver = DependencyResolver(self.physical)
        sorted_deps = resolver.resolve_items(self.deps)
        names = [d.name for d in sorted_deps]
        self.assertEqual(names, ["Step1", "Step2", "FinalMetric"])

    def test_all_incorrect_dax_detected_as_flawed(self):
        for c in self.calcs:
            ir = Parser.parse_formula(c.formula)
            gen_dax = self.emitter.emit(ir)
            legacy_dax = self.incorrect_map[c.id].dax if c.id in self.incorrect_map else ""
            gt_dax = self.gt_map[c.id].dax if c.id in self.gt_map else ""
            result = self.detector.diagnose_and_correct(c.id, c.formula, legacy_dax, gen_dax, gt_dax)
            self.assertTrue(result.is_incorrect, f"Expected calc {c.id} legacy DAX to be detected as incorrect")

    def test_visual_mapping_matches_expected(self):
        mapper = VisualMapper()
        for vis in self.visuals:
            result = mapper.map_visual(vis.id, vis.tableau_visual, vis.dimensions, vis.measures, vis.expected_powerbi)
            self.assertTrue(result.is_match, f"Visual {vis.id} mapping failed: {result.predicted_powerbi} != {vis.expected_powerbi}")

    def test_pipeline_output_has_required_fields(self):
        """Verify the output contract matches the company schema."""
        output_path = "output/migration_results.json"
        if os.path.exists(output_path):
            with open(output_path, "r") as f:
                results = json.load(f)
            for item in results:
                self.assertIn("predicted_dax", item)
                self.assertIn("visual_mapping", item)
                self.assertIn("confidence_score", item)
                self.assertIn("is_corrected", item)
                self.assertIsInstance(item["confidence_score"], (int, float))
                self.assertIsInstance(item["is_corrected"], bool)

    def test_confidence_scores_in_valid_range(self):
        scorer = ConfidenceScorer()
        for c in self.calcs:
            has_lod = "fixed" in c.formula.lower()
            has_tc = any(tc in c.formula.lower() for tc in ["window_sum", "running_sum", "rank"])
            result = scorer.calculate(has_lod=has_lod, has_table_calc=has_tc, numerical_match=True)
            self.assertGreaterEqual(result.overall_score, 0.0)
            self.assertLessEqual(result.overall_score, 1.0)

    def test_numerical_engine_agrees_on_corrected(self):
        engine = NumericalEngine(self.df)
        for cid in ["calc_1", "calc_4"]:
            c = next(c for c in self.calcs if c.id == cid)
            ir = Parser.parse_formula(c.formula)
            dax = self.emitter.emit(ir)
            result = engine.validate_calc(cid, c.formula, dax, is_legacy=False)
            self.assertTrue(result.is_match, f"Numerical mismatch for {cid}")


if __name__ == "__main__":
    unittest.main()
