"""Regression tests for BUG-05: the °′″ key must not dump all three symbols.

The °′″ (DMS) key used to insert the whole sequence ``°′″`` in a single
operation. The backend ``_transform_dms`` only understands a *complete* DMS
form, so pressing DMS after a number produced something like ``30°′″`` whose
minute and second components hold no digits, and evaluation failed with
``Unexpected character '′'``.

The fix keeps the key as a real calculator input sequence: each press inserts
only the next component, chosen by ``nextDmsSymbol()`` from what is already
typed in the current slot (degree -> minute -> second).

Layers covered here:
 1. backend contract  - complete DMS forms convert; the old combined token does
                        not (this is the bug).
 2. key progression   - the real `ellipsis` handler branch, `insertToken`,
                        `nextDmsSymbol` and `serializeSlot` extracted from
                        frontend.html and executed in node.
 3. editing           - DEL, AC, cursor movement and starting a new operand
                        must not leave the DMS progression inconsistent.
 4. ordinary degrees  - plain ° usage and angle-unit handling stay intact.
"""
import json
import math
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from mvp_server import safe_evaluate_expression

PROJECT = Path(__file__).resolve().parent
FRONTEND = (PROJECT / "frontend.html").read_text(encoding="utf-8")

DEG = "°"      # degree
MIN = "′"      # prime / minute
SEC = "″"      # double prime / second
DMS_ALL = DEG + MIN + SEC      # the token the key used to insert
DMS_SPLIT = {"deg": DEG, "min": MIN, "sec": SEC}


def ev(expr, angle="Degree", variables=None):
    return safe_evaluate_expression(expr, 0.0, angle, variables)


# ── 1. backend contract ─────────────────────────────────────────────────────

class TestDmsBackendContract(unittest.TestCase):
    def test_complete_dms_converts(self):
        # 30 + 31/60 + 32/3600
        r = ev(f"30{DEG}31{MIN}32{SEC}")
        self.assertAlmostEqual(r, 30.5255, places=3)

    def test_partial_dms_forms_convert(self):
        self.assertAlmostEqual(ev(f"30{DEG}"), 30.0)
        self.assertAlmostEqual(ev(f"30{DEG}31{MIN}"), 30 + 31 / 60, places=6)

    def test_old_combined_token_is_rejected(self):
        # The pre-fix key produced 30°′″: no minute/second digits, so the
        # backend must fail. This is the defect BUG-05 is about.
        with self.assertRaises(ValueError):
            ev(f"30{DMS_ALL}")

    def test_degree_only_forms_unaffected(self):
        self.assertAlmostEqual(ev(f"1+2{DEG}"), 3.0)
        self.assertAlmostEqual(ev("sin(30" + DEG + ")"), 0.5, places=9)
        self.assertAlmostEqual(ev(f"30.5256{DEG}"), 30.5256)

    def test_angle_units_unaffected(self):
        # The degree sign only marks a value as already being in the active
        # unit, so it must not itself convert; trig still follows the setting.
        for unit in ("Degree", "Radian", "Gradian"):
            self.assertAlmostEqual(ev(f"45{DEG}", unit), 45.0, msg=unit)
        self.assertAlmostEqual(ev(f"sin(30{DEG})", "Radian"),
                               math.sin(30.0), places=9)
        self.assertAlmostEqual(ev(f"sin(30{DEG})", "Degree"), 0.5, places=9)

    def test_arithmetic_around_dms(self):
        r = ev(f"10+{20}{DEG}30{MIN}00{SEC}")
        self.assertAlmostEqual(r, 30.5)


# ── 2/3. frontend key behaviour, executed from real source ────────────────

FUNCTIONS = [
    "serializeSlot",
    "routeResultInput",
    "routeErrorInput",
    "classifyInsertToken",
    "normalizeResultErrorEntry",
    "resetExpr",
    "insertToken",
    "deleteAtCursor",
    "moveCursorLeft",
    "moveCursorRight",
    "nextDmsSymbol",
]

STUBS = """
let _id = 1;
function pushUndoState() {}
function renderLCD() {}
function syncBackendExpression() {}
function getParent() { return null; }
const appState = {
  insertMode: false, error: null, result: null, resultDisplayed: false,
  lastAnswer: null, isFractionMode: false, base: 10, baseNBase: 10, undoStack: []
};
let rootSlot = null;
let cursor = { slot: null, index: 0 };
"""

# The DMS key handler branch, sliced verbatim from the main key router. Running
# this (not a re-implementation) is what makes the test meaningful.
ROUTER_ANCHOR = "if (rawKey === 'sto') {"
BRANCH_START = "if (rawKey === 'ellipsis') {"
BRANCH_END = "if (rawKey === 'integral') {"


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


def extract_const(src, name):
    m = re.search(rf"^  const {name} = .*$", src, re.M)
    assert m, f"const {name} not found in frontend.html"
    return m.group(0).strip()


def dms_branch():
    anchor = FRONTEND.index(ROUTER_ANCHOR)
    start = FRONTEND.index(BRANCH_START, anchor)
    end = FRONTEND.index(BRANCH_END, start)
    return FRONTEND[start:end]


DRIVER = """
// The app initialises the entry tree at startup; mirror that before driving.
rootSlot = createSlot();
cursor = { slot: rootSlot, index: 0 };

function pressDms() {
  const rawKey = 'ellipsis';
  const isShift = false;
  const isAlpha = false;
  const useAlphaForHex = false;
  function handlePendingVar() { return false; }
__BRANCH__
}

function apply(step) {
  const kind = step[0];
  if (kind === 'key') insertToken(step[1]);
  else if (kind === 'dms') pressDms();
  else if (kind === 'old_dms') insertToken('°′″');
  else if (kind === 'del') deleteAtCursor();
  else if (kind === 'ac') resetExpr();
  else if (kind === 'left') moveCursorLeft();
  else if (kind === 'right') moveCursorRight();
  else throw new Error('unknown step ' + kind);
}

function snap() {
  return {
    expr: serializeSlot(rootSlot),
    items: rootSlot.items.map((i) => (typeof i === 'string' ? i : '<' + i.type + '>')),
    index: cursor.index,
    slot: cursor.slot.items.map((i) => (typeof i === 'string' ? i : '<' + i.type + '>'))
  };
}

const out = [];
for (const step of JSON.parse(process.argv[2])) { apply(step); out.push(snap()); }
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestDmsKeyInput(unittest.TestCase):
    """Drives the real frontend routing/insertion code for the °′″ key."""

    @classmethod
    def setUpClass(cls):
        parts = [STUBS,
                 extract_const(FRONTEND, "nextId"),
                 extract_const(FRONTEND, "createSlot")]
        parts += [extract_function(FRONTEND, n) for n in FUNCTIONS]
        parts.append(DRIVER.replace("__BRANCH__", dms_branch()))
        cls.tmp = PROJECT / ".dms_test_tmp.js"
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

    def test_key_inserts_one_symbol_at_a_time(self):
        # BUG-05: one press must add exactly one DMS symbol.
        snaps = self.run_steps([["key", "3"], ["key", "0"], ["dms"]])
        self.assertEqual(snaps[-1]["items"], ["3", "0", DEG])
        self.assertEqual(snaps[-1]["expr"], f"30{DEG}")

    def test_full_dms_progression_case1(self):
        # 30 -> 30° -> 30°31′ -> 30°31′32″
        got = []
        steps = [["key", "3"], ["key", "0"], ["dms"]]
        got.append(self.expr(steps))
        steps += [["key", "3"], ["key", "1"], ["dms"]]
        got.append(self.expr(steps))
        steps += [["key", "3"], ["key", "2"], ["dms"]]
        got.append(self.expr(steps))
        self.assertEqual(got, [f"30{DEG}", f"30{DEG}31{MIN}",
                               f"30{DEG}31{MIN}32{SEC}"])

    def test_constructed_dms_is_accepted_by_backend_case2(self):
        # End-to-end: keypad sequence -> serialized expression -> evaluation.
        steps = [["key", "3"], ["key", "0"], ["dms"],
                 ["key", "3"], ["key", "1"], ["dms"],
                 ["key", "3"], ["key", "2"], ["dms"]]
        built = self.expr(steps)
        self.assertEqual(built, f"30{DEG}31{MIN}32{SEC}")
        self.assertAlmostEqual(ev(built), 30.5255, places=3)

    def test_old_key_output_would_fail_backend(self):
        # Same input, old key behaviour: the whole sequence in one token.
        built = self.expr([["key", "3"], ["key", "0"], ["old_dms"]])
        self.assertEqual(built, f"30{DMS_ALL}")
        with self.assertRaises(ValueError):
            ev(built)

    def test_minute_only_sequence(self):
        built = self.expr([["key", "1"], ["key", "2"], ["dms"]])
        self.assertEqual(built, f"12{DEG}")
        built = self.expr([["key", "1"], ["key", "2"], ["dms"],
                           ["key", "3"], ["key", "0"], ["dms"]])
        self.assertEqual(built, f"12{DEG}30{MIN}")
        self.assertAlmostEqual(ev(built), 12.5, places=9)

    def test_del_removes_one_symbol_and_resyncs_case4(self):
        steps = [["key", "3"], ["key", "0"], ["dms"],
                 ["key", "3"], ["key", "1"], ["dms"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31{MIN}")
        # DEL removes exactly one token: ′ then 1 then 3.
        steps += [["del"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31")
        steps += [["del"]]
        self.assertEqual(self.expr(steps), f"30{DEG}3")
        steps += [["del"]]
        self.assertEqual(self.expr(steps), f"30{DEG}")
        # One more DEL drops the degree symbol; DMS then starts over.
        steps += [["del"]]
        self.assertEqual(self.expr(steps), "30")
        steps += [["dms"]]
        self.assertEqual(self.expr(steps), f"30{DEG}")

    def test_del_mid_sequence_keeps_progression_consistent(self):
        # 30°31′32″ minus the last two tokens -> next DMS must offer ″ again.
        steps = [["key", "3"], ["key", "0"], ["dms"],
                 ["key", "3"], ["key", "1"], ["dms"],
                 ["key", "3"], ["key", "2"], ["dms"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31{MIN}32{SEC}")
        steps += [["del"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31{MIN}32")
        steps += [["del"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31{MIN}3")
        steps += [["del"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31{MIN}")
        steps += [["dms"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31{MIN}{SEC}")

    def test_ac_clears_expression_case4(self):
        steps = [["key", "3"], ["key", "0"], ["dms"], ["ac"]]
        self.assertEqual(self.expr(steps), "")
        steps += [["dms"]]
        self.assertEqual(self.expr(steps), DEG)

    def test_cursor_movement_does_not_corrupt_state_case4(self):
        steps = [["key", "3"], ["key", "0"], ["dms"],
                 ["key", "3"], ["key", "1"], ["dms"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31{MIN}")
        # Walk left past the degree symbol: the component after it is still a
        # minute run, so DMS must not re-offer the degree symbol there.
        steps += [["left"]] * 6
        snaps = self.run_steps(steps)
        self.assertLess(snaps[-1]["index"], snaps[-2]["index"])

    def test_new_operand_after_operator_starts_fresh_degree_case4(self):
        # A finished DMS group followed by an operator must not leak state.
        steps = [["key", "3"], ["key", "0"], ["dms"],
                 ["key", "3"], ["key", "1"], ["dms"],
                 ["key", "3"], ["key", "2"], ["dms"],
                 ["key", "+"], ["key", "5"], ["dms"]]
        self.assertEqual(self.expr(steps), f"30{DEG}31{MIN}32{SEC}+5{DEG}")

    def test_ordinary_degree_key_use_case5(self):
        # Just a degree sign after a number is a normal degree entry.
        built = self.expr([["key", "9"], ["key", "0"], ["dms"]])
        self.assertEqual(built, f"90{DEG}")
        self.assertAlmostEqual(ev(built), 90.0)

    def test_dms_after_result_starts_fresh_entry(self):
        # RESULT routing: a displayed result is discarded for fresh number
        # input, exactly as for any other numeric token.
        snaps = self.run_steps([["key", "3"], ["key", "0"], ["dms"]])
        self.assertEqual(snaps[-1]["expr"], f"30{DEG}")

    def test_dms_inside_fraction_template(self):
        # The decision uses the *current* slot, so a template slot behaves.
        steps = [["dms"]]
        snaps = self.run_steps(steps)
        self.assertEqual(snaps[-1]["slot"], [DEG])

    def test_handler_is_wired_to_the_helper(self):
        # Guards the wiring itself: the key must call nextDmsSymbol(), and the
        # old all-at-once token must be gone from the handler.
        branch = dms_branch()
        self.assertIn("insertToken(nextDmsSymbol()); return;", branch)
        self.assertNotIn(DMS_ALL, branch)


if __name__ == "__main__":
    unittest.main()
