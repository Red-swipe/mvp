import json
import math
import re
import sys
import unittest

from mvp_server import (
    DEFAULT_SETTINGS,
    CalculatorController,
    safe_evaluate_expression,
    _transform_special_functions,
)


class TestSettingsAndSetup(unittest.TestCase):
    def setUp(self):
        self.ctrl = CalculatorController()

    def test_default_settings(self):
        s = self.ctrl.get_settings()
        self.assertEqual(s["inputOutput"], "MathI/MathO")
        self.assertEqual(s["angleUnit"], "Degree")
        self.assertEqual(s["numberFormat"], "Norm")
        self.assertEqual(s["numberFormatPrecision"], 1)
        self.assertFalse(s["engineeringSymbols"])
        self.assertEqual(s["fractionResult"], "ab/c")
        self.assertFalse(s["statisticsFrequency"])
        self.assertTrue(s["autoCalc"])
        self.assertEqual(s["showCell"], "Value")

    def test_settings_validation(self):
        # Valid update
        res = self.ctrl.set_settings({
            "angleUnit": "Radian",
            "numberFormat": "Fix",
            "numberFormatPrecision": 4,
            "statisticsFrequency": True,
            "autoCalc": False,
            "showCell": "Formula",
        })
        self.assertTrue(res["ok"])
        self.assertEqual(res["settings"]["angleUnit"], "Radian")
        self.assertEqual(res["settings"]["numberFormat"], "Fix")
        self.assertEqual(res["settings"]["numberFormatPrecision"], 4)
        self.assertTrue(res["settings"]["statisticsFrequency"])
        self.assertFalse(res["settings"]["autoCalc"])
        self.assertEqual(res["settings"]["showCell"], "Formula")

        # Invalid field value
        res2 = self.ctrl.set_settings({"angleUnit": "InvalidUnit"})
        self.assertFalse(res2["ok"])
        self.assertIn("Invalid angleUnit", res2["error"])

        # Invalid precision for Fix
        res3 = self.ctrl.set_settings({"numberFormatPrecision": 15})
        self.assertFalse(res3["ok"])

    def test_angle_unit_evaluation(self):
        # Degree (default)
        r_deg = safe_evaluate_expression("sin(90)", angle_unit="Degree")
        self.assertAlmostEqual(r_deg, 1.0, places=6)

        # Radian
        r_rad = safe_evaluate_expression("sin(pi/2)", angle_unit="Radian")
        self.assertAlmostEqual(r_rad, 1.0, places=6)

        # Gradian
        r_grad = safe_evaluate_expression("sin(100)", angle_unit="Gradian")
        self.assertAlmostEqual(r_grad, 1.0, places=6)

        # Cosine Degree vs Radian vs Gradian
        self.assertAlmostEqual(safe_evaluate_expression("cos(180)", angle_unit="Degree"), -1.0, places=6)
        self.assertAlmostEqual(safe_evaluate_expression("cos(pi)", angle_unit="Radian"), -1.0, places=6)
        self.assertAlmostEqual(safe_evaluate_expression("cos(200)", angle_unit="Gradian"), -1.0, places=6)

        # Inverse trig in Degree
        r_asin_deg = safe_evaluate_expression("asin(1)", angle_unit="Degree")
        self.assertAlmostEqual(r_asin_deg, 90.0, places=6)

        # Inverse trig in Radian
        r_asin_rad = safe_evaluate_expression("asin(1)", angle_unit="Radian")
        self.assertAlmostEqual(r_asin_rad, math.pi / 2, places=6)

        # Inverse trig in Gradian
        r_asin_grad = safe_evaluate_expression("asin(1)", angle_unit="Gradian")
        self.assertAlmostEqual(r_asin_grad, 100.0, places=6)

    def test_number_formatting(self):
        # Fix 3
        self.ctrl.set_settings({"numberFormat": "Fix", "numberFormatPrecision": 3})
        res = self.ctrl._format_result(1.2)
        self.assertEqual(res, "1.200")

        # Fix 0
        self.ctrl.set_settings({"numberFormat": "Fix", "numberFormatPrecision": 0})
        res0 = self.ctrl._format_result(3.7)
        self.assertEqual(res0, "4")

        # Sci 3
        self.ctrl.set_settings({"numberFormat": "Sci", "numberFormatPrecision": 3})
        res_sci = self.ctrl._format_result(1234.5)
        self.assertEqual(res_sci, "1.23×10^3")

        # Engineering symbols
        self.ctrl.set_settings({"engineeringSymbols": True, "numberFormat": "Norm"})
        res_k = self.ctrl._format_result(1500)
        self.assertEqual(res_k, "1.5 k")

        res_M = self.ctrl._format_result(2500000)
        self.assertEqual(res_M, "2.5 M")

        res_m = self.ctrl._format_result(0.005)
        self.assertEqual(res_m, "5 m")

        res_u = self.ctrl._format_result(0.000004)
        self.assertEqual(res_u, "4 µ")

    def test_norm1_vs_norm2(self):
        # Norm1 (exponential for |x| < 0.01 or |x| >= 1e10)
        self.ctrl.set_settings({"numberFormat": "Norm", "numberFormatPrecision": 1})
        res_norm1_small = self.ctrl._format_result(0.005)
        self.assertIn("10^-3", res_norm1_small)

        # Norm2 (exponential for |x| < 1e-9 or |x| >= 1e10)
        self.ctrl.set_settings({"numberFormat": "Norm", "numberFormatPrecision": 2})
        res_norm2_small = self.ctrl._format_result(0.005)
        self.assertEqual(res_norm2_small, "0.005")

    def test_state_includes_settings(self):
        st = self.ctrl._state()
        self.assertIn("settings", st)
        self.assertEqual(st["settings"]["angleUnit"], "Degree")

    def test_frontend_file_integrity(self):
        with open("frontend.html", "r", encoding="utf-8") as f:
            html = f.read()

        # Check setup DOM elements
        self.assertIn('id="lcdSetup"', html)
        self.assertIn('id="lcdSetupBody"', html)
        self.assertIn('id="setupIndAngle"', html)
        self.assertIn('id="setupIndMath"', html)

        # Check setup CSS rules
        self.assertIn('#lcdSetup', html)
        self.assertIn('.setup-menu-list', html)
        self.assertIn('.setup-menu-item', html)
        self.assertIn('.setup-prompt-box', html)

        # Check localStorage and settings functions
        self.assertIn('casio_fx991ex_settings', html)
        self.assertIn('loadSavedSettings', html)
        self.assertIn('saveSettings', html)
        self.assertIn('syncBackendSettings', html)
        self.assertIn('renderSetupLCD', html)

        # Check Base-N code preservation
        self.assertIn('useAlphaForHex', html)
        self.assertIn('baseNSwitchKeys', html)


if __name__ == "__main__":
    unittest.main()
