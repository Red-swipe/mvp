"""Regression tests for the x-squared / x-cubed base capture.

Defect (reported in raw/context.md:157 as D1, and reproduced live by the Phase D
keypad inventory in commit acc304d):

    typing `100 x 1.05 x^2` produced  100 * 1.0 * (5^2)  =  2500
    instead of                                        110.25

`insertPower()` captured only `cursor.slot.items[cursor.index - 1]`, the single
item immediately left of the cursor. For a multi-item numeric literal such as
`1.05`, or for a parenthesised group such as `(3+4)`, that is a fragment, not
the operand.

These cases are deliberately chosen so they do NOT depend on the blocked
adjacency decision (audit/docs/decision_record_adjacency.md): each uses an
explicit operator or explicit parentheses, so `(2)(3)` legality is irrelevant.

Expected values come from raw/context.md's 46-case battery and are confirmed by
the Python server:

    case 16  (-2)^2        -> 4
    case 22  100 x 1.05^2  -> 110.25

Run: python -m pytest test_power_base_capture.py -q
"""
import os
import pathlib
import sys
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = PROJECT / "frontend.html"

try:
    from browser_support import chromium_executable
    CHROMIUM = chromium_executable()
    HAVE_CHROMIUM = CHROMIUM is not None
except Exception:  # pragma: no cover - browser installation is optional
    CHROMIUM = None
    HAVE_CHROMIUM = False

sys.path.insert(0, str(PROJECT))
import mvp_server  # noqa: E402  the value oracle for the serialisation checks

# (name, keypad keys, intended internal expression, expected value)
CASES = [
    ("square_of_parenthesised_negation",
     ["negate", "left_paren", "2", "right_paren", "square", "equals"],
     "-(((2))^(2))", -4),
    ("square_of_decimal_literal",
     ["1", "0", "0", "multiply", "1", "decimal", "0", "5", "square", "equals"],
     "100*((1.05)^(2))", 110.25),
    ("plain_square_still_works",
     ["2", "square", "equals"],
     "((2)^(2))", 4),
]

def evaluate(expression):
    """Value oracle. The serialisation the keypad builds is an implementation
    detail; what matters is the operand captured is the WHOLE one and the value
    it produces. Every spelling of the same operand must evaluate identically.
    """
    return float(mvp_server.safe_evaluate_expression(expression))


def canonical(s):
    """Canonicalise a display string to a float.

    The default ab/c fraction setting shows 110.25 as the mixed number
    '110 1/4', which is the SAME value. Comparison is numeric, per the battery's
    own rule; display format is a separate check.
    """
    import re
    s = str(s).strip().replace("\u2212", "-").replace("\u00d7", "*") \
        .replace("\u00f7", "/").replace("\u00a0", " ")
    m = re.fullmatch(r"(-?\d+)\s+(\d+)/(\d+)", s)
    if m:
        whole = float(m.group(1))
        frac = float(m.group(2)) / float(m.group(3))
        return whole + (frac if whole >= 0 else -frac)
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)) / float(m.group(2))
    return float(s)


@unittest.skipUnless(HAVE_CHROMIUM, "Playwright-managed Chromium is not installed")
class TestPowerBaseCapture(unittest.TestCase):
    """Drives the real keypad and asserts the constructed expression."""

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

    def _drive(self, keys):
        page = self.page
        page.evaluate(
            "() => { if (typeof hardResetExpr === 'function') hardResetExpr(); "
            "else if (typeof resetExpr === 'function') resetExpr(); }")
        page.wait_for_timeout(60)
        for k in keys[:-1]:                      # everything except `equals`
            loc = page.locator('[data-key="%s"]' % k)
            self.assertGreater(loc.count(), 0, "keypad has no control %r" % k)
            loc.click()
        built = page.evaluate(
            "() => (typeof getExpr === 'function') ? getExpr() : null")
        page.locator('[data-key="equals"]').click()
        page.wait_for_timeout(500)
        state = page.evaluate(
            "() => (typeof appState !== 'undefined') "
            "? {result: appState.result, error: appState.error} : null")
        return built, state

    def test_base_capture_wraps_the_whole_operand(self):
        for name, keys, intended, expected in CASES:
            with self.subTest(case=name):
                built, state = self._drive(keys)
                # Value-based check: whatever spelling the keypad chose, the
                # expression it built must mean "square of the whole operand".
                # A fragment base (e.g. capturing only the last item) evaluates
                # to something else, so this fails on the real defect without
                # pinning one exact serialisation.
                self.assertAlmostEqual(
                    evaluate(built), expected, places=6,
                    msg="keypad built %r which evaluates to %r, expected %r; "
                        "the x^2 key must capture the whole operand, not its "
                        "last item" % (built, evaluate(built), expected))
                self.assertIsNone(state["error"],
                                  "unexpected error %r" % (state["error"],))
                self.assertAlmostEqual(canonical(state["result"]), expected,
                                       places=6)

    def test_decimal_base_is_not_split(self):
        # The precise regression: 1.05 must not become 1.0 with (5^2) beside it.
        built, state = self._drive(CASES[1][1])
        self.assertIn("1.05", built.replace(" ", ""))
        self.assertNotAlmostEqual(canonical(state["result"]), 2500.0, places=3,
                                  msg="the historical 2500 must not come back")
        self.assertAlmostEqual(canonical(state["result"]), 110.25, places=6)


if __name__ == "__main__":
    unittest.main()
