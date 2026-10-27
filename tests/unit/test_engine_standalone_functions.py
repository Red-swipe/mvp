"""Standalone tokenizer/parser/evaluator support for calculator functions."""

import unittest

from engine.evaluator import evaluate
from engine.parser import FunctionNode, parse
from engine.tokenizer import TokenKind, tokenize
from mvp_server import safe_evaluate_expression


def standalone(expression, angle_unit="Degree"):
    return evaluate(parse(tokenize(expression)), angle_unit=angle_unit)


class TestStandaloneFunctions(unittest.TestCase):
    def test_tokenizer_recognizes_function_names(self):
        tokens = tokenize("sin(30)")
        self.assertEqual(tokens[0].kind, TokenKind.IDENTIFIER)
        self.assertEqual(tokens[0].value, "sin")

    def test_parser_builds_function_node(self):
        node = parse(tokenize("sin(30)"))
        self.assertIsInstance(node, FunctionNode)
        self.assertEqual(node.name, "sin")

    def test_required_functions_evaluate(self):
        cases = {
            "sin(30)": 0.5,
            "cos(60)": 0.5,
            "tan(45)": 1.0,
            "sqrt(144)": 12.0,
            "log(100)": 2.0,
            "ln(2.718281828459045)": 1.0,
            "cbrt(-27)": -3.0,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertAlmostEqual(standalone(expression), expected, places=12)

    def test_trig_modes_match_backend(self):
        cases = (
            ("Degree", "sin(30)"),
            ("Radian", "sin(0.5235987755982988)"),
            ("Gradian", "sin(33.333333333333336)"),
        )
        for angle_unit, expression in cases:
            with self.subTest(angle_unit=angle_unit):
                backend = safe_evaluate_expression(expression, angle_unit=angle_unit)
                self.assertAlmostEqual(
                    standalone(expression, angle_unit), float(backend), places=12)

    def test_results_match_backend_for_required_functions(self):
        expressions = (
            "sin(30)", "sqrt(9)", "log(100)", "ln(2.718281828459045)",
            "cos(60)", "tan(45)", "cbrt(-27)",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                backend = safe_evaluate_expression(expression, angle_unit="Degree")
                self.assertAlmostEqual(standalone(expression), float(backend), places=12)


if __name__ == "__main__":
    unittest.main()
