"""Intermediate Representation (IR) semantic node hierarchy."""

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, List, Optional


class AggregationType(Enum):
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    COUNT = "COUNT"
    COUNTD = "COUNTD"


class BinaryOperator(Enum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"


class ComparisonOperator(Enum):
    EQ = "="
    NEQ = "<>"
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="


class LODType(Enum):
    FIXED = "FIXED"
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


class TableCalcType(Enum):
    WINDOW_SUM = "WINDOW_SUM"
    RUNNING_SUM = "RUNNING_SUM"
    RANK = "RANK"


@dataclass(frozen=True)
class IRNode(ABC):
    """Base class for all Intermediate Representation nodes."""
    pass


@dataclass(frozen=True)
class IRLiteral(IRNode):
    """Represents a constant number, string, or boolean."""
    value: Any
    data_type: str  # 'number' | 'string' | 'boolean'


@dataclass(frozen=True)
class IRFieldReference(IRNode):
    """Represents a reference to a dataset column or calculated measure."""
    name: str
    is_measure: bool = False
    table_name: Optional[str] = None


@dataclass(frozen=True)
class IRAggregation(IRNode):
    """Represents an aggregation function: SUM([Sales]), AVG([Profit])."""
    agg_type: AggregationType
    expression: IRNode


@dataclass(frozen=True)
class IRBinaryOp(IRNode):
    """Represents arithmetic operations: A + B, A / B."""
    op: BinaryOperator
    left: IRNode
    right: IRNode


@dataclass(frozen=True)
class IRComparison(IRNode):
    """Represents boolean comparisons: A > B, A = B."""
    op: ComparisonOperator
    left: IRNode
    right: IRNode


@dataclass(frozen=True)
class IRConditional(IRNode):
    """Represents conditional logic: IF cond THEN then_expr ELSE else_expr END."""
    condition: IRNode
    then_expr: IRNode
    else_expr: IRNode


@dataclass(frozen=True)
class IRLODExpression(IRNode):
    """Represents Tableau Level of Detail expressions: {FIXED [Region]: SUM([Sales])}."""
    lod_type: LODType
    dimensions: List[str]
    expression: IRNode


@dataclass(frozen=True)
class IRTableCalculation(IRNode):
    """Represents Tableau Table Calculations: RUNNING_SUM, WINDOW_SUM, RANK."""
    calc_type: TableCalcType
    inner_expression: IRNode
    partition_by: List[str] = field(default_factory=list)
    order_by: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class IRUnsupportedFunction(IRNode):
    """Fallback representation for unknown or unsupported Tableau functions."""
    function_name: str
    arguments: List[IRNode]
