"""Lexer for tokenizing Tableau calculation formulas."""

import re
from typing import List
from parser.tokens import Token, TokenType


class LexerError(Exception):
    """Raised when an unrecognized character or token is encountered."""
    pass


class Lexer:
    """Converts a raw Tableau formula string into a stream of Tokens."""

    KEYWORDS = {
        "if": TokenType.IF,
        "then": TokenType.THEN,
        "else": TokenType.ELSE,
        "elseif": TokenType.ELSEIF,
        "end": TokenType.END,
        "fixed": TokenType.FIXED,
        "include": TokenType.INCLUDE,
        "exclude": TokenType.EXCLUDE,
        "sum": TokenType.SUM,
        "avg": TokenType.AVG,
        "min": TokenType.MIN,
        "max": TokenType.MAX,
        "count": TokenType.COUNT,
        "countd": TokenType.COUNTD,
        "window_sum": TokenType.WINDOW_SUM,
        "running_sum": TokenType.RUNNING_SUM,
        "rank": TokenType.RANK,
    }

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def error(self, msg: str):
        raise LexerError(f"Lexer error at pos {self.pos}: {msg} in formula: '{self.text}'")

    def peek(self) -> str:
        if self.pos < self.length:
            return self.text[self.pos]
        return ""

    def advance(self) -> str:
        ch = self.peek()
        self.pos += 1
        return ch

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < self.length:
            ch = self.peek()

            # 1. Skip whitespace
            if ch.isspace():
                self.advance()
                continue

            start_pos = self.pos

            # 2. Bracketed identifier: [Sales] or [Step 1]
            if ch == "[":
                self.advance()
                ident_chars = []
                while self.pos < self.length and self.peek() != "]":
                    ident_chars.append(self.advance())
                if self.pos >= self.length:
                    self.error("Unclosed bracketed identifier")
                self.advance()  # consume ']'
                tokens.append(Token(TokenType.IDENTIFIER, "".join(ident_chars).strip(), start_pos))
                continue

            # 3. String literal: 'High' or "High"
            if ch in ("'", '"'):
                quote_char = self.advance()
                str_chars = []
                while self.pos < self.length and self.peek() != quote_char:
                    str_chars.append(self.advance())
                if self.pos >= self.length:
                    self.error(f"Unterminated string literal starting with {quote_char}")
                self.advance()  # consume quote
                tokens.append(Token(TokenType.STRING, "".join(str_chars), start_pos))
                continue

            # 4. Numbers: 10000, 0.2
            if ch.isdigit():
                num_chars = []
                has_dot = False
                while self.pos < self.length and (self.peek().isdigit() or self.peek() == "."):
                    if self.peek() == ".":
                        if has_dot:
                            break
                        has_dot = True
                    num_chars.append(self.advance())
                val_str = "".join(num_chars)
                val = float(val_str) if has_dot else int(val_str)
                tokens.append(Token(TokenType.NUMBER, val, start_pos))
                continue

            # 5. Multi-char comparisons: >=, <=, <>, !=, ==
            if ch == ">" and self.pos + 1 < self.length and self.text[self.pos + 1] == "=":
                self.pos += 2
                tokens.append(Token(TokenType.GTE, ">=", start_pos))
                continue
            if ch == "<" and self.pos + 1 < self.length and self.text[self.pos + 1] == "=":
                self.pos += 2
                tokens.append(Token(TokenType.LTE, "<=", start_pos))
                continue
            if ch == "<" and self.pos + 1 < self.length and self.text[self.pos + 1] == ">":
                self.pos += 2
                tokens.append(Token(TokenType.NEQ, "<>", start_pos))
                continue
            if ch == "!" and self.pos + 1 < self.length and self.text[self.pos + 1] == "=":
                self.pos += 2
                tokens.append(Token(TokenType.NEQ, "!=", start_pos))
                continue
            if ch == "=" and self.pos + 1 < self.length and self.text[self.pos + 1] == "=":
                self.pos += 2
                tokens.append(Token(TokenType.EQ, "==", start_pos))
                continue

            # 6. Single-char operators and punctuation
            single_ops = {
                ">": TokenType.GT,
                "<": TokenType.LT,
                "=": TokenType.EQ,
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "*": TokenType.MULTIPLY,
                "/": TokenType.DIVIDE,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                ":": TokenType.COLON,
                ",": TokenType.COMMA,
            }
            if ch in single_ops:
                self.advance()
                tokens.append(Token(single_ops[ch], ch, start_pos))
                continue

            # 7. Words / Identifiers / Keywords
            if ch.isalpha() or ch == "_":
                word_chars = []
                while self.pos < self.length and (self.peek().isalnum() or self.peek() == "_"):
                    word_chars.append(self.advance())
                word = "".join(word_chars)
                word_lower = word.lower()
                token_type = self.KEYWORDS.get(word_lower, TokenType.IDENTIFIER)
                tokens.append(Token(token_type, word, start_pos))
                continue

            self.error(f"Unexpected character: '{ch}'")

        tokens.append(Token(TokenType.EOF, "", self.pos))
        return tokens
