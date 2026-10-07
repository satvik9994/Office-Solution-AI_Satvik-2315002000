"""Token definitions for Tableau formula lexer."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # Literals & Identifiers
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()  # [Field] or function name

    # Keywords
    IF = auto()
    THEN = auto()
    ELSE = auto()
    ELSEIF = auto()
    END = auto()
    FIXED = auto()
    INCLUDE = auto()
    EXCLUDE = auto()

    # Known Functions
    SUM = auto()
    AVG = auto()
    MIN = auto()
    MAX = auto()
    COUNT = auto()
    COUNTD = auto()
    WINDOW_SUM = auto()
    RUNNING_SUM = auto()
    RANK = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()
    EQ = auto()
    NEQ = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    COLON = auto()
    COMMA = auto()

    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: Any
    pos: int
