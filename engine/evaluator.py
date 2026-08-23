"""Evaluator: walks the AST produced by ``parser`` and computes a value."""

from .parser import BinaryOpNode, NumberNode
from .tokenizer import TokenKind


def evaluate(node):
    """Evaluate an AST node, returning a number (int or float).

    Division always uses true float division (``/``), so ``8/2`` yields
    ``4.0``. Division by zero raises ``ZeroDivisionError``.

    Raises ``TypeError`` if ``node`` is not a recognised AST node.
    """
    if isinstance(node, NumberNode):
        return node.number

    if isinstance(node, BinaryOpNode):
        left = evaluate(node.left)
        right = evaluate(node.right)
        if node.op is TokenKind.PLUS:
            return left + right
        if node.op is TokenKind.MINUS:
            return left - right
        if node.op is TokenKind.TIMES:
            return left * right
        if node.op is TokenKind.SLASH:
            return left / right
        raise TypeError(f"Unsupported operator {node.op}")

    raise TypeError(f"Unknown node type: {type(node).__name__}")
