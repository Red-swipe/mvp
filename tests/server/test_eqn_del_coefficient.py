"""Regression coverage: DEL must be able to edit a COMMITTED coefficient in the
simultaneous-equation input flow.

Defect this locks down: the DEL branch did
`eq.inputBuffer = eq.inputBuffer.slice(0,-1)`, which is a no-op when the buffer
is empty. A coefficient that had already been committed (by = or a D-pad press)
lived only in `eq.coefficientValues[row][col]`, and nothing ever pulled it back
into the buffer, so the cell rendered blank while the old number stayed in
state. Pressing = afterwards silently re-committed the untouched value, so the
coefficient could not be corrected.

Expected behaviour, driven here through the real key handler:
  enter -> commit -> DEL restores the value into the editable buffer and
  clears the stored field -> retype -> recommit.

Both the rendered LCD and the underlying eq.coefficientValues are asserted, so
a blank-looking cell cannot hide a still-stored value. Layouts with two, three
and four unknowns are covered because `cols` (and therefore navigation) changes
with the equation count.
"""
import json
import pathlib
import threading
import time
import unittest
from http.server import ThreadingHTTPServer

FRONTEND_PATH = pathlib.Path(__file__).resolve().parents[2] / "frontend.html"
FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright

    _pw = sync_playwright().start()
    _b = _pw.chromium.launch(channel="chrome")
    HAVE_BROWSER = True
    _b.close()
    _pw.stop()
except Exception:  # pragma: no cover - environment dependent
    HAVE_BROWSER = False


class TestDelWiring(unittest.TestCase):
    def test_del_branch_handles_the_empty_buffer(self):
        body = FRONTEND[FRONTEND.index("const commit=()=>{"):]
        body = body[: body.index("else if (rawKey === 'dpad_up')")]
        self.assertIn("rawKey === 'del'", body)
        # The old one-liner could never handle the empty-buffer case.
        self.assertNotIn(
            "else if (rawKey === 'del') eq.inputBuffer=eq.inputBuffer.slice(0,-1);",
            body)

    def test_del_reads_and_clears_the_committed_field(self):
        body = FRONTEND[FRONTEND.index("const commit=()=>{"):]
        body = body[: body.index("else if (rawKey === 'dpad_up')")]
        self.assertIn("eq.coefficientValues[eq.currentEquation]?.[eq.currentCoefficient]", body)
        self.assertIn("eq.inputBuffer = String(stored)", body)
        self.assertIn("eq.coefficientValues[eq.currentEquation][eq.currentCoefficient] = ''", body)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestDelOnCommittedCoefficient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(FRONTEND_PATH.parent))
        import mvp_server  # noqa: E402

        cls._srv = ThreadingHTTPServer(("127.0.0.1", 0), mvp_server.MvpHandler)
        cls.port = cls._srv.server_address[1]
        threading.Thread(target=cls._srv.serve_forever, daemon=True).start()
        time.sleep(0.4)
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls.browser.new_page(viewport={"width": 1000, "height": 1300})
        cls.page.goto(f"http://127.0.0.1:{cls.port}/", wait_until="domcontentloaded")
        cls.page.wait_for_timeout(2500)

    @classmethod
    def tearDownClass(cls):
        cls.page.close()
        cls.browser.close()
        cls._pw.stop()
        cls._srv.shutdown()
        cls._srv.server_close()

    # -- helpers -----------------------------------------------------------
    def key(self, k, shift=False, alpha=False):
        self.page.evaluate(
            """([k,s,a]) => { const b=document.querySelector('[data-key="'+k+'"]');
                 if(!b) throw new Error('no such key '+k);
                 appState.shift=!!s; appState.alpha=!!a; handleKey(b);
                 appState.shift=false; appState.alpha=false; renderLCD(); }""",
            [k, shift, alpha])
        self.page.wait_for_timeout(120)

    def enter_equation_mode(self, unknowns):
        """Drive the real menu: MODE -> 3 (Equation) -> simultaneous -> count."""
        self.page.evaluate(
            """() => { appState.mode = 'Equation/Func';
                 appState.equation = { phase:'typeMenu', selectedMenuItem:0,
                   selectedType:null, numberOfEquations:0, polynomialDegree:0,
                   coefficientValues:[], inputBuffer:'', currentEquation:0,
                   currentCoefficient:0, selectedMenuItem2:0, resultState:null,
                   extremum:null, solutionIndex:0 };
                 renderLCD(); }""")
        self.page.wait_for_timeout(150)
        self.key("equals")                      # pick Simultaneous
        self.page.wait_for_timeout(150)
        # count menu: index 0 -> 2 unknowns, 1 -> 3, 2 -> 4
        for _ in range(unknowns - 2):
            self.key("dpad_down")
        self.key("equals")
        self.page.wait_for_timeout(250)

    def state(self):
        return self.page.evaluate(
            """() => ({ phase: appState.equation.phase,
                        row: appState.equation.currentEquation,
                        col: appState.equation.currentCoefficient,
                        buffer: appState.equation.inputBuffer,
                        values: JSON.parse(JSON.stringify(appState.equation.coefficientValues)),
                        lcd: document.getElementById('lcdEquation').innerText })""")

    def type_digits(self, text):
        for ch in text:
            self.key(ch)

    def commit_at_cursor(self, text):
        """Type a coefficient and commit it. `=` commits AND advances, so the
        caller gets the cursor on the next field, exactly as the device does."""
        self.type_digits(text)
        self.key("equals")
        self.wait_for(lambda: self.state()["buffer"] == "")

    def back_to_previous_field(self):
        self.key("dpad_left")
        self.wait_for(lambda: True)

    def wait_for(self, predicate):
        for _ in range(60):
            if predicate():
                return True
            self.page.wait_for_timeout(50)
        return False

    def field_text(self, row, col):
        """The text the LCD actually renders for one cell."""
        return self.page.evaluate(
            """([r,c]) => { const f = document.querySelectorAll('.eq-row')[r]
                 ?.querySelectorAll('.eq-field')[c]; return f ? f.textContent : null; }""",
            [row, col])

    # -- tests -------------------------------------------------------------
    def test_layout_is_created_for_two_three_and_four_unknowns(self):
        for n, size in ((2, 2), (3, 3), (4, 4)):
            with self.subTest(unknowns=n):
                self.enter_equation_mode(n)
                st = self.state()
                self.assertEqual(st["phase"], "simultaneousInput")
                self.assertEqual(len(st["values"]), n)
                self.assertEqual(len(st["values"][0]), n + 1)

    def test_del_on_empty_buffer_restores_the_committed_value(self):
        self.enter_equation_mode(3)
        self.commit_at_cursor("12")           # commits [0][0]=12, cursor -> [0][1]
        after_commit = self.state()
        self.assertEqual(after_commit["values"][0][0], 12)
        self.assertEqual(after_commit["col"], 1)

        self.back_to_previous_field()          # return to [0][0]
        self.assertEqual(self.state()["col"], 0)
        self.key("del")                        # <- the reported defect
        restored = self.state()
        self.assertEqual(restored["buffer"], "12", "DEL did not restore the value")
        self.assertEqual(restored["values"][0][0], "", "old value still retained")
        self.assertEqual((restored["row"], restored["col"]), (0, 0))
        self.assertEqual(self.field_text(0, 0), "12")

    def test_retyped_value_is_recommitted(self):
        self.enter_equation_mode(3)
        self.commit_at_cursor("12")
        self.back_to_previous_field()
        self.key("del")                        # restore "12" + clear the field
        self.key("del")                        # erase the '2'
        self.assertEqual(self.state()["buffer"], "1")
        self.type_digits("7")
        self.assertEqual(self.state()["buffer"], "17")
        self.key("equals")                     # recommit
        st = self.state()
        self.assertEqual(st["values"][0][0], 17)
        self.assertEqual(st["buffer"], "")
        self.assertEqual(st["col"], 1)

    def test_del_clears_the_coefficient_entirely_when_erased(self):
        self.enter_equation_mode(3)
        self.commit_at_cursor("5")
        self.back_to_previous_field()
        self.key("del")                        # restore "5"
        self.key("del")                        # erase it -> buffer empty
        st = self.state()
        self.assertEqual(st["buffer"], "")
        self.assertEqual(st["values"][0][0], "", "value survived a full erase")
        self.assertEqual(self.field_text(0, 0), "")
        # the next field still works
        self.key("dpad_right")
        self.type_digits("9")
        self.key("equals")
        st = self.state()
        self.assertEqual(st["values"][0][1], 9)

    def test_del_does_not_touch_the_neighbouring_coefficients(self):
        self.enter_equation_mode(3)
        self.commit_at_cursor("2")             # [0][0] = 2, cursor -> [0][1]
        self.commit_at_cursor("5")             # [0][1] = 5, cursor -> [0][2]
        st = self.state()
        self.assertEqual((st["values"][0][0], st["values"][0][1]), (2, 5))
        self.assertEqual((st["row"], st["col"]), (0, 2))

        self.back_to_previous_field()          # back onto [0][1]
        self.assertEqual(self.state()["col"], 1)
        self.key("del")
        st = self.state()
        self.assertEqual(st["buffer"], "5")
        self.assertEqual(st["values"][0][1], "")
        self.assertEqual(st["values"][0][0], 2, "left neighbour was disturbed")

    def test_navigation_still_works_after_a_del_cycle(self):
        self.enter_equation_mode(4)
        self.commit_at_cursor("1")             # [0][0]=1, cursor -> [0][1]
        self.back_to_previous_field()
        self.key("del")                        # restore "1", clear field
        self.key("del")                        # erase -> buffer empty
        st = self.state()
        self.assertEqual(st["buffer"], "")
        self.assertEqual(st["values"][0][0], "")
        # navigate forward and enter a fresh coefficient
        self.key("dpad_right")
        st = self.state()
        self.assertEqual((st["row"], st["col"]), (0, 1))
        self.type_digits("3")
        self.key("equals")
        st = self.state()
        self.assertEqual(st["values"][0][1], 3)
        self.assertEqual((st["row"], st["col"]), (0, 2))

    def test_four_unknown_layout_end_to_end(self):
        self.enter_equation_mode(4)
        # cols = unknowns + 1 = 5, so four commits fill the four coefficient
        # columns and leave the cursor on the constant column [0][4]. A fifth
        # = would solve the equation rather than advance.
        for digit in ["1", "2", "3", "4"]:
            self.commit_at_cursor(digit)
        st = self.state()
        self.assertEqual(st["values"][0][:4], [1, 2, 3, 4])
        self.assertEqual(st["col"], 4)
        # correct the second coefficient
        for _ in range(3):
            self.key("dpad_left")
        self.assertEqual(self.state()["col"], 1)
        self.key("del")
        self.key("del")
        self.type_digits("9")
        self.key("equals")
        st = self.state()
        self.assertEqual(st["values"][0][1], 9)
        self.assertEqual(st["values"][0][0], 1)
        self.assertEqual(st["values"][0][2], 3)
        self.assertEqual(st["values"][0][3], 4)

    def test_del_on_an_untouched_field_is_a_harmless_noop(self):
        self.enter_equation_mode(2)
        before = self.state()
        self.key("del")
        after = self.state()
        self.assertEqual(after["buffer"], "")
        self.assertEqual(after["values"], before["values"])
        self.assertEqual((after["row"], after["col"]), (0, 0))