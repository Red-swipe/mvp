"""State-machine regression tests for calculator input handling.

Covers the frontend screen-state contract (EMPTY / EDITING / RESULT / ERROR),
modifier handling, Ans chaining, and MatAns/VctAns separation — without
enumerating every button combination.

Two layers:
1. Pure JS state functions extracted from frontend.html and executed in node
   (mirrors test_frontend_fixture.py's displayFormat approach).
2. Backend Ans contract (scalar chaining + matrix/vector separation) via
   CONTROLLER.press_key — guards that the math engine was not refactored.
3. Frontend wiring guards: AC/DEL/modifier/editing keys must not reach
   prepareExpressionForEvaluation() or /api/key; '=' only evaluates with a
   valid calculation context.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
FRONTEND = (PROJECT / "frontend.html").read_text(encoding="utf-8")

# Pure state-machine functions that MUST exist in frontend.html (single source
# of truth for interaction state). They are intentionally pure (explicit args,
# no DOM) so they can be extracted and executed in node.
REQUIRED_FNS = [
    "getScreenState",
    "shouldEvaluateScreen",
    "calcTokenKind",
    "routeResultInput",
    "routeErrorInput",
]


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


def run_node_state_cases(cases):
    """Run pure state-machine cases in node.

    cases: list of dicts {fn, args}. Returns list of results.
    """
    fns = "\n".join(extract_function(FRONTEND, n) for n in REQUIRED_FNS)
    runner = (
        fns
        + "\nconst cases=JSON.parse(process.argv[2]);const out=[];"
        + "for(const c of cases){"
        + "  if(c.fn==='getScreenState')out.push(getScreenState(c.arg));"
        + "  else if(c.fn==='shouldEvaluateScreen')out.push(shouldEvaluateScreen(c.arg));"
        + "  else if(c.fn==='calcTokenKind')out.push(calcTokenKind(c.arg));"
        + "  else if(c.fn==='routeResultInput')out.push(routeResultInput(c.arg,c.hasAns));"
        + "  else if(c.fn==='routeErrorInput')out.push(routeErrorInput(c.arg));"
        + "}"
        + "process.stdout.write(JSON.stringify(out));\n"
    )
    tmp = PROJECT / ".state_test_tmp.js"
    tmp.write_text(runner, encoding="utf-8")
    try:
        proc = subprocess.run(
            ["node", str(tmp), json.dumps(cases)],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    finally:
        tmp.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr[:500]
    return json.loads(proc.stdout)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestScreenStates(unittest.TestCase):
    def test_required_functions_exist(self):
        for name in REQUIRED_FNS:
            self.assertIn(f"function {name}(", FRONTEND, name)

    def test_empty_editing_result_error(self):
        cases = [
            {"fn": "getScreenState", "arg": {"error": None, "resultDisplayed": False, "expr": ""}},
            {"fn": "getScreenState", "arg": {"error": None, "resultDisplayed": False, "expr": "7"}},
            {"fn": "getScreenState", "arg": {"error": None, "resultDisplayed": False, "expr": "7+2"}},
            {"fn": "getScreenState", "arg": {"error": None, "resultDisplayed": True, "expr": "7+2"}},
            {"fn": "getScreenState", "arg": {"error": "Math ERROR", "resultDisplayed": False, "expr": "1/0"}},
        ]
        got = run_node_state_cases(cases)
        self.assertEqual(got, ["EMPTY", "EDITING", "EDITING", "RESULT", "ERROR"])

    def test_empty_never_evaluates(self):
        cases = [
            {"fn": "shouldEvaluateScreen", "arg": {"error": None, "resultDisplayed": False, "expr": ""}},
            {"fn": "shouldEvaluateScreen", "arg": {"error": None, "resultDisplayed": False, "expr": "   "}},
            {"fn": "shouldEvaluateScreen", "arg": {"error": None, "resultDisplayed": False, "expr": "7+2"}},
            {"fn": "shouldEvaluateScreen", "arg": {"error": None, "resultDisplayed": True, "expr": "9"}},
            {"fn": "shouldEvaluateScreen", "arg": {"error": "Math ERROR", "resultDisplayed": False, "expr": "1/0"}},
        ]
        got = run_node_state_cases(cases)
        self.assertEqual(got, [False, False, True, False, False])

    def test_modifiers_never_evaluate(self):
        cases = [
            {"fn": "calcTokenKind", "arg": "shift"},
            {"fn": "calcTokenKind", "arg": "alpha"},
            {"fn": "calcTokenKind", "arg": "SHIFT+7"},
        ]
        got = run_node_state_cases(cases)
        for kind in got:
            self.assertEqual(kind, "modifier")

    def test_result_routing(self):
        cases = [
            {"fn": "routeResultInput", "arg": "number", "hasAns": True},
            {"fn": "routeResultInput", "arg": "operator", "hasAns": True},
            {"fn": "routeResultInput", "arg": "ans", "hasAns": True},
            {"fn": "routeResultInput", "arg": "ac", "hasAns": True},
            {"fn": "routeResultInput", "arg": "del", "hasAns": True},
            {"fn": "routeResultInput", "arg": "equals", "hasAns": True},
            {"fn": "routeResultInput", "arg": "modifier", "hasAns": True},
        ]
        got = run_node_state_cases(cases)
        # number/ans start fresh, operator continues from result, AC clears,
        # DEL edits, bare equals/modifier never re-evaluate the old result.
        self.assertEqual(got[0], "fresh")
        self.assertEqual(got[1], "continue")
        self.assertEqual(got[2], "fresh")
        self.assertEqual(got[3], "clear")
        self.assertEqual(got[4], "edit")
        self.assertEqual(got[5], "ignore")
        self.assertEqual(got[6], "ignore")

    def test_error_routing_never_cascades(self):
        cases = [
            {"fn": "routeErrorInput", "arg": "number"},
            {"fn": "routeErrorInput", "arg": "operator"},
            {"fn": "routeErrorInput", "arg": "ans"},
            {"fn": "routeErrorInput", "arg": "ac"},
            {"fn": "routeErrorInput", "arg": "del"},
            {"fn": "routeErrorInput", "arg": "equals"},
            {"fn": "routeErrorInput", "arg": "modifier"},
        ]
        got = run_node_state_cases(cases)
        # AC/DEL clear the error context; number/ans start fresh; operator may
        # continue from the last good Ans but must NEVER re-evaluate the
        # erroneous expression; bare equals/modifier are ignored.
        self.assertEqual(got[3], "clear")
        self.assertEqual(got[4], "clear")
        self.assertEqual(got[0], "fresh")
        self.assertEqual(got[5], "ignore")
        self.assertEqual(got[6], "ignore")
        self.assertIn(got[1], ("fresh", "continue"))
        self.assertIn(got[2], ("fresh", "continue"))


class TestFrontendWiring(unittest.TestCase):
    """AC/DEL/modifiers/editing keys are UI actions: they must be handled by
    the frontend state machine and must not reach prepareExpressionForEvaluation
    or /api/key unless a real calculation is required."""

    def test_evaluate_guards_empty(self):
        # evaluate() must consult the screen state before touching the
        # evaluator or the network.
        idx = FRONTEND.find("async function evaluate()")
        self.assertGreaterEqual(idx, 0, "evaluate() not found")
        body = FRONTEND[idx:idx + 2000]
        self.assertTrue(
            ("shouldEvaluateNow" in body) or ("shouldEvaluateScreen" in body)
            or ("getScreenState" in body),
            "evaluate() must guard on screen state (EMPTY/= must be a no-op)",
        )
        self.assertNotIn("appState.result = '0'", body,
                         "empty '=' must not fabricate a '0' result")

    def test_ac_is_ui_action_in_calculate(self):
        # The Calculate-mode AC path must reset local state and render without
        # POSTing to /api/key and without preparing an expression.
        idx = FRONTEND.find("if (rawKey === 'ac') { closeOptnPanel();")
        self.assertGreaterEqual(idx, 0, "Calculate AC path not found")
        snippet = FRONTEND[idx:idx + 400]
        self.assertNotIn("backendKey", snippet,
                         "AC must not reach /api/key")
        self.assertNotIn("prepareExpressionForEvaluation", snippet,
                         "AC must not reach the evaluator")

    def test_editing_sync_does_not_evaluate(self):
        # Per-keystroke backend sync (input_sync) keeps a second competing
        # state system alive in the backend and must be gone: the backend is
        # a stateless math engine, the frontend owns input state.
        self.assertNotIn("input_sync", FRONTEND,
                         "input_sync must be removed; editing keys stay local")

    def test_reset_preserves_ans(self):
        # resetExpr() clears the entry but MUST preserve lastAnswer (Ans).
        # A separate hard reset covers power-on / Initialize-All.
        m = re.search(r"function resetExpr\(\) \{([\s\S]{0,600}?)\n  \}", FRONTEND)
        self.assertIsNotNone(m, "resetExpr() not found")
        body = m.group(0)
        self.assertNotIn("lastAnswer = null", body,
                         "resetExpr must preserve Ans; use hardResetExpr to clear")
        self.assertIn("function hardResetExpr(", FRONTEND,
                      "hardResetExpr() required for power-on / Initialize-All")

    def test_scalar_ans_not_clobbered_by_matvec(self):
        # Matrix/vector results must land in MatAns/VctAns, never overwrite
        # the scalar Ans register.
        self.assertTrue(
            ("matAns" in FRONTEND) or ("MatAns" in FRONTEND)
            or ("mat_ans" in FRONTEND),
            "frontend must track a separate matrix answer register",
        )


class TestBackendAnsContract(unittest.TestCase):
    """The math engine is a black box: scalar Ans chaining and MatAns/VctAns
    separation must keep working exactly as before."""

    def _fresh_controller(self):
        from mvp_server import CONTROLLER, CONTROLLER_LOCK
        with CONTROLLER_LOCK:
            CONTROLLER.expression = ""
            CONTROLLER.cursor_position = 0
            CONTROLLER.last_result = None
            CONTROLLER.result_displayed = False
            CONTROLLER.state = "INPUT"
            CONTROLLER.ans = "0"
            CONTROLLER.shift = False
            CONTROLLER.alpha = False
        return CONTROLLER

    def test_ans_chain(self):
        c = self._fresh_controller()
        r1 = c.press_key({"key": "equals", "expression": "2+3"})
        self.assertEqual(r1.get("result"), "5")
        r2 = c.press_key({"key": "equals", "expression": "Ans+4"})
        self.assertEqual(r2.get("result"), "9")
        r3 = c.press_key({"key": "equals", "expression": "Ans*2"})
        self.assertEqual(r3.get("result"), "18")

    def test_ac_preserves_ans(self):
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        c.press_key({"key": "ac"})
        r = c.press_key({"key": "equals", "expression": "Ans+1"})
        self.assertEqual(r.get("result"), "6")

    def test_matvec_does_not_clobber_scalar_ans(self):
        from mvp_server import CONTROLLER_LOCK
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        self.assertEqual(c.ans, "5")
        with CONTROLLER_LOCK:
            c.matrices["A"] = {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]}
            c.matrices["B"] = {"rows": 2, "cols": 2, "data": [[5, 6], [7, 8]]}
        r = c.press_key({"key": "equals", "expression": "MatA+MatB"})
        self.assertIsNotNone(r.get("result"))
        self.assertEqual(c.ans, "5",
                         "matrix answers must live in MatAns, not scalar Ans")


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestRegisterIsolationFrontend(unittest.TestCase):
    """storeCalcAnswer() must keep scalar Ans, MatAns and VctAns separate.

    Executes the real functions extracted from frontend.html in node against
    a fake appState. Mirrors the manual audit: scalar 2+3=5, then a matrix
    result, then a vector result — scalar Ans must survive each step.
    """

    def _run_store_sequence(self, steps):
        fns = "\n".join(
            extract_function(FRONTEND, n)
            for n in ("isMatVecResultString", "storeCalcAnswer")
        )
        runner = (
            fns
            + "\nconst steps=JSON.parse(process.argv[2]);"
            + "const appState={result:null,resultDisplayed:false,error:null,"
            + "lastAnswer:null,matAns:null,vctAns:null};"
            + "for(const s of steps){storeCalcAnswer(s.result,s.expr);}"
            + "process.stdout.write(JSON.stringify(appState));\n"
        )
        tmp = PROJECT / ".store_test_tmp.js"
        tmp.write_text(runner, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["node", str(tmp), json.dumps(steps)],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
        finally:
            tmp.unlink(missing_ok=True)
        assert proc.returncode == 0, proc.stderr[:500]
        return json.loads(proc.stdout)

    def test_scalar_ans_survives_matrix_calculation(self):
        st = self._run_store_sequence([
            {"result": "5", "expr": "2+3"},
            {"result": "[[6,8],[10,12]]", "expr": "MatA+MatB"},
        ])
        self.assertEqual(st["lastAnswer"], "5")
        self.assertEqual(st["matAns"], "[[6,8],[10,12]]")
        self.assertIsNone(st["vctAns"])

    def test_scalar_ans_survives_vector_calculation(self):
        st = self._run_store_sequence([
            {"result": "5", "expr": "2+3"},
            {"result": "[4,6]", "expr": "VctA+VctB"},
        ])
        self.assertEqual(st["lastAnswer"], "5")
        self.assertEqual(st["vctAns"], "[4,6]")
        self.assertIsNone(st["matAns"])

    def test_scalar_after_matvec_preserves_registers(self):
        st = self._run_store_sequence([
            {"result": "[[6,8],[10,12]]", "expr": "MatA+MatB"},
            {"result": "[4,6]", "expr": "VctA+VctB"},
            {"result": "11", "expr": "10+1"},
        ])
        self.assertEqual(st["lastAnswer"], "11")
        self.assertEqual(st["matAns"], "[[6,8],[10,12]]")
        self.assertEqual(st["vctAns"], "[4,6]")

    def test_mixed_mat_vct_never_touches_scalar_ans(self):
        st = self._run_store_sequence([
            {"result": "5", "expr": "2+3"},
            {"result": "[[1,2]]", "expr": "MatA+VctA"},
        ])
        self.assertEqual(st["lastAnswer"], "5")

    def test_scalar_expr_without_markers_never_touches_matvec(self):
        # A scalar typed while Matrix/Vector calc phase is open carries no
        # Mat/Vct markers, so MatAns/VctAns must be left alone.
        st = self._run_store_sequence([
            {"result": "[[6,8],[10,12]]", "expr": "MatA+MatB"},
            {"result": "7", "expr": "3+4"},
        ])
        self.assertEqual(st["lastAnswer"], "7")
        self.assertEqual(st["matAns"], "[[6,8],[10,12]]")


class TestCalcSolveWiring(unittest.TestCase):
    """CALC/SOLVE are distinct state-gated evaluations, not bare '='.

    There is no intermediate variable-prompt state in the current design:
    CALC substitutes stored variables and SOLVE uses the stored X guess
    (documented substitute-and-evaluate simplification). These guards pin
    the actual contract: EDITING-only entry, shared register store,
    clean RESULT/ERROR transitions, no stale prompt possible.
    """

    def _body(self, marker, length=2600):
        idx = FRONTEND.find(marker)
        self.assertGreaterEqual(idx, 0, f"{marker} not found")
        return FRONTEND[idx:idx + length]

    def test_do_calc_guards_editing_state(self):
        body = self._body("async function doCalc()")
        self.assertIn("shouldEvaluateNow", body,
                      "doCalc must be EDITING-gated like evaluate()")

    def test_do_solve_guards_editing_state(self):
        body = self._body("async function doSolve()")
        self.assertIn("shouldEvaluateNow", body,
                      "doSolve must be EDITING-gated like evaluate()")

    def test_do_calc_routes_registers(self):
        body = self._body("async function doCalc()")
        self.assertIn("storeCalcAnswer", body,
                      "doCalc must share the register store (CALC on a "
                      "matrix expression must reach MatAns, not scalar Ans)")

    def test_do_solve_routes_registers(self):
        body = self._body("async function doSolve()")
        self.assertIn("storeCalcAnswer", body,
                      "doSolve must share the register store")
        self.assertIn("isMatVecResultString", body,
                      "doSolve display path must defend the 'X=' form")

    def test_backend_sync_is_register_aware(self):
        idx = FRONTEND.find("FIX 3: if backend returned a reconverted result")
        self.assertGreaterEqual(idx, 0, "backendKey result sync not found")
        snippet = FRONTEND[idx:idx + 1200]
        self.assertIn("isMatVecResultString", snippet,
                      "backendKey sync must not blindly overwrite scalar Ans "
                      "with a matrix/vector payload")

    def test_approx_guards_editing_state(self):
        body = self._body("async function evaluateApprox()")
        self.assertIn("shouldEvaluateNow", body,
                      "evaluateApprox must be EDITING-gated")


class TestBackendRegisterLifetime(unittest.TestCase):
    """Backend register lifetime: isolation, CALC/SOLVE, AC persistence."""

    def _fresh_controller(self):
        from mvp_server import CONTROLLER, CONTROLLER_LOCK
        with CONTROLLER_LOCK:
            CONTROLLER.expression = ""
            CONTROLLER.cursor_position = 0
            CONTROLLER.last_result = None
            CONTROLLER.result_displayed = False
            CONTROLLER.state = "INPUT"
            CONTROLLER.ans = "0"
            CONTROLLER.ans_matrix = None
            CONTROLLER.ans_vector = None
            CONTROLLER.variables = {k: 0 for k in
                                    ("A", "B", "C", "D", "E", "F", "M", "X", "Y")}
        return CONTROLLER

    def _seed_matrices(self, c):
        from mvp_server import CONTROLLER_LOCK
        with CONTROLLER_LOCK:
            c.matrices["A"] = {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]}
            c.matrices["B"] = {"rows": 2, "cols": 2, "data": [[5, 6], [7, 8]]}

    def _seed_vectors(self, c):
        from mvp_server import CONTROLLER_LOCK
        with CONTROLLER_LOCK:
            c.vectors["A"] = {"dim": 2, "data": [1, 2]}
            c.vectors["B"] = {"dim": 2, "data": [3, 4]}

    def test_vector_result_preserves_scalar_ans(self):
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        self._seed_vectors(c)
        r = c.press_key({"key": "equals", "expression": "VctA+VctB"})
        self.assertEqual(r.get("result"), "[4,6]")
        self.assertEqual(c.ans, "5")
        self.assertEqual(c.ans_vector, "[4,6]")
        self.assertIsNone(c.ans_matrix)

    def test_matvec_registers_stay_independent(self):
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        self._seed_matrices(c)
        self._seed_vectors(c)
        c.press_key({"key": "equals", "expression": "MatA+MatB"})
        c.press_key({"key": "equals", "expression": "VctA+VctB"})
        self.assertEqual(c.ans, "5")
        self.assertEqual(c.ans_matrix, "[[6,8],[10,12]]")
        self.assertEqual(c.ans_vector, "[4,6]")

    def test_calc_preserves_matvec_registers(self):
        from mvp_server import CONTROLLER_LOCK
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        self._seed_matrices(c)
        c.press_key({"key": "equals", "expression": "MatA+MatB"})
        with CONTROLLER_LOCK:
            c.variables["X"] = 5
        r = c.calc_evaluate("X+1")
        self.assertTrue(r.get("ok"))
        self.assertEqual(r.get("result"), "6")
        self.assertEqual(c.ans, "6")
        self.assertEqual(c.ans_matrix, "[[6,8],[10,12]]")

    def test_solve_preserves_matvec_registers(self):
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        self._seed_matrices(c)
        c.press_key({"key": "equals", "expression": "MatA+MatB"})
        r = c.solve_equation_newton("X+2=6", "X", 0)
        self.assertTrue(r.get("ok"))
        self.assertEqual(r.get("result"), "4")
        self.assertEqual(c.ans, "4")
        self.assertEqual(c.ans_matrix, "[[6,8],[10,12]]")

    def test_failed_solve_leaves_registers_intact(self):
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        r = c.solve_equation_newton("X*0=1", "X", 0)
        self.assertFalse(r.get("ok"))
        self.assertEqual(c.ans, "5")
        self.assertIsNone(c.ans_matrix)
        self.assertIsNone(c.ans_vector)

    def test_ac_preserves_all_registers(self):
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        self._seed_matrices(c)
        self._seed_vectors(c)
        c.press_key({"key": "equals", "expression": "MatA+MatB"})
        c.press_key({"key": "equals", "expression": "VctA+VctB"})
        c.press_key({"key": "ac"})
        self.assertEqual(c.ans, "5")
        self.assertEqual(c.ans_matrix, "[[6,8],[10,12]]")
        self.assertEqual(c.ans_vector, "[4,6]")

    def test_result_ac_ans_chain(self):
        c = self._fresh_controller()
        r1 = c.press_key({"key": "equals", "expression": "2+3"})
        self.assertEqual(r1.get("result"), "5")
        c.press_key({"key": "ac"})
        r2 = c.press_key({"key": "equals", "expression": "Ans+4"})
        self.assertEqual(r2.get("result"), "9")

    def test_result_ac_fresh_number_and_operator(self):
        # RESULT -> AC clears the entry context without corrupting Ans, so a
        # fresh number evaluates standalone and Ans still chains afterwards.
        c = self._fresh_controller()
        c.press_key({"key": "equals", "expression": "2+3"})
        c.press_key({"key": "ac"})
        r = c.press_key({"key": "equals", "expression": "7*2"})
        self.assertEqual(r.get("result"), "14")
        r2 = c.press_key({"key": "equals", "expression": "Ans+1"})
        self.assertEqual(r2.get("result"), "15")


if __name__ == "__main__":
    unittest.main()
