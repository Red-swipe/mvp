"""Focused regression tests for safe_evaluate_expression correctness fixes.

Runs two ways:

* Under pytest / unittest - one test method per regression case (13 total), so
  each case reports pass/fail independently.
* As a direct script - ``python test_safe_eval_regressions.py`` keeps the
  original ``[PASS]`` / ``[FAIL]`` report and exits non-zero on failure.

Note: this module must stay importable. Executing ``sys.exit()`` at module
scope aborts pytest collection with an INTERNALERROR, so all script-only
behaviour lives behind the ``if __name__ == "__main__":`` guard at the bottom.
"""
import math
import pathlib
import sys
import unittest

# Derive the repository root from this file so the module imports the same way
# from any checkout location (the previous hardcoded E:\\A.G\\casio_mvp path
# only worked on one machine). Not strictly required under pytest's default
# "prepend" import mode, but it keeps direct script execution independent of
# the working directory.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from mvp_server import CONTROLLER, CONTROLLER_LOCK, safe_evaluate_expression

# (name, passed, detail) for each case, in execution order. Used to reproduce
# the original console report when run as a script.
_RESULTS = []


def check(name, condition, detail=""):
    """Record a case result and fail loudly if it did not pass.

    The original script only appended failures to a list and signalled through
    the process exit code, so a failing case was easy to miss. Raising here
    makes every case a real, independently reported assertion while keeping
    the recorded result for the script-mode report.
    """
    ok = bool(condition)
    _RESULTS.append((name, ok, detail))
    if not ok:
        raise AssertionError(f"{name}: {detail}" if detail else name)


def reset_controller():
    with CONTROLLER_LOCK:
        CONTROLLER.expression = ""
        CONTROLLER.cursor_position = 0
        CONTROLLER.last_result = None
        CONTROLLER.result_displayed = False
        CONTROLLER.state = "INPUT"
        CONTROLLER.ans = "0"
        CONTROLLER.shift = False
        CONTROLLER.alpha = False


class TestSafeEvalRegressions(unittest.TestCase):
    # --- Issue 1: no false division-by-zero pre-check ---

    def test_one_over_half_is_two(self):
        r = safe_evaluate_expression("1/0.5")
        check("1/0.5 = 2", abs(r - 2.0) < 1e-12, repr(r))

    def test_one_over_parenthesised_one(self):
        r = safe_evaluate_expression("1/(0+1)")
        check("1/(0+1) = 1", abs(r - 1.0) < 1e-12, repr(r))

    def test_five_over_zero_raises(self):
        try:
            safe_evaluate_expression("5/0")
        except ZeroDivisionError:
            check("5/0 raises ZeroDivisionError", True)
            return
        except Exception as exc:
            check("5/0 raises ZeroDivisionError", False, repr(exc))
            return
        check("5/0 raises ZeroDivisionError", False)

    # --- Issue 2: nested parentheses / top-level argument splitting ---

    def test_sqrt_nested_parens(self):
        r = safe_evaluate_expression("sqrt((2+3))")
        check("sqrt((2+3)) ~ 2.2360679", abs(r - math.sqrt(5)) < 1e-9, repr(r))

    def test_log_base_nested_parens(self):
        r = safe_evaluate_expression("log_base(2,(8))")
        check("log_base(2,(8)) = 3", abs(r - 3.0) < 1e-9, repr(r))

    def test_xroot_nested_parens(self):
        r = safe_evaluate_expression("xroot(3,(8))")
        check("xroot(3,(8)) = 2", abs(r - 2.0) < 1e-9, repr(r))

    def test_integral_nested(self):
        r = safe_evaluate_expression("integral(sqrt(x),0,1)")
        check("integral(sqrt(x),0,1) ~ 0.6666667",
              abs(r - 2.0 / 3.0) < 1e-3, repr(r))

    def test_nested_special_functions(self):
        r = safe_evaluate_expression("sqrt(log_base(2,8))")
        check("sqrt(log_base(2,8)) ~ 1.7320508",
              abs(r - math.sqrt(3)) < 1e-9, repr(r))

    # --- Basic evaluation still works ---

    def test_basic_addition(self):
        r = safe_evaluate_expression("1+1")
        check("1+1 = 2", abs(r - 2.0) < 1e-12, repr(r))

    def test_basic_exponent(self):
        r = safe_evaluate_expression("2^3")
        check("2^3 = 8", abs(r - 8.0) < 1e-12, repr(r))

    def test_basic_sine(self):
        r = safe_evaluate_expression("sin(0)")
        check("sin(0) = 0", abs(r) < 1e-12, repr(r))

    # --- Issue 3: controller equals path shows the custom div-zero message ---

    def test_controller_div_zero_message(self):
        reset_controller()
        resp = CONTROLLER.press_key({"key": "equals", "expression": "5/0"})
        check("controller 5/0 -> To infinity and beyonddd",
              resp.get("error") == "To infinity and beyonddd" and resp.get("display") == "To infinity and beyonddd",
              repr((resp.get("error"), resp.get("display"))))

    def test_controller_evaluates_nonzero_denominator(self):
        reset_controller()
        resp = CONTROLLER.press_key({"key": "equals", "expression": "1/(0+1)"})
        check("controller 1/(0+1) = 1", resp.get("result") == "1",
              repr(resp.get("result")))


# Original script order, so the direct-execution report stays grouped by issue.
# (unittest derives test order from dir(), which is alphabetical, so the
# script path builds its suite explicitly. Pytest collects in its own order and
# does not use this.)
_SCRIPT_ORDER = (
    "test_one_over_half_is_two",
    "test_one_over_parenthesised_one",
    "test_five_over_zero_raises",
    "test_sqrt_nested_parens",
    "test_log_base_nested_parens",
    "test_xroot_nested_parens",
    "test_integral_nested",
    "test_nested_special_functions",
    "test_basic_addition",
    "test_basic_exponent",
    "test_basic_sine",
    "test_controller_div_zero_message",
    "test_controller_evaluates_nonzero_denominator",
)


def _run_as_script():
    declared = {n for n in dir(TestSafeEvalRegressions)
                if n.startswith("test")}
    missing = declared - set(_SCRIPT_ORDER)
    if missing:
        raise RuntimeError(
            f"_SCRIPT_ORDER is out of date, missing: {sorted(missing)}")
    suite = unittest.TestSuite(
        TestSafeEvalRegressions(name) for name in _SCRIPT_ORDER)
    result = unittest.TestResult()
    suite.run(result)
    for name, ok, detail in _RESULTS:
        line = f"  [{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += ": " + str(detail)
        print(line)
    total = len(_RESULTS)
    passed = sum(1 for _n, ok, _d in _RESULTS if ok)
    print()
    print(f"TOTAL: {passed}/{total} passed")
    return 0 if not (result.failures or result.errors) and passed == total else 1


if __name__ == "__main__":
    sys.exit(_run_as_script())
