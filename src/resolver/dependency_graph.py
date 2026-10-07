"""Dependency resolution and topological sorting for multi-step calculations."""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Set, Tuple
from ingestion.models import CalculationItem


class CircularDependencyError(Exception):
    """Raised when a circular reference/cycle is detected among calculations."""
    pass


class MissingDependencyError(Exception):
    """Raised when a formula references an unknown calculation or column."""
    pass


@dataclass
class DependencyNode:
    name: str
    formula: str
    dependencies: Set[str] = field(default_factory=set)  # Upstream prerequisites
    dependents: Set[str] = field(default_factory=set)    # Downstream dependents
    in_degree: int = 0


class DependencyResolver:
    """Builds a Directed Acyclic Graph (DAG) of calculation dependencies

    and resolves evaluation order using Kahn's topological sort algorithm.
    """

    def __init__(self, physical_columns: Set[str]):
        # Store canonical lowercase set for case-insensitive column matching
        self.physical_columns = {col.lower().strip() for col in physical_columns}

    def extract_identifiers(self, formula: str) -> Set[str]:
        """Extracts all bracketed tokens [Token] from a formula string."""
        tokens = re.findall(r'\[([^\]]+)\]', formula)
        return {token.strip() for token in tokens}

    def build_graph(self, calculations: Dict[str, str]) -> Dict[str, DependencyNode]:
        """Constructs the adjacency graph and computes in-degrees.

        calculations: mapping of {calc_name: formula_string}
        """
        nodes: Dict[str, DependencyNode] = {}
        # Case-insensitive name lookup mapping lowercase_name -> original_name
        name_lookup = {name.lower().strip(): name for name in calculations}

        for name, formula in calculations.items():
            nodes[name] = DependencyNode(name=name, formula=formula)

        for name, formula in calculations.items():
            tokens = self.extract_identifiers(formula)
            for token in tokens:
                token_lower = token.lower()
                # If token is a physical column, it is not an inter-calculation dependency
                if token_lower in self.physical_columns:
                    continue

                # If token matches another calculation in the model
                if token_lower in name_lookup:
                    prereq_name = name_lookup[token_lower]
                    if prereq_name == name:
                        raise CircularDependencyError(
                            f"Self-referential circular dependency detected in calculation '{name}'"
                        )
                    nodes[name].dependencies.add(prereq_name)
                    nodes[prereq_name].dependents.add(name)
                else:
                    raise MissingDependencyError(
                        f"Calculation '{name}' references unknown field or calculation: [{token}]"
                    )

        # Set initial in-degrees based on prerequisite count
        for node in nodes.values():
            node.in_degree = len(node.dependencies)

        return nodes

    def topological_sort(self, calculations: Dict[str, str]) -> List[DependencyNode]:
        """Computes topological execution order using Kahn's algorithm.

        Raises CircularDependencyError if a cycle is detected.
        """
        nodes = self.build_graph(calculations)
        
        # Initialize queue with nodes that have in-degree 0 (no prerequisites)
        queue = [node for node in nodes.values() if node.in_degree == 0]
        sorted_nodes: List[DependencyNode] = []
        in_degrees = {name: node.in_degree for name, node in nodes.items()}

        while queue:
            # Deterministic pop (alphabetical by name if multiple have in-degree 0)
            queue.sort(key=lambda n: n.name)
            current = queue.pop(0)
            sorted_nodes.append(current)

            for dependent_name in current.dependents:
                in_degrees[dependent_name] -= 1
                if in_degrees[dependent_name] == 0:
                    queue.append(nodes[dependent_name])

        if len(sorted_nodes) < len(nodes):
            unresolved = [name for name, deg in in_degrees.items() if deg > 0]
            raise CircularDependencyError(
                f"Circular dependency detected among calculations: {unresolved}"
            )

        return sorted_nodes

    def resolve_items(self, items: List[CalculationItem]) -> List[CalculationItem]:
        """Accepts a list of CalculationItem objects and returns them sorted by dependency order."""
        calc_map = {item.name: item.formula for item in items}
        sorted_nodes = self.topological_sort(calc_map)
        item_map = {item.name: item for item in items}
        return [item_map[node.name] for node in sorted_nodes]
