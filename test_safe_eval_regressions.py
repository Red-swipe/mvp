"""Focused regression tests for safe_evaluate_expression correctness fixes."""
import math
import sys

sys.path.insert(0, r'E:\A.G\casio_mvp')

from mvp_server import CONTROLLER, CONTROLLER_LOCK, safe_evaluate_expression

passed = 0
failures = []


def check(name, condition, detail=""):
    global passed
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if detail:
        msg += ": " + str(detail)
    print(msg)
    if condition:
        passed += 1
    else:
        failures.append(name)


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


# --- Issue 1: no false division-by-zero pre-check ---
r = safe_evaluate_expression("1/0.5")
check("1/0.5 = 2", abs(r - 2.0) < 1e-12, repr(r))

r = safe_evaluate_expression("1/(0+1)")
check("1/(0+1) = 1", abs(r - 1.0) < 1e-12, repr(r))

try:
    safe_evaluate_expression("5/0")
    check("5/0 raises ZeroDivisionError", False)
except ZeroDivisionError:
    check("5/0 raises ZeroDivisionError", True)
except Exception as exc:
    check("5/0 raises ZeroDivisionError", False, repr(exc))

# --- Issue 2: nested parentheses / top-level argument splitting ---
r = safe_evaluate_expression("sqrt((2+3))")
check("sqrt((2+3)) ~ 2.2360679", abs(r - math.sqrt(5)) < 1e-9, repr(r))

r = safe_evaluate_expression("log_base(2,(8))")
check("log_base(2,(8)) = 3", abs(r - 3.0) < 1e-9, repr(r))

r = safe_evaluate_expression("xroot(3,(8))")
check("xroot(3,(8)) = 2", abs(r - 2.0) < 1e-9, repr(r))

r = safe_evaluate_expression("integral(sqrt(x),0,1)")
check("integral(sqrt(x),0,1) ~ 0.6666667", abs(r - 2.0 / 3.0) < 1e-3, repr(r))

# Nested special functions inside arguments
r = safe_evaluate_expression("sqrt(log_base(2,8))")
check("sqrt(log_base(2,8)) ~ 1.7320508", abs(r - math.sqrt(3)) < 1e-9, repr(r))

# --- Basic evaluation still works ---
r = safe_evaluate_expression("1+1")
check("1+1 = 2", abs(r - 2.0) < 1e-12, repr(r))

r = safe_evaluate_expression("2^3")
check("2^3 = 8", abs(r - 8.0) < 1e-12, repr(r))

r = safe_evaluate_expression("sin(0)")
check("sin(0) = 0", abs(r) < 1e-12, repr(r))

# --- Issue 3: controller equals path shows the custom div-zero message ---
reset_controller()
resp = CONTROLLER.press_key({"key": "equals", "expression": "5/0"})
check("controller 5/0 -> To infinity and beyonddd",
      resp.get("error") == "To infinity and beyonddd" and resp.get("display") == "To infinity and beyonddd",
      repr((resp.get("error"), resp.get("display"))))

reset_controller()
resp = CONTROLLER.press_key({"key": "equals", "expression": "1/(0+1)"})
check("controller 1/(0+1) = 1", resp.get("result") == "1", repr(resp.get("result")))

print()
print(f"TOTAL: {passed}/{passed + len(failures)} passed")
sys.exit(0 if not failures else 1)
