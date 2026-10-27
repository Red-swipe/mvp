"""Exact calculator trig values for standard degree-mode angles."""

import unittest

from mvp_server import safe_evaluate_expression


def trig(expression, angle_unit="Degree"):
    return safe_evaluate_expression(expression, angle_unit=angle_unit)


class TestTrigExactValues(unittest.TestCase):
    def test_required_special_angles_are_exact(self):
        self.assertEqual(trig("sin(30)"), 0.5)
        self.assertEqual(trig("cos(60)"), 0.5)
        self.assertEqual(trig("tan(45)"), 1.0)

    def test_reflections_and_multiples_are_exact(self):
        self.assertEqual(trig("sin(150)"), 0.5)
        self.assertEqual(trig("sin(210)"), -0.5)
        self.assertEqual(trig("cos(120)"), -0.5)
        self.assertEqual(trig("tan(225)"), 1.0)
        self.assertEqual(trig("sin(-30)"), -0.5)

    def test_existing_axis_angle_safeguards_remain_exact(self):
        for angle in (0, 180, 360):
            with self.subTest(function="sin", angle=angle):
                self.assertEqual(trig(f"sin({angle})"), 0.0)
            with self.subTest(function="tan", angle=angle):
                self.assertEqual(trig(f"tan({angle})"), 0.0)
        self.assertEqual(trig("cos(90)"), 0.0)
        self.assertEqual(trig("cos(270)"), 0.0)

    def test_special_degree_lookup_does_not_affect_radians(self):
        self.assertNotEqual(trig("sin(30)", "Radian"), 0.5)


if __name__ == "__main__":
    unittest.main()
