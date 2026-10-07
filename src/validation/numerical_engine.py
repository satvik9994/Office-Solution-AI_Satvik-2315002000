"""Evidence-based numerical validation for supported Tableau/DAX expressions.

The engine intentionally validates only semantics that can be executed from the
provided tabular sample data. Unsupported visual/table-calculation context is
reported as UNVERIFIABLE instead of being treated as correct.
"""

from dataclasses import dataclass
from typing import Any, Optional
import re
import math
import pandas as pd


@dataclass
class NumericalValidationResult:
    calculation_id: str
    tableau_value: Any
    dax_value: Any
    is_match: bool
    absolute_error: float
    status: str  # VERIFIED | MISMATCH | UNVERIFIABLE_INCOMPLETE_TEMPLATE | UNSUPPORTED
    notes: str


class NumericalEngine:
    """Evaluate a safe subset of Tableau/DAX directly against a DataFrame.

    No calculation id is used to decide the expected value. Formula text and
    DAX semantics determine the evaluation, which makes the engine reusable for
    calculations outside the supplied benchmark ids.
    """

    AGG_RE = re.compile(r"\b(SUM|AVG|AVERAGE|MIN|MAX|COUNT)\s*\(\s*(?:Table\s*)?\[?([A-Za-z_][\w ]*)\]?\s*\)", re.I)
    FIXED_RE = re.compile(r"\{\s*FIXED\s+\[([^\]]+)\]\s*:\s*(.*?)\s*\}", re.I)

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        for col in self.df.columns:
            if col not in {"Region", "Date"}:
                converted = pd.to_numeric(self.df[col], errors="coerce")
                if converted.notna().any():
                    self.df[col] = converted

    @staticmethod
    def _clean_col(name: str) -> str:
        return name.strip().strip("[]").split(".")[-1].strip("[]")

    def _aggregate(self, func: str, col: str, frame: Optional[pd.DataFrame] = None) -> Any:
        frame = self.df if frame is None else frame
        col = self._clean_col(col)
        if col not in frame.columns:
            raise ValueError(f"Unknown column: {col}")
        series = pd.to_numeric(frame[col], errors="coerce")
        func = func.upper()
        if func == "SUM": return float(series.sum())
        if func in {"AVG", "AVERAGE"}: return float(series.mean())
        if func == "MIN": return float(series.min())
        if func == "MAX": return float(series.max())
        if func == "COUNT": return int(series.notna().sum())
        raise ValueError(f"Unsupported aggregate: {func}")

    def _fixed_value(self, expression: str) -> dict:
        match = self.FIXED_RE.search(expression)
        if not match:
            raise ValueError("No FIXED expression")
        dimension = self._clean_col(match.group(1))
        inner = match.group(2)
        if dimension not in self.df.columns:
            raise ValueError(f"Unknown FIXED dimension: {dimension}")
        agg = self.AGG_RE.search(inner)
        if not agg:
            raise ValueError("Unsupported FIXED inner expression")
        result = {}
        for key, group in self.df.groupby(dimension, dropna=False):
            result[str(key)] = self._aggregate(agg.group(1), agg.group(2), group)
        return result

    def _eval_scalar(self, expression: str, frame: Optional[pd.DataFrame] = None) -> Any:
        expression = expression.strip()
        frame = self.df if frame is None else frame
        # Remove Tableau field brackets and DAX table qualifiers.
        expression = re.sub(r"Table\[([^\]]+)\]", r"[\1]", expression, flags=re.I)

        # String literals.
        if re.fullmatch(r"['\"]([^'\"]*)['\"]", expression):
            return expression[1:-1]

        # Numeric literals.
        try:
            if re.fullmatch(r"-?\d+(?:\.\d+)?", expression):
                return float(expression)
        except ValueError:
            pass

        # DAX DIVIDE(a,b).
        m = re.match(r"^DIVIDE\s*\((.*),(.*)\)$", expression, re.I)
        if m:
            denominator = self._eval_scalar(m.group(2), frame)
            if denominator in (0, None):
                return None
            return self._eval_scalar(m.group(1), frame) / denominator

        # Simple aggregates.
        m = self.AGG_RE.fullmatch(expression)
        if m:
            return self._aggregate(m.group(1), m.group(2), frame)

        # Simple arithmetic of supported scalar expressions.
        depth = 0
        for i, ch in enumerate(expression):
            if ch == "(": depth += 1
            elif ch == ")": depth -= 1
            elif ch == "/" and depth == 0:
                left = self._eval_scalar(expression[:i], frame)
                right = self._eval_scalar(expression[i + 1:], frame)
                return left / right if right not in (0, None) else None

        # Numeric comparisons are handled by IF.
        raise ValueError(f"Unsupported scalar expression: {expression}")

    def _eval_if(self, expression: str, frame: Optional[pd.DataFrame] = None) -> Any:
        frame = self.df if frame is None else frame
        m = re.match(r"^IF\s*\((.*)\)$", expression.strip(), re.I)
        if not m:
            m = re.match(r"^IF\s+(.*)\s+THEN\s+(.*)\s+ELSE\s+(.*)\s+END$", expression.strip(), re.I)
            if not m:
                raise ValueError("Unsupported IF expression")
            condition, yes_expr, no_expr = m.groups()
        else:
            parts = self._split_top_level(m.group(1), ",")
            if len(parts) != 3:
                raise ValueError("IF requires condition, true branch and false branch")
            condition, yes_expr, no_expr = parts

        op = re.search(r"(>=|<=|<>|=|>|<)", condition)
        if not op:
            raise ValueError("Unsupported IF condition")
        left = self._eval_scalar(condition[:op.start()].strip(), frame)
        right_text = condition[op.end():].strip()
        try:
            right = self._eval_scalar(right_text, frame)
        except ValueError:
            right = right_text.strip("'\"")
        operator = op.group(1)
        passed = {">": left > right, "<": left < right, ">=": left >= right,
                  "<=": left <= right, "=": left == right, "<>": left != right}[operator]
        return self._eval_scalar(yes_expr, frame) if passed else self._eval_scalar(no_expr, frame)

    @staticmethod
    def _split_top_level(text: str, delimiter: str) -> list[str]:
        parts, start, depth = [], 0, 0
        quote = None
        for i, ch in enumerate(text):
            if quote:
                if ch == quote: quote = None
                continue
            if ch in "'\"": quote = ch; continue
            if ch == "(": depth += 1
            elif ch == ")": depth -= 1
            elif ch == delimiter and depth == 0:
                parts.append(text[start:i].strip()); start = i + 1
        parts.append(text[start:].strip())
        return parts

    def _evaluate_formula(self, formula: str) -> Any:
        formula = formula.strip()
        if "..." in formula:
            raise ValueError("Incomplete template contains ellipsis")
        if re.search(r"\b(WINDOW_SUM|RUNNING_SUM|RANK|WINDOW_AVG|LOOKUP)\b", formula, re.I):
            raise NotImplementedError("Table calculation requires visual/order context")
        fixed = self.FIXED_RE.search(formula)
        if fixed and formula.strip() == fixed.group(0):
            return self._fixed_value(formula)
        if re.match(r"^IF\s*(?:\(|\{?)", formula, re.I):
            return self._eval_if(formula)
        return self._eval_scalar(formula)

    def _evaluate_dax(self, dax: str) -> Any:
        dax = dax.strip()
        if "..." in dax:
            raise ValueError("Incomplete DAX template contains ellipsis")
        if re.search(r"\b(FILTER|ALLSELECTED|ALLEXCEPT)\b", dax, re.I):
            # ALLEXCEPT is executable for a single FIXED dimension.
            m = re.match(r"^CALCULATE\s*\(\s*(.*?)\s*,\s*ALLEXCEPT\s*\(.*?,\s*Table\[([^\]]+)\]\s*\)\s*\)$", dax, re.I)
            if m:
                agg_expr, dimension = m.groups()
                agg = self.AGG_RE.search(agg_expr)
                if not agg:
                    raise ValueError("Unsupported CALCULATE expression")
                return {str(key): self._aggregate(agg.group(1), agg.group(2), group)
                        for key, group in self.df.groupby(self._clean_col(dimension), dropna=False)}
            raise NotImplementedError("DAX filter context requires BI runtime")
        if re.match(r"^IF\s*\(", dax, re.I):
            return self._eval_if(dax)
        return self._eval_scalar(dax)

    @staticmethod
    def _values_match(expected: Any, actual: Any, tolerance: float = 1e-5) -> tuple[bool, float]:
        if isinstance(expected, dict) or isinstance(actual, dict):
            if not isinstance(expected, dict) or not isinstance(actual, dict):
                return False, math.inf
            if set(expected) != set(actual): return False, math.inf
            errors = [abs(float(expected[k]) - float(actual[k])) for k in expected]
            return all(e <= tolerance for e in errors), (max(errors) if errors else 0.0)
        if isinstance(expected, str) or isinstance(actual, str):
            return str(expected) == str(actual), 0.0 if str(expected) == str(actual) else 1.0
        if expected is None or actual is None:
            return expected is actual, 0.0 if expected is actual else math.inf
        error = abs(float(expected) - float(actual))
        return error <= tolerance, error

    def validate_calc(self, calc_id: str, formula: str, dax_str: str, is_legacy: bool = False) -> NumericalValidationResult:
        try:
            expected = self._evaluate_formula(formula)
        except (NotImplementedError, ValueError) as exc:
            status = "UNVERIFIABLE_INCOMPLETE_TEMPLATE" if "ellipsis" in str(exc).lower() else "UNSUPPORTED"
            return NumericalValidationResult(calc_id, None, None, False, math.inf, status, str(exc))

        try:
            actual = self._evaluate_dax(dax_str)
        except (NotImplementedError, ValueError) as exc:
            status = "UNVERIFIABLE_INCOMPLETE_TEMPLATE" if "ellipsis" in str(exc).lower() else "UNSUPPORTED"
            return NumericalValidationResult(calc_id, expected, None, False, math.inf, status, str(exc))

        match, error = self._values_match(expected, actual)
        return NumericalValidationResult(
            calculation_id=calc_id,
            tableau_value=expected,
            dax_value=actual,
            is_match=match,
            absolute_error=round(error, 8) if math.isfinite(error) else error,
            status="VERIFIED" if match else "MISMATCH",
            notes="Numerical parity confirmed" if match else "Numerical values differ",
        )
