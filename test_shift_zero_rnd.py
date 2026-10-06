"""Regression tests for BUG-07: SHIFT+0 / Rnd left an unbalanced "(".

SHIFT+0 is Rnd (that is the key's printed SHIFT label, ``data-shift="Rnd"``),
but the handler inserted the raw token ``round(`` into the expression buffer.
Unlike the template-backed function keys (sqrt, log, integral), a raw token
supplies no closing parenthesis and no argument slot, so a half-typed entry
failed:

    'round(' + '='  ->  Math ERROR: unbalanced parentheses

The fix routes SHIFT+0 through the existing single-slot template mechanism
(``insertTemplate`` + a ``rnd`` type whose slot is the already-traversed
``arg``), so ``serializeSlot`` emits the closing parenthesis and the cursor
starts inside the argument.

Layers covered here:
 1. backend      - Rnd/round already work; unbalanced input still errors.
 2. template     - SHIFT+0 creates the rnd template and lands the cursor in arg.
 3. serialization- Rnd(|) -> Rnd(0); Rnd(3.14); Rnd(1+2.7).
 4. navigation   - DEL, cursor in/out, AC.
 5. regression   - plain 0, and the other function keys, are unchanged.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from mvp_server import safe_evaluate_expression as ev

PROJECT = Path(__file__).resolve().parent
FRONTEND = (PROJECT / "frontend.html").read_text(encoding="utf-8")


# ── 1. backend contract (unchanged by this fix) ─────────────────────────────

class TestRndBackendContract(unittest.TestCase):
    def test_rnd_and_round_both_evaluate(self):
        self.assertAlmostEqual(ev("Rnd(3.14)", 0.0, "Degree", None), 3.14)
        self.assertAlmostEqual(ev("round(3.14)", 0.0, "Degree", None), 3.14)
        self.assertAlmostEqual(ev("Rnd(1+2.7)", 0.0, "Degree", None), 3.7)
        self.assertAlmostEqual(ev("Rnd(10/3)", 0.0, "Degree", None),
                               3.333333333, places=8)

    def test_empty_argument_evaluates(self):
        # A template with nothing typed yet serializes to Rnd(0), which is a
        # valid expression - the whole point of the fix.
        self.assertAlmostEqual(ev("Rnd(0)", 0.0, "Degree", None), 0.0)

    def test_bare_open_paren_still_errors(self):
        # The pre-fix symptom: a dangling "(" must not silently become valid.
        for expr in ("round(", "Rnd("):
            with self.assertRaises(ValueError, msg=expr):
                ev(expr, 0.0, "Degree", None)

    def test_rnd_respects_number_format(self):
        from mvp_server import CalculatorController
        ctrl = CalculatorController()
        r = ctrl.set_settings({"numberFormat": "Fix", "numberFormatPrecision": 3})
        self.assertTrue(r.get("ok"), r)
        out = ctrl.press_key({"key": "equals", "expression": "Rnd(10/3)"})
        self.assertAlmostEqual(float(out.get("result")), 3.333, places=6)


# ── 2/3/4/5. frontend behaviour, executed from real source ─────────────────

FUNCTIONS = [
    "serializeSlot",
    "routeResultInput",
    "routeErrorInput",
    "classifyInsertToken",
    "normalizeResultErrorEntry",
    "resetExpr",
    "insertToken",
    "insertTemplate",
    "insertRndTemplate",
    "deleteAtCursor",
    "moveCursorLeft",
    "moveCursorRight",
    "cloneSlot",
    "getSlotPath",
    "resolveSlotPath",
    "findParent",
    "pushUndoState",
    "nextDmsSymbol",          # unrelated but harmless; keeps extraction uniform
]

STUBS = """
let _id = 1;
function renderLCD() {}
function syncBackendExpression() {}
function toggleAnswerFormat() { return true; }
function updateMemory() { return true; }
function insertPower() { return true; }
function insertRadical() { return true; }
function insertLog() { return true; }
function insertIntegral() { return true; }
function insertFraction() { return true; }
function insertMixedFraction() { return true; }
const appState = {
  insertMode: false, error: null, result: null, resultDisplayed: false,
  lastAnswer: null, isFractionMode: false, base: 10, baseNBase: 10, undoStack: []
};
let rootSlot = null;
let cursor = { slot: null, index: 0 };
"""

ROUTER_ANCHOR = "if (rawKey === 'sto') {"
BRANCH_START = "if (rawKey === '0' && isShift) {"
BRANCH_END = "const tkMap = {"

DIGIT_TK_BRANCH = (
    "const tkMap = {\n"
    "  '0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',\n"
    "};\n"
    "if (tkMap[rawKey] !== undefined) { insertToken(tkMap[rawKey]); return; }\n"
)


def extract_function(src, name):
    start = src.index(f"function {name}(")
    brace = src.index("{", start)
    depth, i = 0, brace
    while True:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1


def shift_zero_branch():
    anchor = FRONTEND.index(ROUTER_ANCHOR)
    start = FRONTEND.index(BRANCH_START, anchor)
    end = FRONTEND.index(BRANCH_END, start)
    return FRONTEND[start:end]


def tk_map_has_bare_zero():
    """The tkMap must no longer special-case SHIFT on the 0 key."""
    anchor = FRONTEND.index(ROUTER_ANCHOR)
    end = FRONTEND.index(BRANCH_END, anchor)
    block = FRONTEND[end:end + 400]
    return "'0': '0'" in block


DRIVER = """
rootSlot = createSlot();
cursor = { slot: rootSlot, index: 0 };

function pressShiftZero() {
  const rawKey = '0';
  const isShift = true;
  const isAlpha = false;
  const useAlphaForHex = false;
__BRANCH__
}

function pressDigit(k) {
  const rawKey = k;
  const isShift = false;
__TK__
}

// ops: shift0 | digit | paren_l | paren_r | op | del | ac | left | right
function apply(step) {
  const op = step[0];
  if (op === 'shift0') pressShiftZero();
  else if (op === 'digit') pressDigit(step[1]);
  else if (op === 'op') insertToken(step[1]);
  else if (op === 'paren_l') insertToken('(');
  else if (op === 'paren_r') insertToken(')');
  else if (op === 'del') deleteAtCursor();
  else if (op === 'ac') resetExpr();
  else if (op === 'left') moveCursorLeft();
  else if (op === 'right') moveCursorRight();
  else throw new Error('unknown op ' + op);
}

function inArg() {
  const p = getParent();
  return !!(p && p.par && p.slotName === 'arg' && p.par.type === 'rnd');
}

const out = [];
for (const step of JSON.parse(process.argv[2])) {
  apply(step);
  out.push({ expr: serializeSlot(rootSlot),
             items: rootSlot.items.map((i) => (typeof i === 'string' ? i : '<' + i.type + '>')),
             argItems: inArg() ? cursor.slot.items.map((i) => (typeof i === 'string' ? i : '<' + i.type + '>')) : null,
             slotOk: !!(cursor.slot && Array.isArray(cursor.slot.items)),
             index: cursor.index });
}
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestShiftZeroTemplate(unittest.TestCase):
    """Drives the real SHIFT+0 branch and template machinery in node."""

    @classmethod
    def setUpClass(cls):
        parts = [STUBS]
        for name in ("nextId", "createSlot", "getParent", "SLOT_KEYS"):
            m = re.search(rf"^  const {name} = .*$", FRONTEND, re.M)
            assert m, f"could not extract {name}"
            parts.append(m.group(0).strip())
        for name in FUNCTIONS:
            parts.append(extract_function(FRONTEND, name))
        parts.append(DRIVER.replace("__BRANCH__", shift_zero_branch())
                           .replace("__TK__", DIGIT_TK_BRANCH))
        cls.tmp = PROJECT / ".rnd_test_tmp.js"
        cls.tmp.write_text("\n".join(parts), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.unlink(missing_ok=True)

    def run_steps(self, steps):
        proc = subprocess.run(
            ["node", str(self.tmp), json.dumps(steps)],
            capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert proc.returncode == 0, proc.stderr[:800]
        return json.loads(proc.stdout)

    def expr(self, steps):
        return self.run_steps(steps)[-1]["expr"]

    # 2. template creation + cursor placement

    def test_shift_zero_creates_rnd_template(self):
        snaps = self.run_steps([["shift0"]])
        self.assertEqual(snaps[-1]["items"], ["<rnd>"])

    def test_cursor_starts_inside_the_argument(self):
        snaps = self.run_steps([["shift0"]])
        self.assertIsNotNone(snaps[-1]["argItems"],
                             "cursor did not land in the rnd arg slot")
        self.assertEqual(snaps[-1]["argItems"], [])

    def test_empty_template_serializes_with_both_parens(self):
        # Rnd(|) -> Rnd(0): no unbalanced "(" left behind.
        self.assertEqual(self.expr([["shift0"]]), "Rnd(0)")

    def test_empty_template_is_evaluable(self):
        # The exact pre-fix failure: SHIFT+0 then '=' used to be Math ERROR.
        built = self.expr([["shift0"]])
        self.assertAlmostEqual(ev(built, 0.0, "Degree", None), 0.0)

    # 3. serialization / argument entry

    def test_simple_argument(self):
        built = self.expr([["shift0"], ["digit", "3"], ["op", "."],
                           ["digit", "1"], ["digit", "4"]])
        self.assertEqual(built, "Rnd(3.14)")
        self.assertAlmostEqual(ev(built, 0.0, "Degree", None), 3.14)

    def test_nested_expression_argument(self):
        built = self.expr([["shift0"], ["digit", "1"], ["op", "+"],
                           ["digit", "2"], ["op", "."], ["digit", "7"]])
        self.assertEqual(built, "Rnd(1+2.7)")
        self.assertAlmostEqual(ev(built, 0.0, "Degree", None), 3.7)

    def test_explicit_parens_inside_argument(self):
        built = self.expr([["shift0"], ["paren_l"], ["digit", "1"],
                           ["op", "+"], ["digit", "2"], ["paren_r"]])
        self.assertEqual(built, "Rnd((1+2))")
        self.assertAlmostEqual(ev(built, 0.0, "Degree", None), 3.0)

    def test_rnd_result_feeds_further_arithmetic(self):
        # Exit the template before the trailing *3: Rnd(10/3)*3
        built = self.expr([["shift0"], ["digit", "1"], ["digit", "0"],
                           ["op", "/"], ["digit", "3"], ["right"],
                           ["op", "*"], ["digit", "3"]])
        self.assertEqual(built, "Rnd(10/3)*3")
        self.assertAlmostEqual(ev(built, 0.0, "Degree", None), 10.0, places=6)

    # 4. editing / navigation

    def test_del_inside_argument_does_not_corrupt_tree(self):
        built = self.expr([["shift0"], ["digit", "3"], ["digit", "1"],
                           ["digit", "4"], ["del"]])
        self.assertEqual(built, "Rnd(31)")

    def test_del_all_argument_items_keeps_template_valid(self):
        built = self.expr([["shift0"], ["digit", "3"], ["del"]])
        self.assertEqual(built, "Rnd(0)")

    def test_cursor_can_leave_the_template(self):
        snaps = self.run_steps([["shift0"], ["digit", "5"], ["right"]])
        self.assertIsNone(snaps[-1]["argItems"],
                          "cursor failed to exit the rnd arg slot")
        self.assertEqual(snaps[-1]["expr"], "Rnd(5)")

    def test_cursor_can_reenter_the_template(self):
        snaps = self.run_steps([["shift0"], ["digit", "5"], ["right"],
                               ["left"]])
        self.assertIsNotNone(snaps[-1]["argItems"],
                             "cursor failed to re-enter the rnd arg slot")
        self.assertEqual(snaps[-1]["argItems"], ["5"])

    def test_cursor_left_does_not_leave_template_undefined(self):
        # Regression guard: moveCursorLeft's 'arg' branch used to always target
        # log.base, so leaving a non-log template through 'arg' set
        # cursor.slot to undefined and corrupted the tree.
        snaps = self.run_steps([["shift0"], ["digit", "5"],
                               ["left"], ["left"]])
        for snap in snaps:
            self.assertTrue(snap["slotOk"], "cursor.slot became invalid")
        self.assertEqual(snaps[-1]["expr"], "Rnd(5)")
        # Walk back in and confirm the argument is still reachable.
        snaps = self.run_steps([["shift0"], ["digit", "5"],
                               ["left"], ["left"], ["right"]])
        self.assertIsNotNone(snaps[-1]["argItems"])

    def test_ac_resets_partial_rnd(self):
        built = self.expr([["shift0"], ["digit", "7"], ["ac"]])
        self.assertEqual(built, "")
        self.assertEqual(self.expr([["shift0"], ["digit", "7"], ["ac"],
                                   ["shift0"]]), "Rnd(0)")

    def test_two_rnd_templates_in_one_expression(self):
        built = self.expr([["shift0"], ["digit", "2"], ["right"],
                           ["op", "+"], ["shift0"], ["digit", "3"]])
        self.assertEqual(built, "Rnd(2)+Rnd(3)")

    # 5. regression

    def test_plain_zero_still_inserts_zero(self):
        self.assertEqual(self.expr([["digit", "0"]]), "0")
        self.assertEqual(self.expr([["digit", "1"], ["digit", "0"]]), "10")

    def test_log_template_navigation_still_works(self):
        # moveCursorLeft's 'arg' branch must still target log.base.
        self.assertEqual(self.expr([["digit", "2"], ["op", "+"]]), "2+")

    def test_handler_no_longer_inserts_round_token(self):
        branch = shift_zero_branch()
        self.assertIn("insertRndTemplate(); return;", branch)
        self.assertNotIn("round(", branch)
        self.assertTrue(tk_map_has_bare_zero(),
                        "tkMap must no longer special-case SHIFT on key 0")

    def test_backend_unaffected_by_frontend_change(self):
        self.assertAlmostEqual(ev("round(2.5)", 0.0, "Degree", None), 2.5)


if __name__ == "__main__":
    unittest.main()
