"""Evaluator: walks the AST produced by ``parser`` and computes a value."""

import math

from .parser import BinaryOpNode, FunctionNode, NumberNode, UnaryOpNode
from .tokenizer import TokenKind


def evaluate(node, angle_unit="Degree"):
    """Evaluate an AST node, returning a number (int or float).

    Division always uses true float division (``/``), so ``8/2`` yields
    ``4.0``. Division by zero raises ``ZeroDivisionError``.
    Trigonometric functions use the supplied angle unit (Degree by default,
    matching the calculator's default setting).

    Raises ``TypeError`` if ``node`` is not a recognised AST node.
    """
    if isinstance(node, NumberNode):
        return node.number

    if isinstance(node, FunctionNode):
        value = evaluate(node.argument, angle_unit)
        name = node.name.lower()
        if name in ("sin", "cos", "tan"):
            if angle_unit == "Degree":
                value = math.radians(value)
            elif angle_unit == "Gradian":
                value = value * math.pi / 200
            if name == "sin":
                return math.sin(value)
            if name == "cos":
                return math.cos(value)
            cosine = math.cos(value)
            if abs(cosine) <= 1e-12:
                raise ValueError("Math ERROR")
            return math.tan(value)
        if name in ("asin", "acos", "atan"):
            result = {"asin": math.asin, "acos": math.acos, "atan": math.atan}[name](value)
            if angle_unit == "Degree":
                return math.degrees(result)
            if angle_unit == "Gradian":
                return result * 200 / math.pi
            return result
        if name == "sqrt":
            return math.sqrt(value)
        if name == "log":
            return math.log10(value)
        if name == "ln":
            return math.log(value)
        if name == "cbrt":
            return math.copysign(abs(value) ** (1 / 3), value)
        raise ValueError(f"Unknown function: {node.name}")

    if isinstance(node, UnaryOpNode):
        operand = evaluate(node.operand, angle_unit)
        if node.op is TokenKind.MINUS:
            return -operand
        raise TypeError(f"Unsupported unary operator {node.op}")

    if isinstance(node, BinaryOpNode):
        left = evaluate(node.left, angle_unit)
        right = evaluate(node.right, angle_unit)
        if node.op is TokenKind.PLUS:
            return left + right
        if node.op is TokenKind.MINUS:
            return left - right
        if node.op is TokenKind.TIMES:
            return left * right
        if node.op is TokenKind.SLASH:
            return left / right
        if node.op is TokenKind.POWER:
            return left ** right
        raise TypeError(f"Unsupported operator {node.op}")

    raise TypeError(f"Unknown node type: {type(node).__name__}")
