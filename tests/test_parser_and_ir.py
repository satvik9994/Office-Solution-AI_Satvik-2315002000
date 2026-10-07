"""Unit tests for lexer, parser, and IR node construction."""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath('src'))

from parser.lexer import Lexer, LexerError
from parser.parser import Parser, ParserError
from parser.tokens import TokenType
from ir.ir_nodes import (
    IRAggregation, IRBinaryOp, IRComparison, IRConditional,
    IRFieldReference, IRLiteral, IRLODExpression, IRTableCalculation,
    IRUnsupportedFunction, AggregationType, BinaryOperator,
    ComparisonOperator, LODType, TableCalcType,
)


class TestLexer(unittest.TestCase):

    def test_simple_sum(self):
        tokens = Lexer("SUM([Sales])").tokenize()
        types = [t.type for t in tokens]
        self.assertIn(TokenType.SUM, types)
        self.assertIn(TokenType.IDENTIFIER, types)

    def test_lod_tokens(self):
        tokens = Lexer("{FIXED [Region]: SUM([Sales])}").tokenize()
        types = [t.type for t in tokens]
        self.assertIn(TokenType.LBRACE, types)
        self.assertIn(TokenType.FIXED, types)
        self.assertIn(TokenType.COLON, types)
        self.assertIn(TokenType.RBRACE, types)

    def test_string_literal(self):
        tokens = Lexer("'High'").tokenize()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "High")

    def test_number_literal(self):
        tokens = Lexer("10000").tokenize()
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertEqual(tokens[0].value, 10000)

    def test_float_literal(self):
        tokens = Lexer("0.2").tokenize()
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertAlmostEqual(tokens[0].value, 0.2)

    def test_comparison_operators(self):
        tokens = Lexer("> >= < <= <> =").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        self.assertEqual(types, [TokenType.GT, TokenType.GTE, TokenType.LT,
                                 TokenType.LTE, TokenType.NEQ, TokenType.EQ])

    def test_table_calc_keywords(self):
        tokens = Lexer("WINDOW_SUM RUNNING_SUM RANK").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        self.assertEqual(types, [TokenType.WINDOW_SUM, TokenType.RUNNING_SUM, TokenType.RANK])


class TestParser(unittest.TestCase):

    def test_simple_sum(self):
        ir = Parser.parse_formula("SUM([Sales])")
        self.assertIsInstance(ir, IRAggregation)
        self.assertEqual(ir.agg_type, AggregationType.SUM)
        self.assertIsInstance(ir.expression, IRFieldReference)
        self.assertEqual(ir.expression.name, "Sales")

    def test_division_becomes_binary_op(self):
        ir = Parser.parse_formula("SUM([Profit]) / SUM([Sales])")
        self.assertIsInstance(ir, IRBinaryOp)
        self.assertEqual(ir.op, BinaryOperator.DIVIDE)

    def test_subtraction(self):
        ir = Parser.parse_formula("SUM([Sales]) - SUM([Cost])")
        self.assertIsInstance(ir, IRBinaryOp)
        self.assertEqual(ir.op, BinaryOperator.SUBTRACT)

    def test_if_then_else(self):
        ir = Parser.parse_formula("IF SUM([Sales]) > 5000 THEN 'High' ELSE 'Low' END")
        self.assertIsInstance(ir, IRConditional)
        self.assertIsInstance(ir.condition, IRComparison)
        self.assertEqual(ir.condition.op, ComparisonOperator.GT)
        self.assertIsInstance(ir.then_expr, IRLiteral)
        self.assertEqual(ir.then_expr.value, "High")

    def test_fixed_lod(self):
        ir = Parser.parse_formula("{FIXED [Region]: SUM([Sales])}")
        self.assertIsInstance(ir, IRLODExpression)
        self.assertEqual(ir.lod_type, LODType.FIXED)
        self.assertEqual(ir.dimensions, ["Region"])
        self.assertIsInstance(ir.expression, IRAggregation)

    def test_window_sum(self):
        ir = Parser.parse_formula("WINDOW_SUM(SUM([Profit]))")
        self.assertIsInstance(ir, IRTableCalculation)
        self.assertEqual(ir.calc_type, TableCalcType.WINDOW_SUM)

    def test_running_sum(self):
        ir = Parser.parse_formula("RUNNING_SUM(SUM([Sales]))")
        self.assertIsInstance(ir, IRTableCalculation)
        self.assertEqual(ir.calc_type, TableCalcType.RUNNING_SUM)

    def test_rank(self):
        ir = Parser.parse_formula("RANK(SUM([Sales]))")
        self.assertIsInstance(ir, IRTableCalculation)
        self.assertEqual(ir.calc_type, TableCalcType.RANK)

    def test_nested_if_with_lod(self):
        formula = "IF {FIXED [Region]: SUM([Sales])} > 10000 THEN AVG([Profit]) / SUM([Sales]) ELSE WINDOW_SUM(SUM([Profit])) END"
        ir = Parser.parse_formula(formula)
        self.assertIsInstance(ir, IRConditional)
        self.assertIsInstance(ir.condition, IRComparison)
        self.assertIsInstance(ir.condition.left, IRLODExpression)
        self.assertIsInstance(ir.then_expr, IRBinaryOp)
        self.assertIsInstance(ir.else_expr, IRTableCalculation)

    def test_field_reference_standalone(self):
        ir = Parser.parse_formula("[Step1]")
        self.assertIsInstance(ir, IRFieldReference)
        self.assertEqual(ir.name, "Step1")

    def test_nested_division_with_field_ref(self):
        ir = Parser.parse_formula("[Step1] / SUM([Sales])")
        self.assertIsInstance(ir, IRBinaryOp)
        self.assertEqual(ir.op, BinaryOperator.DIVIDE)
        self.assertIsInstance(ir.left, IRFieldReference)


if __name__ == "__main__":
    unittest.main()
