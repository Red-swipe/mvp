import unittest

from mvp_server import CalculatorController


class TestIssue6QuadraticExtremum(unittest.TestCase):
    def test_quadratic_result_includes_vertex_coordinates(self):
        result = CalculatorController().solve_equation(
            "polynomial", [1, -5, 6], 2)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["extremum"], {"x": 2.5, "y": -0.25})
