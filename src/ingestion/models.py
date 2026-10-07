"""Domain models for data ingestion and representation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CalculationItem:
    """Represents a standardized Tableau calculation item."""
    id: str
    name: str
    formula: str
    source_type: str = "json_calc"  # "json_calc" | "json_dep" | "xml_calc"
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualItem:
    """Represents a visual configuration from Tableau."""
    id: str
    tableau_visual: str
    dimensions: List[str]
    measures: List[str]
    expected_powerbi: Optional[str] = None


@dataclass
class IncorrectDaxItem:
    """Represents a flawed legacy DAX conversion item."""
    id: str
    dax: str


@dataclass
class GroundTruthItem:
    """Represents a certified ground truth DAX conversion item."""
    id: str
    dax: str
