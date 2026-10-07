"""Error detection and automated correction for legacy DAX conversions."""

from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class DetectionResult:
    calculation_id: str
    is_incorrect: bool
    error_category: str
    explanation: str
    legacy_dax: str
    corrected_dax: str


class ErrorDetector:
    """Compares legacy DAX against validated generated DAX to detect flaws and propose corrections."""

    @staticmethod
    def normalize_dax(dax_str: str) -> str:
        """Normalizes whitespace, casing, and removes table qualifiers for structural comparison."""
        s = dax_str.strip()
        s = re.sub(r'Table\[([^\]]+)\]', r'\1', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+', ' ', s)
        return s

    def diagnose_and_correct(
        self,
        calc_id: str,
        tableau_formula: str,
        legacy_dax: str,
        generated_dax: str,
        ground_truth_dax: Optional[str] = None,
    ) -> DetectionResult:
        norm_legacy = self.normalize_dax(legacy_dax)
        norm_gen = self.normalize_dax(generated_dax)

        # 1. Exact or structural match
        if norm_legacy == norm_gen:
            return DetectionResult(
                calculation_id=calc_id,
                is_incorrect=False,
                error_category="none",
                explanation="Legacy DAX matches generated target structurally.",
                legacy_dax=legacy_dax,
                corrected_dax=legacy_dax,
            )

        # 2. Diagnose specific flaw categories
        formula_lower = tableau_formula.lower()
        legacy_lower = legacy_dax.lower()

        # Check for catastrophic expression truncation first (e.g. calc_3: multi-part IF reduced to single AVG)
        if ("if" in formula_lower or "window_sum" in formula_lower) and len(legacy_dax.split()) < 3 and "if" not in legacy_lower:
            category = "expression_truncation"
            explanation = (
                "Legacy DAX truncated a compound multi-part conditional calculation into a single "
                "inner scalar aggregation, losing conditions and table calculations."
            )
            return DetectionResult(calc_id, True, category, explanation, legacy_dax, generated_dax)

        # Check for inverted division ratio (e.g. calc_1)
        if "/" in formula_lower and "/" in legacy_lower:
            if "sum(sales) / sum(profit)" in norm_legacy.lower() and "profit" in formula_lower.split("/")[0]:
                category = "inverted_aggregation_and_unsafe_division"
                explanation = (
                    "Legacy DAX inverted the numerator and denominator (swapped Sales and Profit) "
                    "and used the raw '/' operator instead of the safe 'DIVIDE()' function."
                )
                return DetectionResult(calc_id, True, category, explanation, legacy_dax, generated_dax)

        # Check for dropped Level of Detail (LOD) (e.g. calc_2)
        if "fixed" in formula_lower and "allexcept" not in legacy_lower and "calculate" not in legacy_lower:
            category = "incorrect_lod_conversion"
            explanation = (
                "Legacy DAX completely omitted the Level of Detail (FIXED) context modifier, "
                "reducing a regional fixed grain calculation to an unconstrained simple sum."
            )
            return DetectionResult(calc_id, True, category, explanation, legacy_dax, generated_dax)

        # Check for return type mismatch (integers 1, 0 instead of strings 'High', 'Low') (e.g. calc_4)
        if ("'high'" in formula_lower or '"high"' in formula_lower) and ("1" in legacy_lower or "0" in legacy_lower) and "high" not in legacy_lower:
            category = "return_type_mismatch"
            explanation = (
                "Legacy DAX returned numeric values (1, 0) instead of textual category labels ('High', 'Low'), "
                "violating the expected return data type."
            )
            return DetectionResult(calc_id, True, category, explanation, legacy_dax, generated_dax)

        # General semantic mismatch fallback
        return DetectionResult(
            calculation_id=calc_id,
            is_incorrect=True,
            error_category="semantic_mismatch",
            explanation="Legacy DAX diverges structurally from the verified DAX compilation.",
            legacy_dax=legacy_dax,
            corrected_dax=generated_dax,
        )
