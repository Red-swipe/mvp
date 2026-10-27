"""BUG-B regression coverage: /api/fraction must never invent exactness.

Defect this locks down: the handler ran
``Fraction(value).limit_denominator(10000)`` on any decimal, and
limit_denominator() always returns SOME nearby rational. So the irrational
``sin(60 deg) = 0.8660254037844386`` came back as ``2521/2911`` and pi came
back as ``355/113`` -- fractions that look exact but have no mathematical
relationship to the value.

The endpoint now accepts a continued-fraction candidate only when either
(a) it is the exact rational form of the decimal supplied (0.25 -> 1/4), or
(b) it is a genuinely simple fraction (denominator <= 100) that reproduces
the value within 1e-9 (1/3, 7/3). Otherwise it returns the decimal text
unchanged. Case (b)'s denominator ceiling matters: with 1e-9 alone,
cos(25 deg) still "matched" 4411/4867.

Every case below runs against the real HTTP handler using the same
ThreadingHTTPServer harness as tests/server/test_s_to_d_file_mode.py. The
trigonometric case goes through the real /api/evaluate pipeline first because
that is how the frontend obtains the number it later sends to /api/fraction.
"""
import json
import math
import re
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

import mvp_server

FRACTION_TEXT = re.compile(r"^-?\d+(?:\s+\d+)?/\d+$")


class FractionApiBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._srv = ThreadingHTTPServer(("127.0.0.1", 0), mvp_server.MvpHandler)
        cls.port = cls._srv.server_address[1]
        threading.Thread(target=cls._srv.serve_forever, daemon=True).start()
        time.sleep(0.4)

    @classmethod
    def tearDownClass(cls):
        cls._srv.shutdown()
        cls._srv.server_close()

    def _post(self, path, payload):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path):
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _evaluate(self, expression):
        response = self._post("/api/evaluate", {"expression": expression})
        self.assertIn("result", response)
        return response["result"]

    def fraction(self, value, mixed=False):
        response = self._post("/api/fraction", {"value": value, "mixed": mixed})
        self.assertTrue(response.get("success"))
        self.assertIn("result", response)
        return response["result"]


class TestIrrationalTrigonometricValue(FractionApiBase):
    """Handover Test 1: sin(60 deg) must not become 2521/2911."""

    def test_sin_60_degree_mode_does_not_claim_an_exact_fraction(self):
        original = self._get("/api/settings")["settings"]["angleUnit"]
        self._post("/api/settings", {"angleUnit": "Degree"})
        try:
            evaluated = self._evaluate("sin(60)")
        finally:
            self._post("/api/settings", {"angleUnit": original})

        self.assertAlmostEqual(float(evaluated), math.sqrt(3) / 2, places=9)
        result = self.fraction(float(evaluated))

        self.assertNotEqual(result, "2521/2911")
        self.assertIsNone(FRACTION_TEXT.match(result))
        self.assertEqual(result, str(float(evaluated)))

    def test_full_precision_sin_60_does_not_claim_an_exact_fraction(self):
        result = self.fraction(0.8660254037844386)

        self.assertNotEqual(result, "2521/2911")
        self.assertIsNone(FRACTION_TEXT.match(result))
        self.assertEqual(result, "0.8660254037844386")


class TestPi(FractionApiBase):
    """Handover Test 2: pi must not be presented as 355/113."""

    def test_pi_through_the_evaluate_pipeline(self):
        evaluated = self._evaluate("pi")
        self.assertAlmostEqual(float(evaluated), math.pi, places=8)

        result = self.fraction(float(evaluated))
        self.assertNotEqual(result, "355/113")
        self.assertIsNone(FRACTION_TEXT.match(result))
        self.assertEqual(result, str(float(evaluated)))

    def test_full_precision_pi(self):
        result = self.fraction(math.pi)

        self.assertNotEqual(result, "355/113")
        self.assertIsNone(FRACTION_TEXT.match(result))
        self.assertEqual(result, "3.141592653589793")


class TestTerminatingDecimal(FractionApiBase):
    """Handover Test 3: 0.25 must still be 1/4."""

    def test_quarter_is_still_an_exact_fraction(self):
        self.assertEqual(self.fraction(0.25), "1/4")

    def test_quarter_through_the_evaluate_pipeline(self):
        self.assertEqual(self._evaluate("0.25"), "0.25")
        self.assertEqual(self.fraction(0.25), "1/4")


class TestDirectlyEnteredFraction(FractionApiBase):
    """Handover Test 4: entered 1/4 must stay exact, not degrade to a guess."""

    def test_one_over_four_is_still_one_over_four(self):
        self.assertEqual(self._evaluate("1/4"), "0.25")
        self.assertEqual(self.fraction(0.25), "1/4")


class TestExistingFractionBehaviour(FractionApiBase):
    """Regression: the fractions the old handler got right must not change."""

    def test_simple_fractions_remain_exact(self):
        cases = {
            1 / 3: "1/3",
            2 / 3: "2/3",
            7 / 3: "7/3",
            5 / 8: "5/8",
            1 / 7: "1/7",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(self.fraction(value), expected)

    def test_values_rounded_by_evaluate_remain_exact(self):
        # /api/evaluate rounds to 10 significant digits, so 7/3 arrives as
        # 2.333333333. The tolerance has to keep accepting that.
        self.assertEqual(self._evaluate("7/3"), "2.333333333")
        self.assertEqual(self.fraction(2.333333333), "7/3")
        self.assertEqual(self._evaluate("1/3"), "0.3333333333")
        self.assertEqual(self.fraction(0.3333333333), "1/3")

    def test_integer_and_mixed_forms_are_unchanged(self):
        self.assertEqual(self.fraction(42), "42")
        self.assertEqual(self.fraction(7 / 3, mixed=True), "2 1/3")

    def test_other_irrationals_are_not_given_false_fractions(self):
        cases = {
            1.414213562: "8119/5741",          # sqrt(2), 10 significant digits
            2.618033988749895: "17711/6765",    # golden ratio squared
            0.9063077870366499: "4411/4867",    # cos(25 deg)
            3.1780538303479458: "1535/483",     # ln(24)
        }
        for value, old_fraction in cases.items():
            with self.subTest(value=value):
                result = self.fraction(value)
                self.assertNotEqual(result, old_fraction)
                self.assertIsNone(FRACTION_TEXT.match(result))

    def test_terminating_decimals_keep_their_exact_reduced_form(self):
        # These are exactly representable decimals, so their fraction form is
        # exact even when the reduced denominator is larger than the
        # simple-fraction ceiling.
        self.assertEqual(self.fraction(0.1234), "617/5000")
        self.assertEqual(self.fraction(0.0078125), "1/128")
        self.assertEqual(self.fraction(0.001), "1/1000")

    def test_repeating_fraction_with_a_large_denominator_stays_decimal(self):
        # 1/101 arrives from /api/evaluate as 0.009900990099, which is a
        # rounded decimal; claiming 1/101 would be a guess, not exactness.
        self.assertEqual(self.fraction(0.009900990099), "0.009900990099")


if __name__ == "__main__":
    unittest.main()
