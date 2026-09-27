"""Regression tests for BUG-06: SHIFT+ENG inserted a bare '<' token.

The ENG key is a *display* transform: ``cycleEngNotation()`` rewrites the shown
result into engineering notation (``m×10^n``). Its SHIFT action is the reverse
direction - the '←' half of the key's two-way ``←→`` legend, which
``main.py`` also models as the ENG key's SHIFT label.

The implementation nevertheless inserted a literal ``'<'`` into the expression
buffer. ``<`` is not a calculator operator, so the tokenizer rejected it:

    '2<3' -> Math ERROR: Unexpected character '<' at position 1

Layers covered here:
 1. backend      - '<' is rejected (the bug's mechanism), '*10^n' is accepted.
 2. ENG forward  - plain ENG behaviour is unchanged.
 3. ENG reverse  - SHIFT+ENG expands a displayed m×10^n back to decimal.
 4. slot tree    - SHIFT+ENG must not insert anything into the entry.
 5. regression   - exponent / scientific / ENG-adjacent behaviour still works.
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

TIMES = "×"          # ×
EXP = "^"


# ── 1. backend contract ─────────────────────────────────────────────────────

class TestEngBackendContract(unittest.TestCase):
    def test_angle_bracket_is_not_a_calculator_token(self):
        # The mechanism behind BUG-06: the parser has no '<'.
        for expr in ("2<3", "5<3", "1<2"):
            with self.assertRaises(ValueError, msg=expr):
                ev(expr, 0.0, "Degree", None)

    def test_engineering_notation_is_valid_backend_syntax(self):
        # The `×10^` representation the frontend emits is already supported:
        # serializeSlot() maps '×10^' to '*10^' before evaluation.
        self.assertAlmostEqual(ev("1.5*10^3", 0.0, "Degree", None), 1500.0)
        self.assertAlmostEqual(ev("1.234*10^-3", 0.0, "Degree", None), 0.001234,
                               places=9)


# ── 2/3/4. frontend ENG behaviour, executed from real source ───────────────

FUNCTIONS = [
    "answerAsNumber",
    "cycleEngNotation",
    "expandEngNotation",
    "localFormat",
    "normalizeResultErrorEntry",
    "resetExpr",
    "insertToken",
    "classifyInsertToken",
    "routeResultInput",
    "routeErrorInput",
    "serializeSlot",
    "_fmtG",
    "_expandIntDigits",
]

STUBS = """
let _id = 1;
function pushUndoState() {}
function renderLCD() { renderCount++; }
let renderCount = 0;
function syncBackendExpression() {}
function getParent() { return null; }
const appState = {
  insertMode: false, error: null, result: null, resultDisplayed: false,
  lastAnswer: null, isFractionMode: false, base: 10, baseNBase: 10, undoStack: [],
  memoryValue: 0, hasMemory: false, settings: {
    numberFormat: 'Norm', numberFormatPrecision: 10, engineeringSymbols: false
  },
  resultPrecision: 10, approxMode: false
};
let rootSlot = null;
let cursor = { slot: null, index: 0 };
"""

ROUTER_ANCHOR = "if (rawKey === 'sto') {"
BRANCH_START = "if (rawKey === 'eng') {"
BRANCH_END = "if (rawKey === 'ac') {"


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


def eng_branch():
    anchor = FRONTEND.index(ROUTER_ANCHOR)
    start = FRONTEND.index(BRANCH_START, anchor)
    end = FRONTEND.index(BRANCH_END, start)
    return FRONTEND[start:end]


DRIVER = """
rootSlot = createSlot();
cursor = { slot: rootSlot, index: 0 };

function pressEng(mode) {
  const rawKey = 'eng';
  const isShift = (mode === 'shift');
  const action = (mode === 'shift') ? 'ENG_LEFT'
              : (mode === 'alpha') ? 'i' : null;
  const isAlpha = (mode === 'alpha');
__BRANCH__
}

function showResult(value) {
  appState.resultDisplayed = true;
  appState.result = value;
  appState.lastAnswer = value;
}

// seq: [op, arg]; ops = eng | shift_eng | alpha_eng | show | expr
function apply(step) {
  const op = step[0];
  if (op === 'eng') pressEng('plain');
  else if (op === 'shift_eng') pressEng('shift');
  else if (op === 'alpha_eng') pressEng('alpha');
  else if (op === 'show') showResult(step[1]);
  else if (op === 'localfmt') showResult(localFormat(step[1]));
  else if (op === 'expr') insertToken(step[1]);
  else throw new Error('unknown op ' + op);
}

const out = [];
for (const step of JSON.parse(process.argv[2])) {
  apply(step);
  out.push({ result: appState.result, lastAnswer: appState.lastAnswer,
             expr: serializeSlot(rootSlot),
             items: rootSlot.items.length, renders: renderCount });
}
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestEngKeyBehaviour(unittest.TestCase):
    """Drives the real ENG handler branch and helpers in node."""

    @classmethod
    def setUpClass(cls):
        parts = [STUBS]
        for name in ("nextId", "createSlot", "_cIsC"):
            m = re.search(rf"^  const {name} = .*$", FRONTEND, re.M)
            assert m, f"could not extract {name}"
            parts.append(m.group(0).strip())
        for name in FUNCTIONS:
            try:
                parts.append(extract_function(FRONTEND, name))
            except ValueError:
                m = re.search(rf"^  const {name} = .*$", FRONTEND, re.M)
                assert m, f"could not extract {name}"
                parts.append(m.group(0).strip())
        parts.append(DRIVER.replace("__BRANCH__", eng_branch()))
        cls.tmp = PROJECT / ".eng_test_tmp.js"
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

    def local_expect(self, value):
        """Render a value with the app's real localFormat (no hardcoding)."""
        return self.run_steps([["localfmt", value]])[-1]["result"]

    # 2. plain ENG unchanged

    def test_plain_eng_converts_result_to_engineering_notation(self):
        # Engineering notation: exponent a multiple of 3, mantissa in [1,1000).
        # 123400 -> 123.4×10^3 (NOT 1.234×10^5, which is scientific notation).
        snaps = self.run_steps([["show", "123400"], ["eng"]])
        self.assertEqual(snaps[-1]["result"], f"123.4{TIMES}10{EXP}3")

    def test_plain_eng_with_negative_exponent(self):
        snaps = self.run_steps([["show", "0.001234"], ["eng"]])
        self.assertEqual(snaps[-1]["result"], f"1.234{TIMES}10{EXP}-3")

    def test_plain_eng_is_a_noop_without_a_result(self):
        snaps = self.run_steps([["expr", "5"], ["eng"]])
        self.assertIsNone(snaps[-1]["result"])
        # ...and it must not have inserted anything either.
        self.assertEqual(snaps[-1]["items"], 1)

    # 3. SHIFT+ENG expands back

    def test_shift_eng_expands_engineering_notation(self):
        # BUG-06: this used to insert '<' and always produce Math ERROR.
        snaps = self.run_steps([["show", f"1.234{TIMES}10{EXP}5"], ["shift_eng"]])
        self.assertEqual(snaps[-1]["result"], "123400")

    def test_shift_eng_round_trip(self):
        snaps = self.run_steps([["show", "123400"], ["eng"], ["shift_eng"]])
        self.assertEqual(snaps[-1]["result"], "123400")

    def test_shift_eng_negative_exponent(self):
        # The value is expanded numerically, then re-rendered by localFormat.
        # localFormat (untouched, pre-existing) shows |v| < 1e-2 in exponential
        # form, so a tiny expansion is displayed that way again - that is the
        # app's display policy, not an ENG regression.
        snaps = self.run_steps([["show", f"1.234{TIMES}10{EXP}-3"], ["shift_eng"]])
        self.assertEqual(snaps[-1]["result"], self.local_expect(0.001234))

    def test_shift_eng_expands_negative_value(self):
        snaps = self.run_steps([["show", f"-2.5{TIMES}10{EXP}4"], ["shift_eng"]])
        self.assertEqual(snaps[-1]["result"], "-25000")

    def test_shift_eng_updates_last_answer(self):
        snaps = self.run_steps([["show", f"2{TIMES}10{EXP}6"], ["shift_eng"]])
        self.assertEqual(snaps[-1]["lastAnswer"], snaps[-1]["result"])
        self.assertEqual(snaps[-1]["result"], "2000000")

    def test_shift_eng_is_noop_on_plain_number(self):
        snaps = self.run_steps([["show", "42"], ["shift_eng"]])
        self.assertEqual(snaps[-1]["result"], "42")

    def test_shift_eng_without_a_result_does_nothing(self):
        snaps = self.run_steps([["expr", "7"], ["shift_eng"]])
        self.assertIsNone(snaps[-1]["result"])
        self.assertEqual(snaps[-1]["items"], 1)

    # 4. no entry token may be inserted

    def test_shift_eng_inserts_nothing_into_the_entry(self):
        steps = [["expr", "3"], ["expr", "0"], ["shift_eng"]]
        snaps = self.run_steps(steps)
        self.assertEqual(snaps[-1]["items"], 2)
        self.assertEqual(snaps[-1]["expr"], "30")

    def test_shift_eng_never_produces_the_bracket_token(self):
        for steps in ([["show", f"1{TIMES}10{EXP}3"], ["shift_eng"]],
                      [["show", "5"], ["shift_eng"]],
                      [["shift_eng"]]):
            snaps = self.run_steps(steps)
            for snap in snaps:
                self.assertNotIn("<", snap["expr"])
                self.assertNotIn("<", str(snap["result"]))

    def test_handler_no_longer_inserts_the_bracket(self):
        branch = eng_branch()
        self.assertIn("expandEngNotation(); return;", branch)
        self.assertNotIn("insertToken('<'); return;", branch)

    # 5. regression

    def test_alpha_eng_still_inserts_imaginary_unit(self):
        snaps = self.run_steps([["expr", "3"], ["alpha_eng"]])
        self.assertEqual(snaps[-1]["expr"], "3i")

    def test_expand_output_is_valid_backend_input(self):
        # The expanded value feeds the backend like any other numeric result.
        snaps = self.run_steps([["show", f"1.5{TIMES}10{EXP}3"], ["shift_eng"]])
        expanded = snaps[-1]["result"]
        self.assertAlmostEqual(ev(expanded, 0.0, "Degree", None), 1500.0)

    def test_scientific_key_still_inserts_scale_token(self):
        snaps = self.run_steps([["expr", f"2{TIMES}10{EXP}"]])
        self.assertEqual(snaps[-1]["expr"], f"2*10{EXP}")
        self.assertAlmostEqual(ev("2*10^3", 0.0, "Degree", None), 2000.0)

    def test_powers_unaffected(self):
        self.assertAlmostEqual(ev("2^10", 0.0, "Degree", None), 1024.0)
        self.assertAlmostEqual(ev("3*10^2", 0.0, "Degree", None), 300.0)


if __name__ == "__main__":
    unittest.main()
