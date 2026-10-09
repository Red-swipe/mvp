import unittest

from mvp_server import CONTROLLER


def roots(result):
    assert result["ok"] is True, result
    return [(float(item["real"]), float(item["imag"])) for item in result["result"]]


class QuadraticWorkflowTests(unittest.TestCase):
    def solve(self, coefficients):
        return roots(CONTROLLER.solve_equation("polynomial", coefficients, 2))

    def test_two_real_roots(self):
        self.assertEqual(self.solve([1, 5, 6]), [(-3.0, 0.0), (-2.0, 0.0)])

    def test_two_positive_roots(self):
        self.assertEqual(self.solve([1, -5, 6]), [(3.0, 0.0), (2.0, 0.0)])

    def test_repeated_root(self):
        self.assertEqual(self.solve([1, -2, 1]), [(1.0, 0.0), (1.0, -0.0)])

    def test_complex_roots(self):
        actual = self.solve([1, 0, 1])
        self.assertAlmostEqual(actual[0][0], 0.0)
        self.assertAlmostEqual(abs(actual[0][1]), 1.0)
        self.assertAlmostEqual(actual[1][0], 0.0)
        self.assertAlmostEqual(abs(actual[1][1]), 1.0)

    def test_zero_constant_repeated_zero_root(self):
        self.assertEqual(self.solve([1, 0, 0]), [(0.0, 0.0), (0.0, 0.0)])

    def test_linear_degenerate_input_remains_an_error(self):
        result = CONTROLLER.solve_equation("polynomial", [0, 2, 4], 2)
        self.assertFalse(result["ok"])
        self.assertIn("Math ERROR", result["error"])

    def test_frontend_uses_the_api_root_contract(self):
        with open("frontend.html", encoding="utf-8") as handle:
            frontend = handle.read()
        self.assertIn("formatEquationRoot", frontend)
        self.assertIn("root.real", frontend)
        # Item 13: this used to assert the literal template
        # `x${['₁','₂','₃','₄']`, i.e. that every equation result was labelled
        # with a polynomial root index. That is exactly the defect Item 13 fixed:
        # a solved simultaneous system was reported as x_1, x_2, ... while its
        # input grid showed x, y, z, w. The contract is now that the label is
        # chosen by the equation type, and a polynomial still keeps its indexed
        # subscript (Item 6 depends on that being a real KaTeX msub).
        self.assertIn("function equationVariableLabel(", frontend)
        self.assertIn("eq.selectedType === 'simultaneous'", frontend)
        self.assertIn("'x_{' + (index + 1) + '}'", frontend)
        self.assertNotIn("x${['\u2081','\u2082','\u2083','\u2084']", frontend)
        self.assertIn("rawKey === 'negate' || rawKey === 'minus'", frontend)
        # Item 13 also removed the equation path's leftover tracing. The
        # KEY-TRACE-DROP trace below belongs to backendKey() and is unrelated, so
        # it is deliberately left alone and still asserted here.
        self.assertNotIn("EQUATION-TRACE", frontend)
        self.assertIn("KEY-TRACE-DROP", frontend)


if __name__ == "__main__":
    unittest.main()
