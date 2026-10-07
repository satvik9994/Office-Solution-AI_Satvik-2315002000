"""Visual mapping engine converting Tableau visual metadata to Power BI visual archetypes."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from ingestion.models import VisualItem


@dataclass
class VisualMappingResult:
    visual_id: str
    tableau_visual: str
    predicted_powerbi: str
    expected_powerbi: Optional[str]
    confidence: float
    is_match: bool
    explanation: str


class VisualMapper:
    """Determines Power BI visual archetypes based on Tableau mark types, dimensions, and measures."""

    def __init__(self, temporal_keywords: Optional[Set[str]] = None):
        self.temporal_keywords = temporal_keywords or {"date", "time", "year", "month", "day", "quarter"}

    def is_temporal_dimension(self, dim_name: str) -> bool:
        """Checks if a dimension identifier represents a temporal/time-series axis."""
        return any(keyword in dim_name.lower() for keyword in self.temporal_keywords)

    def map_visual(
        self,
        visual_id: str,
        tableau_visual: str,
        dimensions: List[str],
        measures: List[str],
        expected_powerbi: Optional[str] = None,
    ) -> VisualMappingResult:
        t_type = tableau_visual.lower().strip()
        dim_count = len(dimensions)
        has_temporal = any(self.is_temporal_dimension(d) for d in dimensions)

        predicted = "table"
        confidence = 0.50
        explanation = ""

        if t_type == "bar":
            if dim_count >= 1:
                predicted = "clustered column chart"
                confidence = 0.95
                explanation = f"Tableau 'bar' with discrete dimension(s) {dimensions} maps to Power BI vertical clustered column chart."
            else:
                predicted = "card"
                confidence = 0.90
                explanation = "Tableau bar with 0 dimensions maps to single KPI card."

        elif t_type == "line":
            predicted = "line chart"
            if has_temporal:
                confidence = 0.98
                explanation = f"Tableau 'line' over temporal dimension(s) {dimensions} maps to Power BI line chart."
            else:
                confidence = 0.85
                explanation = f"Tableau 'line' over categorical dimension(s) {dimensions} maps to Power BI line chart."

        elif t_type in ("circle", "pie"):
            predicted = "donut chart"
            confidence = 0.85
            explanation = f"Tableau '{t_type}' mark maps to Power BI proportional donut chart."

        elif t_type in ("text", "table"):
            predicted = "matrix" if dim_count > 1 else "table"
            confidence = 0.95
            explanation = f"Tableau tabular data maps to Power BI {predicted}."

        else:
            predicted = "table"
            confidence = 0.40
            explanation = f"Unmapped visual type '{t_type}', falling back to table view."

        is_match = (predicted.lower() == expected_powerbi.lower()) if expected_powerbi else True

        return VisualMappingResult(
            visual_id=visual_id,
            tableau_visual=tableau_visual,
            predicted_powerbi=predicted,
            expected_powerbi=expected_powerbi,
            confidence=confidence,
            is_match=is_match,
            explanation=explanation,
        )

    def extract_visual_context_for_measures(self, visual_items: List[VisualItem]) -> Dict[str, Dict]:
        """Extracts dimensional context (e.g. order_by axis) to ground table calculations."""
        context_map = {}
        for vis in visual_items:
            for measure_name in vis.measures:
                context_map[measure_name] = {
                    "visual_id": vis.id,
                    "visual_type": vis.tableau_visual,
                    "dimensions": vis.dimensions,
                    "order_by": [d for d in vis.dimensions if self.is_temporal_dimension(d)] or vis.dimensions,
                }
        return context_map
