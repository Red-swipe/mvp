"""Parser: converts a list of tokens into an AST using recursive descent."""

from dataclasses import dataclass

from .tokenizer import Token, TokenKind, TokenizerError


class ParseError(ValueError):
    """Raised when a token sequence is not a valid expression."""


@dataclass
class NumberNode:
    number: object


@dataclass
class BinaryOpNode:
    left: "Node"
    op: TokenKind
    right: "Node"


Node = NumberNode | BinaryOpNode


class _Parser:
    def __init__(self, tokens):
        self._tokens = tokens
        self._pos = 0

    def _peek(self):
        if self._pos >= len(self._tokens):
            return None
        return self._tokens[self._pos]

    def _advance(self):
        token = self._peek()
        if token is None:
            raise ParseError("Unexpected end of expression")
        self._pos += 1
        return token

    def _expect(self, kind):
        token = self._peek()
        if token is None or token.kind != kind:
            raise ParseError(f"Expected {kind.name} but found {token}")
        self._pos += 1
        return token

    def parse(self):
        if not self._tokens:
            raise ParseError("Empty expression")
        node = self._expression()
        if self._peek() is not None:
            raise ParseError(f"Unexpected trailing token {self._peek()}")
        return node

    def _expression(self):
        node = self._term()
        while True:
            token = self._peek()
            if token is not None and token.kind in (TokenKind.PLUS, TokenKind.MINUS):
                self._advance()
                right = self._term()
                node = BinaryOpNode(node, token.kind, right)
            else:
                return node

    def _term(self):
        node = self._factor()
        while True:
            token = self._peek()
            if token is not None and token.kind in (TokenKind.TIMES, TokenKind.SLASH):
                self._advance()
                right = self._factor()
                node = BinaryOpNode(node, token.kind, right)
            else:
                return node

    def _factor(self):
        return self._power()

    def _power(self):
        # Casio fx-991EX priority: powers bind tighter than a leading
        # negative sign, so -2**2 == -(2**2) == -4 (while (-2)**2 == 4).
        token = self._peek()
        if token is not None and token.kind == TokenKind.MINUS:
            self._advance()
            operand = self._power()
            if isinstance(operand, NumberNode):
                return NumberNode(-operand.number)
            return BinaryOpNode(NumberNode(0), TokenKind.MINUS, operand)
        node = self._unary()
        token = self._peek()
        if token is not None and token.kind == TokenKind.POWER:
            self._advance()
            # Right-associative: 2**3**2 == 2**(3**2)
            right = self._power()
            node = BinaryOpNode(node, token.kind, right)
        return node

    def _unary(self):
        token = self._peek()
        if token is not None and token.kind == TokenKind.PLUS:
            self._advance()
            return self._unary()
        if token is not None and token.kind == TokenKind.MINUS:
            self._advance()
            operand = self._unary()
            if isinstance(operand, NumberNode):
                return NumberNode(-operand.number)
            return BinaryOpNode(NumberNode(0), TokenKind.MINUS, operand)
        return self._primary()

    def _primary(self):
        token = self._peek()
        if token is None:
            raise ParseError("Unexpected end of expression")
        if token.kind == TokenKind.NUMBER:
            self._advance()
            return NumberNode(token.value)
        if token.kind == TokenKind.LPAREN:
            self._advance()
            node = self._expression()
            self._expect(TokenKind.RPAREN)
            return node
        raise ParseError(f"Unexpected token {token}")


def parse(tokens):
    """Build an AST from ``tokens``.

    Raises ParseError on invalid or incomplete expressions.
    """
    return _Parser(tokens).parse()
