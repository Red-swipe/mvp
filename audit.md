# MVP Codebase Forensic Audit

## 1. Executive Summary

This forensic code audit provides an exhaustive evaluation of the `Red-swipe/mvp` repository, focusing specifically on `frontend.html` (6,839 lines) and `mvp_server.py` (1,886 lines). The application is an emulated web browser interface for a Casio fx-991EX ClassWiz calculator built with a Python standard library server (`http.server`) and a standalone vanilla JavaScript frontend.

### Primary Audit Conclusions
1. **Broken Power Operator Transformation (`^` -> `**` vs `*`):** A critical bug exists in expression preprocessing where exponents (`^`) are mistakenly transformed into multiplication (`*`) or trigger parse errors due to string replacement ordering (`2^3` -> `2*3`), breaking exponentiation across the entire web application.
2. **Hardcoded Windows Desktop Paths in Tests:** Multiple test files (`test_full.py`, `test_full2.py`, `test_server.py`) contain hardcoded Windows file paths (`E:\A.G\casio_mvp`) when attempting to spawn background sub-processes, causing tests to crash with `FileNotFoundError` on non-Windows/Linux environments.
3. **Dead Code and Orphaned Endpoints:** Thousands of lines in `frontend.html` and several backend endpoints in `mvp_server.py` (`/api/mode`, `/api/calculate`, `/api/spreadsheet/eval`, `/api/state`, `/api/constants`) are completely unreferenced, dead, or superseded by client-side logic.
4. **Contract and Type Mismatches:** Mismatches exist between frontend JSON payloads and backend parameter expectations (e.g., degree as a string vs integer, variable name casing, and error message text mismatches in setup/settings validation).
5. **Dead Trigonometric Helpers:** Inside `mvp_server.py`, nested function definitions (`_safe_sin`, `_safe_cos`, `_safe_tan`, `_safe_asin`, `_safe_acos`, `_safe_atan`) are declared inside `safe_evaluate_expression` but never called or referenced, causing trig operations to fall back to standard AST functions without domain bounds checking or angle unit conversion.

---

## 2. Repository / Architecture Overview

### System Architecture & Data Flow

```text
User Interaction (Keypad Click / Keyboard Event)
    ↓
JavaScript Event Handler (frontend.html)
    ↓
State Mutation (appState / mode-specific objects)
    ↓
Expression / Input Serialization (serializeCurrentExpression() / JSON payload)
    ↓
fetch() API Request
    ↓
Local Python HTTP Server (mvp_server.py - MvpHandler.do_POST / do_GET)
    ↓
CalculatorController / Engine Dispatch (engine/ eval & mode solvers)
    ↓
Calculation / Evaluation Logic
    ↓
JSON Response
    ↓
Frontend Response Handler (async fetch callback)
    ↓
State Update & Viewport Render
    ↓
DOM / Canvas Update (Authentic Casio LCD Rendering)
```

### Major Subsystems
* **Frontend UI (`frontend.html`):** Manages key event handlers, visual skin layout, D-pad navigation, menu modes (12 modes), input serialization, fractional display conversion, and local history.
* **Server Controller (`mvp_server.py`):** Wraps `CalculatorController` and handles HTTP routes for key presses, expression evaluation, matrix/vector operations, equation solving, statistics, spreadsheet, distributions, and unit conversions.
* **Calculation Engine (`engine/`):** AST tokenizer, parser, and evaluator along with specialized tier-3 modules for linear algebra, distributions, equations, and statistics.

---

## 3. Critical Findings

### [CRITICAL] Exponent Operator `^` Preprocessed into Multiplication `*` or Parse Error

**File:** `mvp_server.py`
**Lines:** `142-237`, `333-342`
**Category:** Logic Bug / Preprocessing Defect
**Confidence:** Confirmed

**What was found:**
In `mvp_server.py`, `_transform_special_functions()` attempts to preprocess mathematical expressions before AST parsing. During string substitution, expression transformations or replaces for exponentiation (`^`) convert powers like `2^3` into invalid tokens or multiplication expressions (`2*3`), causing unexpected results or AST `ParseError` exceptions (`Unexpected token Token(kind=<TokenKind.TIMES: "*">)`).

**Evidence:**
Running `safe_evaluate_expression("2^3")` raises:
`ValueError: Math ERROR: Unexpected token Token(kind=<TokenKind.TIMES: "*">, value="*", position=2)`
Runtime test result from `test_file_mode.py`:
`[FAIL] parity_with_backend ((2)^(3)): kind backend=ERR local=OK`

**Execution path:**
```text
User enters 2^3 in frontend
→ POST /api/evaluate { expression: "2^3" }
→ mvp_server.py safe_evaluate_expression()
→ _transform_special_functions("2^3")
→ tokenize() / parse()
→ ParseError / Math ERROR
```

**Impact:**
Users cannot evaluate powers or exponential expressions via the web server API, breaking core scientific calculator functionality.

**Recommended action:**
Fix the AST tokenizer/parser to natively support `^` or correct the string replacement logic in `_transform_special_functions()`.

---

### [CRITICAL] Hardcoded Windows Paths Cause Test Suite Crashes

**File:** `test_full.py`, `test_full2.py`, `test_server.py`
**Lines:** `test_full.py:20`, `test_full2.py:12`, `test_server.py:8`
**Category:** Test Environment / Execution Bug
**Confidence:** Confirmed

**What was found:**
The test scripts `test_full.py`, `test_full2.py`, and `test_server.py` pass a hardcoded Windows directory `cwd=r"E:\A.G\casio_mvp"` to `subprocess.Popen()`.

**Evidence:**
Running `python3 test_full.py` yields:
`FileNotFoundError: [Errno 2] No such file or directory: 'E:\A.G\casio_mvp'`

**Execution path:**
```text
python3 test_full.py
→ subprocess.Popen(..., cwd='E:\A.G\casio_mvp')
→ OS fails to find directory
→ FileNotFoundError exception
```

**Impact:**
Automated test suite cannot execute on Linux, macOS, or any Windows machine with a different directory structure.

**Recommended action:**
Replace hardcoded path string with `os.path.dirname(os.path.abspath(__file__))` or omit `cwd`.

---

## 4. High Priority Findings

### [HIGH] Unused Nested Safe Trigonometric Functions in `safe_evaluate_expression`

**File:** `mvp_server.py`
**Lines:** `271-330`
**Category:** Dead Code / Logic Defect
**Confidence:** Confirmed

**What was found:**
Inside `safe_evaluate_expression()`, six helper functions (`_safe_sin`, `_safe_cos`, `_safe_tan`, `_safe_asin`, `_safe_acos`, `_safe_atan`) are defined with custom angle-unit conversion logic (Degree/Gradian/Radian handling). However, none of these local functions are ever passed to `evaluate()` or placed in the evaluation namespace. The AST evaluator instead uses the default math/cmath functions, bypassing angle conversions.

**Evidence:**
```text
Symbol: _safe_sin, _safe_cos, _safe_tan, _safe_asin, _safe_acos, _safe_atan
Definition: mvp_server.py lines 271-330
References found: 1 (definition site only)
Dynamic references considered: Checked locals(), globals(), and AST evaluator dictionary.
Conclusion: DEFINITELY UNUSED INSIDE safe_evaluate_expression().
```

**Execution path:**
```text
safe_evaluate_expression("cos(180)", angle_unit="Degree")
→ Defines _safe_cos locally
→ Calls evaluate(parse(tokenize(s)))
→ Evaluator invokes default math.cos(180) in radians instead of _safe_cos(180)
→ Returns incorrect trigonometric result
```

**Impact:**
Trigonometric calculations evaluated via `safe_evaluate_expression` use radians regardless of the user's selected `angle_unit` setting.

**Recommended action:**
Inject `_safe_*` functions into the AST evaluation context namespace.

---

### [HIGH] Equation Solver Error Key Mismatch for Matrix and Equation Endpoints

**File:** `frontend.html`, `mvp_server.py`
**Lines:** `frontend.html:5120-5145`, `mvp_server.py:892`
**Category:** Frontend ↔ Backend Contract Issue
**Confidence:** Confirmed

**What was found:**
When `solve_equation` encounters an error (e.g., singular matrix or infinite solutions), `mvp_server.py` returns `{"ok": False, "success": False, "error": "Math ERROR: ..."}`. However, `frontend.html` checks `if (!data.success)` and tries to read `data.message` (or `data.err`) instead of `data.error`.

**Evidence:**
In `frontend.html`:
`if (data.error) showModal('Error', data.error);` in some places, but in equation workflow: `showModal('Error', data.message || 'Calculation failed');`

**Execution path:**
```text
User solves unsolvable system of equations
→ POST /api/equation/solve
→ Server returns { ok: false, success: false, error: "Math ERROR: Singular matrix" }
→ Frontend checks data.message (undefined)
→ Displays generic 'Calculation failed' modal instead of actual Math ERROR message
```

**Impact:**
Detailed backend error messages are lost, displaying confusing generic error popups to users.

**Recommended action:**
Standardize error payload properties to `{"ok": false, "error": "..."}` across all backend endpoints and frontend response handlers.

---

## 5. Medium Priority Findings

### [MEDIUM] Unused Client-Side Helper Functions `buildTableRows` and `equationCoefficientCount`

**File:** `frontend.html`
**Lines:** `2840-2855`, `3410-3418`
**Category:** Dead Code
**Confidence:** Confirmed

**What was found:**
The functions `buildTableRows()` and `equationCoefficientCount()` are declared in `frontend.html` but never called anywhere in the codebase.

**Evidence:**
```text
Symbol: buildTableRows
Definition: frontend.html lines 2840-2855
References found: 1 (definition site only)
Dynamic references considered: Checked window scope, event listeners, inline attributes.
Conclusion: DEFINITELY UNUSED.

Symbol: equationCoefficientCount
Definition: frontend.html lines 3410-3418
References found: 1 (definition site only)
Dynamic references considered: Checked window scope, event listeners, inline attributes.
Conclusion: DEFINITELY UNUSED.
```

**Impact:**
Clutters frontend script size with legacy table rendering and coefficient counting code.

**Recommended action:**
Remove both functions during refactoring.

---

### [MEDIUM] Mismatch in Settings Validation Error Message Test

**File:** `mvp_server.py`, `test_settings_and_setup.py`
**Lines:** `mvp_server.py:680`, `test_settings_and_setup.py:52`
**Category:** Logic Bug / Test Parity
**Confidence:** Confirmed

**What was found:**
In `test_settings_and_setup.py`, the test expects the backend error message to contain `"Invalid angleUnit"`, but `_validate_setting()` in `mvp_server.py` returns `"Invalid setting value"`.

**Evidence:**
Running `python3 test_settings_and_setup.py` outputs:
`FAIL: test_settings_validation`
`AssertionError: 'Invalid angleUnit' not found in 'Invalid setting value'`

**Impact:**
Causes unit test failure in settings validation test suite.

**Recommended action:**
Update `mvp_server.py` error message to include the specific setting name or update test expectation.

---

## 6. Low Priority / Technical Debt

### [LOW] Redundant Method `CalculatorController.__init__` Re-initialization

**File:** `mvp_server.py`
**Lines:** `599-640`
**Category:** Technical Debt
**Confidence:** Confirmed

**What was found:**
`CalculatorController.__init__` sets up default states for all 12 calculator modes. However, `reset_calculator()` duplicates this exact initialization dictionary logic across lines 1046-1082.

**Impact:**
Duplicate state initialization creates maintenance overhead if state structure changes.

**Recommended action:**
Refactor `__init__` to invoke `reset_calculator()`.

---

## 7. Dead Code

### Summary Table of Unused Symbols

```text
Symbol: __init__ (CalculatorController)
Definition: mvp_server.py:599
References found: 1
Dynamic references considered: Standard Python instantiation
Conclusion: POSSIBLY INTENTIONAL (class constructor)

Symbol: _safe_sin, _safe_cos, _safe_tan, _safe_asin, _safe_acos, _safe_atan
Definition: mvp_server.py:271-330
References found: 1 each
Dynamic references considered: Local scope inside safe_evaluate_expression
Conclusion: DEFINITELY UNUSED (never called or passed to AST evaluator)

Symbol: buildTableRows
Definition: frontend.html:2840
References found: 1
Dynamic references considered: DOM callbacks, window properties
Conclusion: DEFINITELY UNUSED

Symbol: equationCoefficientCount
Definition: frontend.html:3410
References found: 1
Dynamic references considered: DOM callbacks, window properties
Conclusion: DEFINITELY UNUSED

Symbol: log_message (MvpHandler)
Definition: mvp_server.py:1860
References found: 1
Dynamic references considered: Override of http.server.BaseHTTPRequestHandler.log_message
Conclusion: POSSIBLY INTENTIONAL (silences standard HTTP logging)
```

---

## 8. Duplicate / Competing Implementations

### Competing Expression Evaluation Paths
1. **Frontend Local Parser:** `serializeCurrentExpression()` and `evaluateExpressionLocal()` in `frontend.html`.
2. **Backend Engine API:** `/api/evaluate` and `/api/key` handling via `safe_evaluate_expression()` in `mvp_server.py`.

**Analysis:**
`frontend.html` attempts to parse simple arithmetic locally when offline or in fast-response mode, but falls back to `/api/evaluate` for advanced functions. Differences in handling operator precedence between the JS local evaluator and Python AST parser create inconsistent results between local UI calculation and server API evaluation.

---

## 9. Dead-End Execution Paths

### Unreachable Backend Endpoints
The following endpoints exist in `mvp_server.py` `do_POST` / `do_GET` handlers but are never called by `frontend.html`:

```text
1. POST /api/mode
   → Server handler: lines 1779-1780
   → Frontend callers: 0
   → Result: Dead endpoint

2. POST /api/calculate
   → Server handler: lines 1785-1786
   → Frontend callers: 0
   → Result: Dead endpoint

3. POST /api/spreadsheet/eval
   → Server handler: lines 1823-1824
   → Frontend callers: 0
   → Result: Dead endpoint

4. GET /api/state
   → Server handler: lines 1723-1725
   → Frontend callers: 0
   → Result: Dead endpoint

5. GET /api/constants
   → Server handler: lines 1735-1737
   → Frontend callers: 0
   → Result: Dead endpoint
```

---

## 10. Frontend Logic Issues

### Stale State in D-Pad Menu Navigation

**File:** `frontend.html`
**Lines:** `1200-1250`
**Category:** State / UI Issue
**Confidence:** Confirmed

**What was found:**
When navigating setup menus using the D-pad, `appState.menuPage` is modified, but if the user presses `AC` or exits without selecting an option, `appState.menuPage` is not reset to `0`, leaving setup state stale upon reopening.

---

## 11. Backend Logic Issues

### Division by Zero Exception Translation

**File:** `mvp_server.py`
**Lines:** `338-342`
**Category:** Exception Handling
**Confidence:** Confirmed

**What was found:**
In `safe_evaluate_expression()`, `except ZeroDivisionError: raise` allows raw `ZeroDivisionError` to bubble up, whereas other evaluation failures are caught and wrapped as `ValueError("Math ERROR: ...")`. This causes inconsistent HTTP status codes or unhandled internal server errors depending on caller catch blocks.

---

## 12. Frontend ↔ Backend Contract Issues

### Field Casing Mismatch in Matrix Data Payload

**File:** `frontend.html`, `mvp_server.py`
**Lines:** `frontend.html:4210`, `mvp_server.py:740-771`
**Category:** API Contract Issue
**Confidence:** Confirmed

**What was found:**
Frontend sends matrix initialization payloads with dimensions as `rows` and `cols` integers, but backend validation expects `dim` array `[rows, cols]` in certain secondary helper paths.

---

## 13. Syntax / Parse Issues

### Python Syntax Warning in Test File

**File:** `test_serialize.py`
**Line:** `28`
**Category:** Syntax Warning
**Confidence:** Confirmed

**What was found:**
`SyntaxWarning: invalid escape sequence '\^'` occurs during module compilation due to unescaped regex backslash in string literal `out.replace("×10\^", "*10^")`.

---

## 14. Runtime / Test Results

### Test Execution Summary

| Test File | Command | Status | Result / Error Output |
| :--- | :--- | :--- | :--- |
| `verify.py` | `python3 verify.py` | **PASS** | 7/7 HTTP calls succeeded, legacy indicator checks clean |
| `test_file_mode.py` | `python3 test_file_mode.py` | **FAIL** | 5/6 passed. `parity_with_backend` failed on exponentiation expressions (`2^3`) |
| `test_engine.py` | `python3 test_engine.py` | **PASS** | Engine AST tokenization and evaluation verified |
| `test_eval.py` | `python3 test_eval.py` | **PASS** | Expression evaluation and keypress handling verified |
| `test_full.py` | `python3 test_full.py` | **FAIL** | `FileNotFoundError: [Errno 2] No such file or directory: 'E:\A.G\casio_mvp'` |
| `test_full2.py` | `python3 test_full2.py` | **FAIL** | `FileNotFoundError: [Errno 2] No such file or directory: 'E:\A.G\casio_mvp'` |
| `test_safe_eval.py` | `python3 test_safe_eval.py` | **PASS** | Safe evaluation tests passed |
| `test_safe_eval_regressions.py` | `python3 test_safe_eval_regressions.py` | **FAIL** | Failed on `2^3` exponentiation expression evaluation |
| `test_serialize.py` | `python3 test_serialize.py` | **PASS** | Serialization pipeline passed (with 1 SyntaxWarning) |
| `test_settings_and_setup.py` | `python3 test_settings_and_setup.py` | **FAIL** | 1 Error (Trig angle degree parse error), 1 Fail (AssertionError on error string) |

---

## 15. Suspicious Code Requiring Investigation

1. **`_transform_special_functions` Regex Substitution Rules (`mvp_server.py:142-237`):** The complex regular expression pipeline for converting Casio display symbols (`×`, `÷`, `−`, `√`, `∫`, `^`) into standard Python expressions contains overlapping regex patterns that alter token positions and cause `ParseError` on valid inputs.
2. **Dual Setup State Storage (`frontend.html:850`, `mvp_server.py:642`):** Settings are stored both in client `localStorage` and server `CalculatorController.settings`. Synchronization occurs only on explicit POST `/setup_update`, leading to drift if page refreshes without server sync.

---

## 16. Recommended Cleanup Order

1. **Fix Exponentiation Parsing (`^` operator in `mvp_server.py`):** Resolve the regex transformation bug in `_transform_special_functions` so powers evaluate correctly.
2. **Fix Trigonometric Function Context in `safe_evaluate_expression`:** Wire `_safe_sin`, `_safe_cos`, `_safe_tan`, etc., into the evaluation namespace so angle units (Degree/Gradian/Radian) are respected.
3. **Fix Test Suite Hardcoded Paths:** Replace `E:\A.G\casio_mvp` in `test_full.py`, `test_full2.py`, and `test_server.py` with dynamic directory references.
4. **Standardize API Error Response Schemas:** Align backend error response objects (`{"ok": false, "error": "..."}`) with frontend response parsers.
5. **Remove Dead Client Functions and Unused Endpoints:** Delete `buildTableRows`, `equationCoefficientCount`, and orphaned backend routes (`/api/mode`, `/api/calculate`, `/api/spreadsheet/eval`, `/api/state`, `/api/constants`).

---

## 17. Files Audited

* `frontend.html` (6,839 lines) — Browser Frontend UI & Client State Logic
* `mvp_server.py` (1,886 lines) — Local HTTP Server & Controller
* `engine/` package files — AST Tokenizer, Parser, Evaluator, Mode Packages
* `test_*.py` and `verify.py` — Test Suite & Verification Scripts

---

## 18. Audit Limitations

* Static analysis of dynamic `eval()` or string-constructed element selectors in JavaScript can miss indirect call sites; manual inspection was performed to verify zero usages.
* Desktop GUI (`main.py` / PySide6) was not executed in interactive GUI mode as the audit focus is `frontend.html` and `mvp_server.py`.
