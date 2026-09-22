"""Tokenizer: converts a raw expression string into a list of tokens."""

from dataclasses import dataclass
from enum import Enum


class TokenKind(Enum):
    NUMBER = "NUMBER"
    PLUS = "PLUS"
    MINUS = "MINUS"
    TIMES = "TIMES"
    SLASH = "SLASH"
    POWER = "POWER"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"


@dataclass
class Token:
    kind: TokenKind
    value: object = None
    position: int = 0


class TokenizerError(ValueError):
    """Raised when the input string cannot be tokenized."""


_SINGLE_CHAR_TOKENS = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.TIMES,
    "/": TokenKind.SLASH,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
}


def tokenize(text):
    """Tokenize ``text`` into a list of Tokens, ignoring whitespace.

    Raises TokenizerError on any character that is not a digit,
    decimal point, operator, parenthesis, or whitespace.
    """
    tokens = []
    i = 0
    length = len(text)

    while i < length:
        char = text[i]

        if char.isspace():
            i += 1
            continue

        # Power operator '**' (must be checked before single '*')
        if char == '*' and i + 1 < length and text[i + 1] == '*':
            tokens.append(Token(TokenKind.POWER, '**', i))
            i += 2
            continue

        if char.isdigit() or char == ".":
            start = i
            while i < length and (text[i].isdigit() or text[i] == "."):
                i += 1
            raw = text[start:i]
            try:
                value = float(raw) if "." in raw else int(raw)
            except ValueError:
                raise TokenizerError(
                    f"Invalid number '{raw}' at position {start}"
                )
            tokens.append(Token(TokenKind.NUMBER, value, start))
            continue

        if char in _SINGLE_CHAR_TOKENS:
            tokens.append(Token(_SINGLE_CHAR_TOKENS[char], char, i))
            i += 1
            continue

        raise TokenizerError(f"Unexpected character '{char}' at position {i}")

    return tokens
