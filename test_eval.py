import json
import sys
sys.path.insert(0, '.')
from mvp_server import CONTROLLER, CONTROLLER_LOCK

# Test safe_evaluate_expression directly
from mvp_server import safe_evaluate_expression

# Test 1+1
try:
    result = safe_evaluate_expression("1+1", 0.0)
    print(f"safe_evaluate_expression('1+1', 0.0) = {result}")
except Exception as e:
    print(f"safe_evaluate_expression('1+1', 0.0) ERROR: {e}")

# Test 2*3
try:
    result = safe_evaluate_expression("2*3", 0.0)
    print(f"safe_evaluate_expression('2*3', 0.0) = {result}")
except Exception as e:
    print(f"safe_evaluate_expression('2*3', 0.0) ERROR: {e}")

# Test 10/2
try:
    result = safe_evaluate_expression("10/2", 0.0)
    print(f"safe_evaluate_expression('10/2', 0.0) = {result}")
except Exception as e:
    print(f"safe_evaluate_expression('10/2', 0.0) ERROR: {e}")

# Now test the full press_key flow
print("\n--- Testing press_key ---")

# Reset controller
with CONTROLLER_LOCK:
    CONTROLLER.expression = ""
    CONTROLLER.cursor_position = 0
    CONTROLLER.last_result = None
    CONTROLLER.result_displayed = False
    CONTROLLER.state = "INPUT"
    CONTROLLER.ans = "0"
    CONTROLLER.shift = False
    CONTROLLER.alpha = False

# Test pressing 1, +, 1, =
payloads = [
    {"key": "1"},
    {"key": "plus"},  # or "multiply" depending on shift
    {"key": "1"},
    {"key": "equals", "expression": "1+1"},
]

for payload in payloads:
    with CONTROLLER_LOCK:
        # Reset for each test
        CONTROLLER.expression = ""
        CONTROLLER.cursor_position = 0
        CONTROLLER.last_result = None
        CONTROLLER.result_displayed = False
        CONTROLLER.state = "INPUT"
        CONTROLLER.ans = "0"
        CONTROLLER.shift = False
        CONTROLLER.alpha = False
    
    try:
        response = CONTROLLER.press_key(payload)
        print(f"press_key({payload}) => ok={response.get('ok')}, state={response.get('state')}, display={response.get('display')}, error={response.get('error')}")
    except Exception as e:
        print(f"press_key({payload}) ERROR: {e}")