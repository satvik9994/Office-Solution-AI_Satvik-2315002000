"""Evidence-based evaluation metrics for the BI migration benchmark.

The benchmark deliberately keeps structural, numerical, detection, and correction
metrics separate. Incomplete ground-truth templates are excluded from metrics
that cannot be certified from the supplied evidence.
"""

from dataclasses import dataclass
from typing import Dict, List, Any
import re


@dataclass
class BenchmarkSummary:
    baseline_dax_accuracy: float
    engine_dax_accuracy: float
    net_accuracy_gain: float
    flaw_detection_rate: float
    correction_success_rate: float
    numerical_agreement_rate: float
    baseline_numerical_agreement_rate: float
    visual_mapping_accuracy: float
    baseline_mean_confidence: float
    engine_mean_confidence: float
    structural_baseline_numerator: int
    structural_denominator: int
    structural_engine_numerator: int
    numerical_baseline_numerator: int
    numerical_denominator: int
    numerical_engine_numerator: int
    detection_numerator: int
    detection_denominator: int
    correction_numerator: int
    correction_denominator: int
    incomplete_ground_truth_count: int


class MetricsCalculator:
    """Calculates metrics only from explicit evidence in evaluation records."""

    @staticmethod
    def normalize_dax(dax_str: str) -> str:
        """Normalize harmless formatting/table-qualification differences."""
        s = (dax_str or "").strip()
        s = re.sub(r"Table\[([^\]]+)\]", r"[\1]", s, flags=re.IGNORECASE)
        s = re.sub(r"\[([^\]]+)\]", r"\1", s)
        s = re.sub(r"\s+", " ", s)
        s = s.replace(" ", "")
        return s.lower()

    @classmethod
    def structural_match(cls, actual: str, expected: str) -> bool:
        """Return True when formulas are structurally equivalent after normalization."""
        return cls.normalize_dax(actual) == cls.normalize_dax(expected)

    @staticmethod
    def _is_ground_truth_verifiable(item: Dict[str, Any]) -> bool:
        target = item.get("ground_truth_dax", "")
        return bool(target) and "..." not in target

    @staticmethod
    def _is_numerically_verifiable(item: Dict[str, Any], prefix: str) -> bool:
        status = item.get(f"{prefix}_numerical_status")
        return status in {"VERIFIED", "MISMATCH"}

    @classmethod
    def calculate_summary(
        cls,
        evaluation_items: List[Dict[str, Any]],
        visual_results: List[Any],
    ) -> BenchmarkSummary:
        if not evaluation_items:
            raise ValueError("No evaluation items provided.")

        structural_items = [
            item for item in evaluation_items
            if cls._is_ground_truth_verifiable(item)
        ]

        baseline_structural_matches = sum(
            1 for item in structural_items if item["baseline_structural_match"]
        )
        engine_structural_matches = sum(
            1 for item in structural_items if item["engine_structural_match"]
        )

        baseline_num_items = [
            item for item in evaluation_items
            if cls._is_numerically_verifiable(item, "baseline")
        ]
        engine_num_items = [
            item for item in evaluation_items
            if cls._is_numerically_verifiable(item, "engine")
        ]

        baseline_num_matches = sum(
            1 for item in baseline_num_items if item["baseline_numerical_match"]
        )
        engine_num_matches = sum(
            1 for item in engine_num_items if item["engine_numerical_match"]
        )

        # The supplied incorrect_dax.json is the benchmark's labelled flawed set.
        known_flaws = sum(1 for item in evaluation_items if item["is_flawed_baseline"])
        detected_flaws = sum(1 for item in evaluation_items if item["flaw_detected"])

        # A correction is "successful" only when it is fully certifiable.
        correction_candidates = [
            item for item in evaluation_items if item["is_flawed_baseline"]
        ]
        successful_corrections = sum(
            1 for item in correction_candidates
            if item["correction_fully_verified"]
        )

        visual_matches = sum(1 for v in visual_results if v.is_match)

        structural_den = len(structural_items)
        numerical_den = len(engine_num_items)
        baseline_numerical_den = len(baseline_num_items)
        correction_den = len(correction_candidates)

        baseline_acc = (
            baseline_structural_matches / structural_den if structural_den else 0.0
        )
        engine_acc = (
            engine_structural_matches / structural_den if structural_den else 0.0
        )
        baseline_num_rate = (
            baseline_num_matches / baseline_numerical_den
            if baseline_numerical_den else 0.0
        )
        engine_num_rate = (
            engine_num_matches / numerical_den if numerical_den else 0.0
        )
        detection_rate = detected_flaws / known_flaws if known_flaws else 0.0
        correction_rate = (
            successful_corrections / correction_den if correction_den else 0.0
        )
        visual_rate = (
            visual_matches / len(visual_results) if visual_results else 0.0
        )

        baseline_conf = sum(
            float(item["baseline_confidence"]) for item in evaluation_items
        ) / len(evaluation_items)
        engine_conf = sum(
            float(item["engine_confidence"]) for item in evaluation_items
        ) / len(evaluation_items)

        return BenchmarkSummary(
            baseline_dax_accuracy=round(baseline_acc * 100, 1),
            engine_dax_accuracy=round(engine_acc * 100, 1),
            net_accuracy_gain=round((engine_acc - baseline_acc) * 100, 1),
            flaw_detection_rate=round(detection_rate * 100, 1),
            correction_success_rate=round(correction_rate * 100, 1),
            numerical_agreement_rate=round(engine_num_rate * 100, 1),
            baseline_numerical_agreement_rate=round(baseline_num_rate * 100, 1),
            visual_mapping_accuracy=round(visual_rate * 100, 1),
            baseline_mean_confidence=round(baseline_conf, 2),
            engine_mean_confidence=round(engine_conf, 2),
            structural_baseline_numerator=baseline_structural_matches,
            structural_denominator=structural_den,
            structural_engine_numerator=engine_structural_matches,
            numerical_baseline_numerator=baseline_num_matches,
            numerical_denominator=baseline_numerical_den,
            numerical_engine_numerator=engine_num_matches,
            detection_numerator=detected_flaws,
            detection_denominator=known_flaws,
            correction_numerator=successful_corrections,
            correction_denominator=correction_den,
            incomplete_ground_truth_count=len(evaluation_items) - structural_den,
        )
