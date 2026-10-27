"""BUG-E regression: AC from any quadratic result page starts fresh arithmetic."""
import threading
import unittest
from http.server import ThreadingHTTPServer

import mvp_server

try:
    from playwright.sync_api import sync_playwright

    _probe = sync_playwright().start()
    _browser = _probe.chromium.launch(channel="chrome")
    HAVE_BROWSER = True
    _browser.close()
    _probe.stop()
except Exception:  # pragma: no cover - environment dependent
    HAVE_BROWSER = False


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestQuadraticACReset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def setUp(self):
        mvp_server.CONTROLLER = mvp_server.CalculatorController()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), mvp_server.MvpHandler)
        self._port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.page = self._browser.new_page()
        self.page.set_default_timeout(10000)
        self.page.goto(f"http://127.0.0.1:{self._port}/", wait_until="domcontentloaded")
        self.page.wait_for_timeout(500)

    def tearDown(self):
        self.page.close()
        self._server.shutdown()
        self._server.server_close()

    def press(self, key):
        self.page.locator(f'[data-key="{key}"]').click()
        self.page.wait_for_timeout(250)

    def enter_downward_quadratic(self):
        # Use the rendered keypad for the complete mode and coefficient flow.
        self.press("setup")
        for _ in range(8):
            self.press("dpad_right")
        self.press("2")  # page 2: Equation/Func
        self.press("2")  # Polynomial
        self.press("equals")
        self.press("2")  # quadratic
        for keys in (("negate", "1"), ("2",), ("3",)):
            for key in keys:
                self.press(key)
            self.press("equals")
        self.page.wait_for_function(
            "() => document.querySelector('#lcdEquationBody .eq-solution-pos')?.textContent === '1/4  d/c'",
            timeout=10000,
        )

    def verify_ac_from_page(self, page_index, label):
        self.enter_downward_quadratic()
        for _ in range(page_index):
            self.press("dpad_down")
        expected_position = f"{page_index + 1}/4"
        self.page.wait_for_function(
            "(position) => document.querySelector('#lcdEquationBody .eq-solution-pos')?.textContent.startsWith(position)",
            arg=expected_position,
        )
        body = self.page.locator("#lcdEquationBody").inner_text()
        self.assertIn(label, body)
        if page_index >= 2:
            self.assertIn("Max of y = ax²+bx+c", body)
        self.assertNotIn("Min of", body)

        self.press("ac")
        for key in ("2", "plus", "3", "equals"):
            self.press(key)
        self.page.wait_for_timeout(1000)
        current = self.page.evaluate(
            "() => ({ mode: appState.mode, result: appState.result, displayed: appState.resultDisplayed, "
            "screen: document.querySelector('#lcdResultLine')?.textContent, "
            "equation: document.querySelector('#lcdEquationBody')?.innerText })"
        )
        self.assertEqual(current["result"], "5", current)
        self.assertEqual(current["mode"], "Calculate", current)
        self.assertTrue(current["displayed"], current)
        self.assertTrue(self.page.locator("#lcdCalc").is_visible())
        self.assertFalse(self.page.locator("#lcdEquation").is_visible())

    def test_ac_from_page_1_starts_fresh_calculation(self):
        self.verify_ac_from_page(0, "x₁ =")

    def test_ac_from_page_2_starts_fresh_calculation(self):
        self.verify_ac_from_page(1, "x₂ =")

    def test_ac_from_page_3_starts_fresh_calculation(self):
        self.verify_ac_from_page(2, "x =")

    def test_ac_from_page_4_starts_fresh_calculation(self):
        self.verify_ac_from_page(3, "y =")


if __name__ == "__main__":
    unittest.main()
