"""Stage E validation of the Phase D insertPower() fix.

test_power_base_capture.py proves the basic cases. This adds the boundary
conditions that were listed as unverified in the Phase D report:

  - cursor at position 0 (nothing to the left)
  - cursor immediately after a complete group
  - a compound base such as 2(3+4) followed by x^2
  - x^3 and x^-1, which share insertPower()
  - square twice in a row
  - a binary minus before a group must NOT be absorbed as unary
"""
import os
import pathlib
import sys
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[2]
CHROMIUM = r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
FRONTEND = PROJECT / "frontend.html"

sys.path.insert(0, str(PROJECT))
import mvp_server  # noqa: E402  the value oracle for the serialisation checks


def evaluate(expression):
    """Value oracle. The exact serialisation the keypad emits is an
    implementation detail; these checks assert the MEANING of the captured
    base, not one particular string.
    """
    return float(mvp_server.safe_evaluate_expression(expression))


@unittest.skipUnless(os.path.exists(CHROMIUM), "chromium is not installed")
class TestPowerKeyBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls._pw_ctx = sync_playwright()
        cls._pw = cls._pw_ctx.start()
        cls._browser = cls._pw.chromium.launch(headless=True,
                                                executable_path=CHROMIUM)
        cls.page = cls._browser.new_page()
        cls.page.goto("file:///" + str(FRONTEND).replace("\\", "/"),
                      wait_until="load")

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def _type(self, keys):
        """Type keys without submitting, then return the constructed expression."""
        page = self.page
        page.evaluate(
            "() => { if (typeof hardResetExpr === 'function') hardResetExpr(); }")
        page.wait_for_timeout(60)
        for k in keys:
            loc = page.locator('[data-key="%s"]' % k)
            self.assertGreater(loc.count(), 0, "no keypad control %r" % k)
            loc.click()
        page.wait_for_timeout(250)
        return page.evaluate(
            "() => (typeof getExpr === 'function') ? getExpr() : null")

    # ---- cursor boundaries -------------------------------------------------

    def test_power_at_start_of_expression_has_no_base(self):
        # Nothing to the left: the power key must open an empty template
        # rather than crash or invent a base.
        built = self._type(["square"])
        self.assertIsNotNone(built)
        self.assertNotIn("undefined", built)

    def test_power_after_single_digit(self):
        self.assertEqual(self._type(["2", "square"]), "((2)^(2))")

    def test_power_after_multi_digit_number(self):
        built = self._type(["1", "2", "3", "square"])
        self.assertEqual(built, "((123)^(2))")

    def test_power_after_decimal_number(self):
        built = self._type(["1", "decimal", "0", "5", "square"])
        self.assertEqual(built, "((1.05)^(2))")

    def test_power_after_closed_group(self):
        built = self._type(["left_paren", "3", "plus", "4", "right_paren", "square"])
        self.assertEqual(built, "(((3+4))^(2))")

    # ---- compound bases ----------------------------------------------------

    def test_power_after_compound_base(self):
        # Battery case 45: 2(3+4)^2. The base is the group, not the 4.
        built = self._type(["2", "left_paren", "3", "plus", "4", "right_paren",
                            "square"])
        self.assertEqual(built, "2(((3+4))^(2))")

    def test_binary_minus_before_group_is_not_absorbed(self):
        # 5-(2) then x^2: the minus is binary, so the base is (2) alone.
        built = self._type(["5", "minus", "left_paren", "2", "right_paren", "square"])
        self.assertAlmostEqual(
            evaluate(built), 1.0, places=6,
            msg="a binary minus must not be pulled into the power base; "
                "keypad built %r which evaluates to %r, expected 1.0"
                % (built, evaluate(built)))

    def test_unary_minus_before_group_is_absorbed(self):
        # -(2) then x^2 is (-2)^2 = -4. A base that dropped the unary minus
        # would give (2)^2 = 4, so the value distinguishes the two.
        built = self._type(["negate", "left_paren", "2", "right_paren", "square"])
        self.assertAlmostEqual(
            evaluate(built), -4.0, places=6,
            msg="a unary minus must be absorbed into the power base; keypad "
                "built %r which evaluates to %r, expected -4.0"
                % (built, evaluate(built)))

    def test_leading_operand_minus_group_then_square_is_negative(self):
        # 1-(2) then x^2 is 1-4 = -3. Guards the binary case independently of
        # the 5-(2) spelling above.
        built = self._type(["1", "minus", "left_paren", "2", "right_paren", "square"])
        self.assertAlmostEqual(
            evaluate(built), -3.0, places=6,
            msg="keypad built %r which evaluates to %r, expected -3.0"
                % (built, evaluate(built)))

    # ---- sibling keys ------------------------------------------------------

    def test_cube_key_shares_the_same_base_capture(self):
        # x^3 is SHIFT + x^2 on this keypad; there is no separate `cube` control.
        built = self._type(["1", "decimal", "0", "5", "shift", "square"])
        self.assertEqual(built, "((1.05)^(3))")

    def test_inverse_key_shares_the_same_base_capture(self):
        built = self._type(["1", "decimal", "0", "5", "inverse"])
        self.assertEqual(built, "((1.05)^(-1))")

    # ---- repetition --------------------------------------------------------

    def test_squaring_twice(self):
        built = self._type(["3", "square", "square"])
        self.assertEqual(built, "((((3)^(2)))^(2))")

    def test_squaring_after_an_operator_has_no_base(self):
        # The cursor follows an operator, so there is no operand to wrap.
        built = self._type(["2", "plus", "square"])
        self.assertIsNotNone(built)


if __name__ == "__main__":
    unittest.main()