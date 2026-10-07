"""DAX code generator from Intermediate Representation (IR) trees."""

from typing import Optional, Set
from ir.ir_nodes import (
    IRNode,
    IRLiteral,
    IRFieldReference,
    IRAggregation,
    IRBinaryOp,
    IRComparison,
    IRConditional,
    IRLODExpression,
    IRTableCalculation,
    IRUnsupportedFunction,
    AggregationType,
    BinaryOperator,
    ComparisonOperator,
    LODType,
    TableCalcType,
)


class DAXEmitter:
    """Traverses an Intermediate Representation (IR) tree and emits idiomatic DAX."""

    def __init__(self, table_name: str = "Table", physical_columns: Optional[Set[str]] = None):
        self.table_name = table_name
        self.physical_columns = {col.lower().strip() for col in physical_columns} if physical_columns else set()

    def emit(self, node: IRNode) -> str:
        """Main entry point to serialize an IR node into a DAX string."""
        if isinstance(node, IRLiteral):
            return self.emit_literal(node)
        elif isinstance(node, IRFieldReference):
            return self.emit_field_reference(node)
        elif isinstance(node, IRAggregation):
            return self.emit_aggregation(node)
        elif isinstance(node, IRBinaryOp):
            return self.emit_binary_op(node)
        elif isinstance(node, IRComparison):
            return self.emit_comparison(node)
        elif isinstance(node, IRConditional):
            return self.emit_conditional(node)
        elif isinstance(node, IRLODExpression):
            return self.emit_lod_expression(node)
        elif isinstance(node, IRTableCalculation):
            return self.emit_table_calculation(node)
        elif isinstance(node, IRUnsupportedFunction):
            return self.emit_unsupported(node)
        else:
            raise TypeError(f"Unknown IR node type: {type(node)}")

    def emit_literal(self, node: IRLiteral) -> str:
        if node.data_type == "string":
            # In DAX, strings are enclosed in double quotes
            escaped = str(node.value).replace('"', '""')
            return f'"{escaped}"'
        elif node.data_type == "number":
            return str(node.value)
        elif node.value is None:
            return "BLANK()"
        return str(node.value)

    def emit_field_reference(self, node: IRFieldReference) -> str:
        field_lower = node.name.lower().strip()
        # If explicitly marked as measure or NOT in physical columns when physical columns provided
        if node.is_measure or (self.physical_columns and field_lower not in self.physical_columns):
            return f"[{node.name}]"
        # Otherwise, physical column qualified with table name
        return f"{self.table_name}[{node.name}]"

    def emit_aggregation(self, node: IRAggregation) -> str:
        inner_str = self.emit(node.expression)
        if node.agg_type == AggregationType.COUNTD:
            return f"DISTINCTCOUNT({inner_str})"
        return f"{node.agg_type.value}({inner_str})"

    def emit_binary_op(self, node: IRBinaryOp) -> str:
        left_str = self.emit(node.left)
        right_str = self.emit(node.right)

        if node.op == BinaryOperator.DIVIDE:
            return f"DIVIDE({left_str}, {right_str})"
        elif node.op == BinaryOperator.MULTIPLY and isinstance(node.left, IRLiteral) and node.left.value == -1:
            return f"-{right_str}"
        return f"{left_str} {node.op.value} {right_str}"

    def emit_comparison(self, node: IRComparison) -> str:
        left_str = self.emit(node.left)
        right_str = self.emit(node.right)
        return f"{left_str} {node.op.value} {right_str}"

    def emit_conditional(self, node: IRConditional) -> str:
        cond_str = self.emit(node.condition)
        then_str = self.emit(node.then_expr)
        else_str = self.emit(node.else_expr)
        return f"IF({cond_str}, {then_str}, {else_str})"

    def emit_lod_expression(self, node: IRLODExpression) -> str:
        inner_str = self.emit(node.expression)
        if node.lod_type == LODType.FIXED:
            dim_qualifiers = [f"{self.table_name}[{d}]" for d in node.dimensions]
            dims_str = ", ".join(dim_qualifiers)
            return f"CALCULATE({inner_str}, ALLEXCEPT({self.table_name}, {dims_str}))"
        elif node.lod_type == LODType.INCLUDE:
            dim_qualifiers = [f"{self.table_name}[{d}]" for d in node.dimensions]
            dims_str = ", ".join(dim_qualifiers)
            return f"CALCULATE({inner_str}, ALLSELECTED({dims_str}))"
        else:  # EXCLUDE
            dim_qualifiers = [f"{self.table_name}[{d}]" for d in node.dimensions]
            dims_str = ", ".join(dim_qualifiers)
            return f"CALCULATE({inner_str}, ALL({dims_str}))"

    def emit_table_calculation(self, node: IRTableCalculation) -> str:
        inner_str = self.emit(node.inner_expression)

        if node.calc_type == TableCalcType.WINDOW_SUM:
            # Emits full table or visual slice filter removal
            return f"CALCULATE({inner_str}, ALLSELECTED({self.table_name}))"

        elif node.calc_type == TableCalcType.RUNNING_SUM:
            # If ordering dimension is provided via visual context
            order_dim = node.order_by[0] if node.order_by else "Date"
            return f"CALCULATE({inner_str}, FILTER(ALLSELECTED({self.table_name}[{order_dim}]), {self.table_name}[{order_dim}] <= MAX({self.table_name}[{order_dim}])))"

        elif node.calc_type == TableCalcType.RANK:
            dim = node.partition_by[0] if node.partition_by else (node.order_by[0] if node.order_by else "Dimension")
            return f"RANKX(ALLSELECTED({self.table_name}[{dim}]), {inner_str}, , DESC)"

        return inner_str

    def emit_unsupported(self, node: IRUnsupportedFunction) -> str:
        return f"/* Unsupported function: {node.function_name} */ BLANK()"
