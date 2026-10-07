"""Recursive-descent parser for Tableau calculation expressions into IR."""

from typing import List, Optional
from parser.tokens import Token, TokenType
from parser.lexer import Lexer
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


class ParserError(Exception):
    """Raised when formula syntax does not match expected grammar."""
    pass


class Parser:
    """Parses a stream of Tokens into a semantic Intermediate Representation (IR) tree."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    @classmethod
    def parse_formula(cls, formula: str) -> IRNode:
        """Convenience factory to tokenize and parse a formula string directly."""
        lexer = Lexer(formula)
        tokens = lexer.tokenize()
        parser = cls(tokens)
        return parser.parse()

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # EOF

    def advance(self) -> Token:
        tok = self.peek()
        self.pos += 1
        return tok

    def match(self, *expected_types: TokenType) -> bool:
        if self.peek().type in expected_types:
            self.advance()
            return True
        return False

    def expect(self, expected_type: TokenType, error_msg: Optional[str] = None) -> Token:
        tok = self.peek()
        if tok.type != expected_type:
            msg = error_msg or f"Expected token {expected_type}, but got {tok.type} ('{tok.value}') at pos {tok.pos}"
            raise ParserError(msg)
        return self.advance()

    def parse(self) -> IRNode:
        node = self.parse_expression()
        if self.peek().type != TokenType.EOF:
            raise ParserError(f"Unexpected trailing token: {self.peek().type} ('{self.peek().value}')")
        return node

    def parse_expression(self) -> IRNode:
        # Check if starting an IF ... THEN ... ELSE ... END block
        if self.peek().type == TokenType.IF:
            return self.parse_conditional()
        return self.parse_comparison()

    def parse_conditional(self, is_sub_clause: bool = False) -> IRConditional:
        """Parses IF <cond> THEN <then> [ELSEIF <cond2> THEN <then2> ...] [ELSE <else>] END"""
        if is_sub_clause:
            self.expect(TokenType.ELSEIF)
        else:
            self.expect(TokenType.IF)

        condition = self.parse_comparison()
        self.expect(TokenType.THEN)
        then_branch = self.parse_expression()

        if self.peek().type == TokenType.ELSEIF:
            else_branch = self.parse_conditional(is_sub_clause=True)
        elif self.match(TokenType.ELSE):
            else_branch = self.parse_expression()
            self.expect(TokenType.END)
        else:
            self.expect(TokenType.END)
            else_branch = IRLiteral(None, "null")

        return IRConditional(condition=condition, then_expr=then_branch, else_expr=else_branch)

    def parse_comparison(self) -> IRNode:
        left = self.parse_additive()

        comp_ops = {
            TokenType.GT: ComparisonOperator.GT,
            TokenType.LT: ComparisonOperator.LT,
            TokenType.GTE: ComparisonOperator.GTE,
            TokenType.LTE: ComparisonOperator.LTE,
            TokenType.EQ: ComparisonOperator.EQ,
            TokenType.NEQ: ComparisonOperator.NEQ,
        }

        while self.peek().type in comp_ops:
            op_token = self.advance()
            op = comp_ops[op_token.type]
            right = self.parse_additive()
            left = IRComparison(op=op, left=left, right=right)

        return left

    def parse_additive(self) -> IRNode:
        left = self.parse_multiplicative()

        while self.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.advance()
            op = BinaryOperator.ADD if op_token.type == TokenType.PLUS else BinaryOperator.SUBTRACT
            right = self.parse_multiplicative()
            left = IRBinaryOp(op=op, left=left, right=right)

        return left

    def parse_multiplicative(self) -> IRNode:
        left = self.parse_unary()

        while self.peek().type in (TokenType.MULTIPLY, TokenType.DIVIDE):
            op_token = self.advance()
            op = BinaryOperator.MULTIPLY if op_token.type == TokenType.MULTIPLY else BinaryOperator.DIVIDE
            right = self.parse_unary()
            left = IRBinaryOp(op=op, left=left, right=right)

        return left

    def parse_unary(self) -> IRNode:
        if self.match(TokenType.MINUS):
            operand = self.parse_unary()
            return IRBinaryOp(op=BinaryOperator.MULTIPLY, left=IRLiteral(-1, "number"), right=operand)
        return self.parse_primary()

    def parse_primary(self) -> IRNode:
        tok = self.peek()

        # 1. Parenthesized expression: ( expr )
        if self.match(TokenType.LPAREN):
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN, "Unclosed parenthesis")
            return expr

        # 2. Level of Detail: { FIXED [Dim]: expr }
        if self.match(TokenType.LBRACE):
            lod_tok = self.advance()
            lod_type_map = {
                TokenType.FIXED: LODType.FIXED,
                TokenType.INCLUDE: LODType.INCLUDE,
                TokenType.EXCLUDE: LODType.EXCLUDE,
            }
            if lod_tok.type not in lod_type_map:
                raise ParserError(f"Expected FIXED, INCLUDE, or EXCLUDE after '{{', got {lod_tok.type}")
            lod_type = lod_type_map[lod_tok.type]

            dimensions: List[str] = []
            # Parse dimension list until ':'
            while self.peek().type != TokenType.COLON and self.peek().type != TokenType.EOF:
                if self.peek().type == TokenType.IDENTIFIER:
                    dimensions.append(self.advance().value)
                elif self.peek().type == TokenType.COMMA:
                    self.advance()
                else:
                    raise ParserError(f"Unexpected token in LOD dimension list: {self.peek().type}")

            self.expect(TokenType.COLON, "Expected ':' separating dimensions from expression in LOD")
            inner_expr = self.parse_expression()
            self.expect(TokenType.RBRACE, "Unclosed '}' in LOD expression")
            return IRLODExpression(lod_type=lod_type, dimensions=dimensions, expression=inner_expr)

        # 3. Known Aggregations
        agg_types = {
            TokenType.SUM: AggregationType.SUM,
            TokenType.AVG: AggregationType.AVG,
            TokenType.MIN: AggregationType.MIN,
            TokenType.MAX: AggregationType.MAX,
            TokenType.COUNT: AggregationType.COUNT,
            TokenType.COUNTD: AggregationType.COUNTD,
        }
        if tok.type in agg_types:
            agg_type = agg_types[tok.type]
            self.advance()
            self.expect(TokenType.LPAREN)
            arg = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return IRAggregation(agg_type=agg_type, expression=arg)

        # 4. Known Table Calculations
        table_calc_types = {
            TokenType.WINDOW_SUM: TableCalcType.WINDOW_SUM,
            TokenType.RUNNING_SUM: TableCalcType.RUNNING_SUM,
            TokenType.RANK: TableCalcType.RANK,
        }
        if tok.type in table_calc_types:
            calc_type = table_calc_types[tok.type]
            self.advance()
            self.expect(TokenType.LPAREN)
            arg = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return IRTableCalculation(calc_type=calc_type, inner_expression=arg)

        # 5. Literals
        if self.match(TokenType.NUMBER):
            return IRLiteral(value=tok.value, data_type="number")
        if self.match(TokenType.STRING):
            return IRLiteral(value=tok.value, data_type="string")

        # 6. Identifiers (Field references or general function calls)
        if tok.type == TokenType.IDENTIFIER:
            ident_name = tok.value
            self.advance()
            # If followed by '(', it is a function call
            if self.match(TokenType.LPAREN):
                args: List[IRNode] = []
                if self.peek().type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        args.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
                # Check if it was an aliased function
                ident_lower = ident_name.lower()
                if ident_lower in ("sum", "avg", "min", "max", "count", "countd"):
                    return IRAggregation(AggregationType[ident_lower.upper()], args[0])
                return IRUnsupportedFunction(function_name=ident_name, arguments=args)
            else:
                return IRFieldReference(name=ident_name)

        raise ParserError(f"Unexpected token in expression: {tok.type} ('{tok.value}') at pos {tok.pos}")
