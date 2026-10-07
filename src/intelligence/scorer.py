"""Multi-factor deterministic confidence scoring engine."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfidenceBreakdown:
    syntax_score: float
    semantic_score: float
    validation_score: float
    context_score: float
    overall_score: float
    explanation: str


class ConfidenceScorer:
    """Calculates calibrated, explainable confidence scores for BI migrations."""

    def __init__(
        self,
        w_syntax: float = 0.20,
        w_semantic: float = 0.35,
        w_validation: float = 0.25,
        w_context: float = 0.20,
    ):
        self.w_syntax = w_syntax
        self.w_semantic = w_semantic
        self.w_validation = w_validation
        self.w_context = w_context

    def calculate(
        self,
        has_syntax_error: bool = False,
        has_circular_dependency: bool = False,
        unsupported_functions_count: int = 0,
        has_lod: bool = False,
        has_table_calc: bool = False,
        has_visual_context: bool = False,
        numerical_match: Optional[bool] = None,
        is_template_ellipsis: bool = False,
    ) -> ConfidenceBreakdown:

        # 1. Hard Overrides
        if has_syntax_error:
            return ConfidenceBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, "Syntax parse error")
        if has_circular_dependency:
            return ConfidenceBreakdown(1.0, 0.0, 0.0, 0.0, 0.0, "Circular dependency cycle detected")

        # 2. Syntax Score
        s_syntax = 1.0

        # 3. Semantic Rule Score
        s_semantic = 1.0
        if has_lod:
            s_semantic -= 0.05
        if has_table_calc:
            s_semantic -= 0.15
        if unsupported_functions_count > 0:
            s_semantic -= 0.50 * unsupported_functions_count
        s_semantic = max(0.0, s_semantic)

        # 4. Validation Score
        if numerical_match is True:
            s_val = 0.85 if is_template_ellipsis else 1.0
        elif numerical_match is False:
            s_val = 0.0  # Proven mathematical discrepancy
        else:
            s_val = 0.70 if is_template_ellipsis else 0.60

        # 5. Context Score
        if has_table_calc:
            s_context = 0.85 if has_visual_context else 0.40
        else:
            s_context = 1.0

        # 6. Weighted Sum
        overall = (
            self.w_syntax * s_syntax
            + self.w_semantic * s_semantic
            + self.w_validation * s_val
            + self.w_context * s_context
        )

        # Cap overall score if numerical mismatch occurred
        if numerical_match is False:
            overall = min(overall, 0.30)

        overall = round(max(0.0, min(1.0, overall)), 2)
        explanation = f"Syntax: {s_syntax:.2f}, Semantic: {s_semantic:.2f}, Validation: {s_val:.2f}, Context: {s_context:.2f}"

        return ConfidenceBreakdown(
            syntax_score=s_syntax,
            semantic_score=s_semantic,
            validation_score=s_val,
            context_score=s_context,
            overall_score=overall,
            explanation=explanation,
        )
