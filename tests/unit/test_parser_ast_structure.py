"""AST structure and evaluation regressions for unary negation."""

import unittest

from engine.evaluator import evaluate
from engine.parser import UnaryOpNode, parse
from engine.tokenizer import tokenize


class TestUnaryMinusAst(unittest.TestCase):
    def test_negative_literal_uses_unary_node(self):
        node = parse(tokenize("-5"))
        self.assertIsInstance(node, UnaryOpNode)
        self.assertEqual(evaluate(node), -5)

    def test_negative_parenthesized_expression_uses_unary_node(self):
        node = parse(tokenize("-(2+3)"))
        self.assertIsInstance(node, UnaryOpNode)
        self.assertEqual(evaluate(node), -5)

    def test_unary_minus_precedence_is_preserved(self):
        cases = {
            "-3**2": -9,
            "(-3)**2": 9,
            "--5": 5,
            "+-5": -5,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(evaluate(parse(tokenize(expression))), expected)


if __name__ == "__main__":
    unittest.main()
