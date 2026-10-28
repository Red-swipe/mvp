"""Caret editing regressions for the browser editor, server adapter and desktop."""
import os
import threading
import time
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = (ROOT / "frontend.html").read_text(encoding="utf-8")
try:
    from playwright.sync_api import sync_playwright
    from browser_support import chromium_executable
    HAVE_PLAYWRIGHT = True
except ImportError:
    HAVE_PLAYWRIGHT = False

CHROMIUM = chromium_executable() if HAVE_PLAYWRIGHT else None


@unittest.skipUnless(CHROMIUM, "Playwright-managed Chromium is not installed")
class TestBrowserCaretEditing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True, executable_path=CHROMIUM)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.goto((ROOT / "frontend.html").as_uri())

    def tearDown(self):
        self.page.close()

    def test_del_backspaces_before_caret(self):
        state = self.page.evaluate("""() => {
          resetExpr(); for (const ch of '963*36') insertToken(ch);
          cursor.index = 4; deleteAtCursor();
          return {text:getExpr(), index:cursor.index};
        }""")
        self.assertEqual(state, {"text": "96336", "index": 3})

    def test_insert_preserves_character_after_caret(self):
        state = self.page.evaluate("""() => {
          resetExpr(); for (const ch of '963*6') insertToken(ch);
          cursor.index = 4; insertToken('3');
          return {text:getExpr(), index:cursor.index};
        }""")
        self.assertEqual(state, {"text": "963*36", "index": 5})

    def test_del_at_end_removes_last_item(self):
        state = self.page.evaluate("""() => {
          resetExpr(); for (const ch of 'abcdef') insertToken(ch);
          deleteAtCursor();
          return {text:getExpr(), index:cursor.index};
        }""")
        self.assertEqual(state, {"text": "abcde", "index": 5})

    def test_insert_at_start_middle_end_and_immediate_backspace(self):
        for text, position in [("12", 0), ("12", 1), ("12", 2)]:
            with self.subTest(text=text, position=position):
                state = self.page.evaluate("""({text,position}) => {
                  resetExpr(); for (const ch of text) insertToken(ch);
                  cursor.index = position; insertToken('X');
                  const inserted = {text:getExpr(), index:cursor.index};
                  deleteAtCursor();
                  return {inserted, after:{text:getExpr(), index:cursor.index}};
                }""", {"text": text, "position": position})
                self.assertEqual(state["inserted"]["text"], text[:position] + "X" + text[position:])
                self.assertEqual(state["after"]["text"], text)

    def test_repeated_del_stops_cleanly_at_empty(self):
        state = self.page.evaluate("""() => {
          resetExpr(); for (const ch of '12') insertToken(ch);
          deleteAtCursor(); deleteAtCursor(); deleteAtCursor();
          return {text:getExpr(), index:cursor.index};
        }""")
        self.assertEqual(state, {"text": "", "index": 0})

    def test_function_key_is_one_deletion_unit(self):
        state = self.page.evaluate("""() => {
          resetExpr(); insertToken('sin('); deleteAtCursor();
          return {text:getExpr(), index:cursor.index, count:rootSlot.items.length};
        }""")
        self.assertEqual(state, {"text": "", "index": 0, "count": 0})

    def test_del_in_template_empty_slot_removes_template_without_dangling_structure(self):
        state = self.page.evaluate("""() => {
          resetExpr(); insertFraction(); deleteAtCursor();
          return {text:getExpr(), index:cursor.index, count:rootSlot.items.length};
        }""")
        self.assertEqual(state, {"text": "", "index": 0, "count": 0})

    def test_del_matrix_at_start_middle_end_for_expression_shapes(self):
        cases = [
            (["7"], 0, ["7"]), (["7"], 1, []),
            (list("1234"), 0, list("1234")), (list("1234"), 2, list("134")), (list("1234"), 4, list("123")),
            (list("12.3"), 0, list("12.3")), (list("12.3"), 2, list("1.3")), (list("12.3"), 4, list("12.")),
            (["1", "+", "2"], 0, ["1", "+", "2"]), (["1", "+", "2"], 2, ["1", "2"]), (["1", "+", "2"], 3, ["1", "+"]),
            (["(", "2", ")"], 0, ["(", "2", ")"]), (["(", "2", ")"], 2, ["(", ")"]), (["(", "2", ")"], 3, ["(", "2"]),
            (["sin(", "2", ")"], 0, ["sin(", "2", ")"]), (["sin(", "2", ")"], 1, ["2", ")"]), (["sin(", "2", ")"], 3, ["sin(", "2"]),
        ]
        for items, pos, expected in cases:
            with self.subTest(items=items, pos=pos):
                actual = self.page.evaluate("""({items,pos}) => {
                  resetExpr(); for (const item of items) insertToken(item);
                  cursor.index=pos; deleteAtCursor();
                  return {items:rootSlot.items.slice(), index:cursor.index};
                }""", {"items": items, "pos": pos})
                self.assertEqual(actual["items"], expected)
                self.assertEqual(actual["index"], max(0, pos - 1))

    def test_ac_resets_cursor_pending_modifiers_and_result_or_error(self):
        for pos in (0, 1, 3):
            for state in ("input", "result", "error"):
                with self.subTest(pos=pos, state=state):
                    actual = self.page.evaluate("""({pos,state}) => {
                      resetExpr(); for (const c of '123') insertToken(c);
                      cursor.index=pos; appState.shift=true; appState.alpha=true;
                      if(state==='result'){appState.resultDisplayed=true;appState.result='6';}
                      if(state==='error') appState.error='Math ERROR';
                      resetExpr();
                      return {text:getExpr(),index:cursor.index,shift:appState.shift,
                        alpha:appState.alpha,result:appState.result,
                        displayed:appState.resultDisplayed,error:appState.error};
                    }""", {"pos": pos, "state": state})
                    self.assertEqual(actual["text"], "")
                    self.assertEqual(actual["index"], 0)
                    self.assertFalse(actual["shift"])
                    self.assertFalse(actual["alpha"])
                    self.assertIsNone(actual["result"])
                    self.assertFalse(actual["displayed"])
                    self.assertIsNone(actual["error"])

    def test_arrow_boundaries_and_mixed_edit_sequence(self):
        actual = self.page.evaluate("""() => {
          resetExpr(); moveCursorLeft(); const leftStart=cursor.index;
          for(const c of '12345') insertToken(c);
          moveCursorRight(); const rightEnd=cursor.index;
          moveCursorLeft(); moveCursorLeft(); moveCursorLeft();
          insertToken('X'); deleteAtCursor(); insertToken('Y');
          return {leftStart,rightEnd,text:getExpr(),index:cursor.index};
        }""")
        self.assertEqual(actual["leftStart"], 0)
        self.assertEqual(actual["rightEnd"], 5)
        self.assertEqual(actual["text"], "12Y345")
        self.assertEqual(actual["index"], 3)

    def test_templates_accept_editing_inside_slots(self):
        for kind in ("fraction", "power", "integral"):
            with self.subTest(kind=kind):
                actual = self.page.evaluate("""(kind) => {
                  resetExpr();
                  if(kind==='fraction') insertFraction();
                  else if(kind==='power') insertPower(false);
                  else insertIntegral();
                  const target=cursor.slot;
                  insertToken('2'); insertToken('3');
                  moveCursorLeft(); insertToken('X'); deleteAtCursor();
                  return {index:cursor.index, count:target.items.length,
                    text:getExpr(), targetAlive:Array.isArray(target.items)};
                }""", kind)
                self.assertGreaterEqual(actual["index"], 0)
                self.assertTrue(actual["targetAlive"])
                self.assertNotIn("XX", actual["text"])


@unittest.skipUnless(CHROMIUM, "Playwright-managed Chromium is not installed")
class TestServedCalculatorEditing(TestBrowserCaretEditing):
    """Exercise actual keypad handlers on the HTTP-served teacher path."""
    @classmethod
    def setUpClass(cls):
        import mvp_server
        cls._srv = ThreadingHTTPServer(("127.0.0.1", 0), mvp_server.MvpHandler)
        cls.port = cls._srv.server_address[1]
        threading.Thread(target=cls._srv.serve_forever, daemon=True).start()
        time.sleep(0.2)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True, executable_path=CHROMIUM)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls._srv.shutdown()
        cls._srv.server_close()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.goto("http://127.0.0.1:%d/" % self.port, wait_until="load")
        self.page.wait_for_timeout(250)

    def press(self, key):
        return self.page.evaluate("""(key) => {
          const button = document.querySelector(`[data-key="${key}"]`);
          if (!button) throw new Error('missing keypad button '+key);
          handleKey(button);
          return {text:getExpr(), cursor:cursor.index,
            lcd:document.querySelector('.lcd')?.innerText || ''};
        }""", key)

    def test_teacher_path_three_reproductions(self):
        self.page.evaluate("hardResetExpr(); appState.poweredOn=true; renderLCD()")
        for k in ["9", "6", "3", "multiply", "3", "6"]: self.press(k)
        self.press("dpad_left"); self.press("dpad_left"); result = self.press("del")
        self.assertEqual(result["text"], "96336")
        self.assertEqual(result["cursor"], 3)
        self.page.evaluate("hardResetExpr()")
        for k in ["9", "6", "3", "multiply", "6"]: self.press(k)
        self.press("dpad_left"); result = self.press("3")
        self.assertEqual(result["text"], "963*36")
        self.assertEqual(result["cursor"], 5)
        self.page.evaluate("hardResetExpr()")
        for ch in "abcdef": self.page.evaluate("(c)=>insertToken(c)", ch)
        result = self.press("del")
        self.assertEqual(result["text"], "abcde")

    def test_edited_expression_is_the_one_sent_to_engine(self):
        self.page.evaluate("hardResetExpr(); appState.poweredOn=true; renderLCD()")
        for k in ["9", "6", "3", "multiply", "6"]: self.press(k)
        self.press("dpad_left"); self.press("3")
        before = self.page.evaluate("getExpr()")
        self.assertEqual(before, "963*36")
        self.press("equals")
        self.page.wait_for_function("appState.resultDisplayed === true || !!appState.error", timeout=10000)
        result = self.page.evaluate("({expression:getExpr(), result:appState.result, error:appState.error})")
        self.assertEqual(result["expression"], before)
        self.assertIsNone(result["error"])
        self.assertEqual(float(result["result"]), 34668)


class TestServerAdapterCaret(unittest.TestCase):
    def test_per_key_buffer_obeys_caret_insert_and_backspace(self):
        from mvp_server import CalculatorController
        c = CalculatorController()
        for key in ("9", "6", "3", "multiply", "6"):
            c.press_key({"key": key})
        c.press_key({"key": "dpad_left"})
        state = c.press_key({"key": "3"})
        self.assertEqual(state["expression"], "963*36")
        self.assertEqual(state["cursorPosition"], 5)
        state = c.press_key({"key": "del"})
        self.assertEqual(state["expression"], "963*6")
        self.assertEqual(state["cursorPosition"], 4)


class TestDesktopCaret(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
            cls.app = QApplication.instance() or QApplication([])
            from main import CalculatorWindow
            cls.CalculatorWindow = CalculatorWindow
        except ImportError as exc:
            raise unittest.SkipTest("PySide6 is unavailable: %s" % exc)

    def test_desktop_caret_sequences(self):
        window = self.CalculatorWindow()
        for key in ("9", "6", "3", "multiply", "6"):
            window.on_key(key)
        window.on_key("dpad_left")
        window.on_key("3")
        self.assertEqual(window.expr, "963*36")
        self.assertEqual(window.cursor_position, 5)
        window.on_key("del")
        self.assertEqual(window.expr, "963*6")
        self.assertEqual(window.cursor_position, 4)
        window.on_key("ac")
        self.assertEqual((window.expr, window.cursor_position), ("", 0))
        window.close()


if __name__ == "__main__":
    unittest.main()
