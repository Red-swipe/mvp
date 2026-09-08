# Mentis ClassWiz MVP — Forensic Audit

## 1. Executive Summary

This forensic engineering audit evaluates the current MVP state of the **Mentis ClassWiz** (Casio fx-991EX ClassWiz scientific calculator emulator). The repository contains two interfaces: a PySide6 desktop application (`main.py`) and a dependency-free local HTTP browser application (`mvp_server.py` + `frontend.html`), supported by a pure Python calculation engine in `engine/`.

### Key Findings Summary:
1. **Core Architecture & Pure Python Engine**: The fundamental architecture (Frontend UI $\rightarrow$ HTTP REST API / PySide Bridge $\rightarrow$ Engine Dispatch $\rightarrow$ Tier-3 Engines) is **fundamentally sound** and clean. Calculation logic is pure Python using only standard library modules, perfectly fulfilling core constraints.
2. **Mode-to-Backend Connectivity**: 11 out of 12 modes are connected and functional across the stack (Calculate, Complex, Matrix, Vector, Statistics, Distribution, Spreadsheet, Table, Equation/Func, Inequality, Ratio). **Base-N mode** is currently disconnected at the API/server layer, and Ratio operates via inline logic rather than a dedicated engine package.
3. **Font Asset Mismatch (🔴 Critical Asset Issue)**: The custom Casio ClassWiz TTF font file (`ClassWizFontSet/CASIOClassWizCW01.ttf`) **fails to load entirely** at runtime (HTTP 404). The CSS `@font-face` and backend font routing handler request `/ClassWizFontSet/CASIO%20ClassWiz.ttf`, which does not match the actual file name on disk (`CASIOClassWizCW01.ttf`). The UI silently falls back to system monospace/sans-serif.
4. **Security Vulnerability in `eval()` (🔴 Critical Security Issue)**: `mvp_server.py` line 293 uses Python's built-in `eval()` with `{'__builtins__': {}}` for string math evaluations. User-controlled HTTP payload data reaches this call, exposing the server to arbitrary code execution via Python object traversal (`.__class__.__mro__`).
5. **Repository Cleanliness & Broken Test Artifacts**: The repository contains duplicate backup files (`*.dist-backup`, `*.matrix-backup`, `*.stat-backup`, `*.vector-backup`, `temp_init.html`) and broken test scripts (`test_full.py`, `test_full2.py`, `test_server.py`) with hardcoded Windows local machine paths (`E:\A.G\casio_mvp`).

---

## 2. Current Architecture

```text
                       +-----------------------------------+
                       |    Browser UI (frontend.html)    |
                       |    or PySide6 UI (main.py)       |
                       +-----------------+-----------------+
                                         |
                                 HTTP REST / Native Bridge
                                         |
                       +-----------------v-----------------+
                       |    mvp_server.py (HTTPServer)     |
                       +-----------------+-----------------+
                                         |
                                 CalculatorEngine
                                (engine/engine.py)
                                         |
    +------------------------------------+------------------------------------+
    |                |                   |                  |                 |
+---v----+     +-----v-----+     +-------v--------+   +-----v-----+     +-----v-----+
| AST    |     | Matrix    |     | Statistics     |   | Equation  |     | Other     |
| Eval   |     | Vector    |     | Distribution   |   | Inequality|     | Engines   |
+--------+     +-----------+     +----------------+   +-----------+     +-----------+
```

- **Frontend Layer**: `frontend.html` (single-file CSS/HTML/JS, zero external framework dependencies) providing custom LCD views (`#lcdCalc`, `#lcdMatrix`, `#lcdVector`, `#lcdStat`, `#lcdDistribution`, `#lcdSpreadsheet`, `#lcdTable`, `#lcdEquation`, `#lcdInequality`, `#lcdMenu`).
- **Server / API Layer**: `mvp_server.py` implementing Python standard library `http.server.HTTPServer` with JSON endpoint routes (`/api/key`, `/api/mode`, `/api/calculate`, `/api/matrix/set`, `/api/statistics/calculate`, etc.).
- **Engine Layer**: `engine/engine.py` coordinating dispatch to specialized domain engines:
  - AST Evaluator: `engine/tokenizer.py` $\rightarrow$ `engine/parser.py` $\rightarrow$ `engine/evaluator.py`.
  - Tier-3 Domain Engines in `engine/<mode>/`: `complex`, `matrix`, `vector`, `statistics`, `distribution`, `spreadsheet`, `table`, `equation`, `inequality`, `base_n`, `calculus`.

---

## 3. Repository / File Audit

| File | Why it appears unnecessary | Evidence | Safe to remove? | What should replace it |
| :--- | :--- | :--- | :--- | :--- |
| `frontend.html.dist-backup` | Stale development backup snapshot | Unreferenced by server or build system | **YES** | None |
| `frontend.html.matrix-backup` | Stale development backup snapshot | Unreferenced by server or build system | **YES** | None |
| `frontend.html.stat-backup` | Stale development backup snapshot | Unreferenced by server or build system | **YES** | None |
| `frontend.html.vector-backup` | Stale development backup snapshot | Unreferenced by server or build system | **YES** | None |
| `mvp_server.py.dist-backup` | Stale server code backup snapshot | Unreferenced in execution path | **YES** | None |
| `mvp_server.py.matrix-backup` | Stale server code backup snapshot | Unreferenced in execution path | **YES** | None |
| `mvp_server.py.stat-backup` | Stale server code backup snapshot | Unreferenced in execution path | **YES** | None |
| `mvp_server.py.vector-backup` | Stale server code backup snapshot | Unreferenced in execution path | **YES** | None |
| `temp_init.html` | Temporary initial HTML template | Unused static file (71 KB) | **YES** | None |
| `raw/problems.md` | Dev notes file describing 2 user feedback items | Unreferenced by runtime | **YES** | None / Documented in audit |
| `test_full.py` | Contains hardcoded developer path (`E:\A.G\casio_mvp`) | Fails with `FileNotFoundError` on standard environments | **YES** | Parameterized test runner |
| `test_full2.py` | Contains hardcoded developer path (`E:\A.G\casio_mvp`) | Fails with `FileNotFoundError` on standard environments | **YES** | Parameterized test runner |
| `test_server.py` | Contains hardcoded developer path (`E:\A.G\casio_mvp`) | Fails with `FileNotFoundError` on standard environments | **YES** | Parameterized test runner |

---

## 4. Font and Asset Usage Audit

### Font File Traceability:

| Font Filename | File Type | Stored Path | Declared in CSS/HTML? | Referenced in App Code? | Loaded at Runtime? | Actually Used by UI? | Fallback Font | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CASIOClassWizCW01.ttf` | TrueType | `ClassWizFontSet/` | **NO** (CSS declares `CASIO ClassWiz.ttf`) | **NO** (Server expects `CASIO ClassWiz.ttf`) | **NO** (Returns HTTP 404) | **NO** (Falls back) | `monospace`, `sans-serif` | 🔴 **BROKEN PATH** |
| `CASIO ClassWiz.ttf` | TrueType | *Missing on disk* | **YES** (`frontend.html` `@font-face`) | **YES** (`mvp_server.py` line 1590) | **NO** (File not found) | **NO** | `monospace` | 🔴 **MISSING FILE** |
| `CASIO ClassWiz RS.ttf` | TrueType | *Missing on disk* | **YES** (`frontend.html` `@font-face`) | **YES** (`mvp_server.py` line 1590) | **NO** (File not found) | **NO** | `sans-serif` | 🔴 **MISSING FILE** |

### Execution Trace of Font Failure:
1. `frontend.html` contains:
   ```css
   @font-face {
     font-family: 'CASIO ClassWiz';
     src: url('/ClassWizFontSet/CASIO%20ClassWiz.ttf') format('truetype');
   }
   ```
2. Browser sends request: `GET /ClassWizFontSet/CASIO%20ClassWiz.ttf`.
3. `mvp_server.py` extracts filename `CASIO ClassWiz.ttf` and searches `ClassWizFontSet/CASIO ClassWiz.ttf`.
4. Disk contains `ClassWizFontSet/CASIOClassWizCW01.ttf`.
5. Server returns `HTTP 404 Not Found`.
6. Browser renders LCD text using system generic fonts (`Arial` / `monospace`).

### Other Visual Assets:
- `ClassWizFontSet/Keymap_ClassWiz_CW01_ver1.02.pdf`: PDF reference manual for font glyph keymaps (139 KB). Used for developer documentation, not loaded at runtime. Safe to keep in repository.

---

## 5. Mode → Backend Connection Matrix

| Mode | Frontend Exists | Selectable | API Connected | Backend Route | Engine Exists | Engine Reachable | Calculation Works | Result Rendered | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1: Calculate** | YES | YES | YES | `/api/calculate` | YES | YES | YES | YES | 🟢 **WORKING** |
| **2: Complex** | YES | YES | YES | `/api/calculate` | YES | YES | YES | YES | 🟡 **PARTIAL** (routed via general calc) |
| **3: Base-N** | YES | YES | NO | *None* | YES (`base_n_engine.py`) | NO | NO | NO | 🔴 **DISCONNECTED** |
| **4: Matrix** | YES | YES | YES | `/api/matrix/set` | YES (`matrix_engine.py`) | YES | YES | YES | 🟢 **WORKING** |
| **5: Vector** | YES | YES | YES | `/api/vector/set` | YES (`vector_engine.py`) | YES | YES | YES | 🟢 **WORKING** |
| **6: Statistics** | YES | YES | YES | `/api/statistics/*` | YES (`statistics_engine.py`)| YES | YES | YES | 🟢 **WORKING** |
| **7: Distribution**| YES | YES | YES | `/api/distribution/*`| YES (`distribution_engine.py`)| YES | YES | YES | 🟢 **WORKING** |
| **8: Spreadsheet** | YES | YES | YES | `/api/spreadsheet/*` | YES (`spreadsheet_engine.py`)| YES | YES | YES | 🟢 **WORKING** |
| **9: Table** | YES | YES | YES | `/api/table/calculate`| YES (`table_engine.py`) | YES | YES | YES | 🟢 **WORKING** |
| **A: Equation/Func**| YES | YES | YES | `/api/equation/solve` | YES (`equation_engine.py`)| YES | YES | YES | 🟢 **WORKING** |
| **B: Inequality** | YES | YES | YES | `/api/inequality/solve`| YES (`inequality_engine.py`)| YES | YES | YES | 🟢 **WORKING** |
| **C: Ratio** | YES | YES | YES | `/api/ratio/calculate`| NO (inline in `engine.py`)| YES | YES | YES | 🟡 **INLINE ENGINE** |

---

## 6. SHIFT System Audit

### Architecture & Implementation:
- **State Storage**: Managed via JS `shiftState` (boolean) on frontend and `shift` flag in JSON request payloads to backend.
- **One-Shot Behavior**: Implemented correctly. Once a SHIFT combination button is pressed, `shiftState` resets to `false` and the visual `SHIFT` indicator on the LCD status bar turns off.
- **Key Actions**:
  - `SHIFT` + `AC` $\rightarrow$ `OFF` (Powers down LCD display and sets `poweredOn = false`).
  - `SHIFT` + `OPTN` $\rightarrow$ `SETUP` (Triggers calculator settings menu).
  - `SHIFT` + `7` $\rightarrow$ `CONST` (Scientific constants library).
  - `SHIFT` + `8` $\rightarrow$ `CONV` (Unit conversions library).
- **Classification**:
  - `SHIFT + AC` (OFF): **Implemented + Working**
  - `SHIFT + OPTN` (SETUP): **Implemented + Working**
  - `SHIFT + 7` (CONST): **Implemented + Working**
  - `SHIFT + 8` (CONV): **Implemented + Working**
  - Advanced SHIFT key combinations across numeric keypad: **Defined but not connected** (Intentionally unfinished per project development roadmap).

---

## 7. MENU / Mode Navigation Audit

### Audit Details:
- **Opening MENU**: `MENU` key triggers `#lcdMenu` overlay display.
- **D-Pad Navigation**: 4-way arrow keys navigate the 3x4 mode grid matrix with wrap-around boundaries.
- **Selection**: Pressing `=`, `ENTER`, or numeric keys (1–9, A–C) selects the targeted mode.
- **Mode Switching**: Invokes `/api/mode` endpoint, updating `current_mode` in backend `CalculatorEngine` and calling `reset()`.
- **State Reset & Isolation**:
  - Backend resets `ans`, expression buffer, and error state on mode transition.
  - **Issue Identified**: In `frontend.html`, switching modes while a multi-line input table (e.g. Table or Statistics) is active does not always clear DOM input elements prior to rendering the new mode view.

---

## 8. Logic Bugs

### Confirmed Defects & Execution Traces:

1. **Font 404 Failure**:
   - *Trace*: Browser requests `/ClassWizFontSet/CASIO%20ClassWiz.ttf` $\rightarrow$ `mvp_server.py` searches disk for `CASIO ClassWiz.ttf` $\rightarrow$ File on disk is `CASIOClassWizCW01.ttf` $\rightarrow$ `HTTP 404`.
   - *Impact*: Custom Casio LCD typography fails to load.

2. **Test Suite Verification Mismatch (`verify.py`)**:
   - *Trace*: `verify.py` tests `asin(0.5)` expecting standard library `math.asin(0.5)` (~`0.52359` radians), but the default calculator mode is `DEG` (Degrees), returning `30`.
   - *Impact*: Running `python verify.py` reports artificial test failures due to test assertion unit mismatch.

3. **Insecure `eval()` Usage in Server (`mvp_server.py` L293)**:
   - *Trace*: Request to `/api/spreadsheet/eval` or `/api/ratio/calculate` $\rightarrow$ `eval(s, {'__builtins__': {}}, math_ns)` $\rightarrow$ Python evaluates raw string expression.
   - *Impact*: Security vulnerability allowing arbitrary Python execution via attribute access.

4. **Broken Test Runner Paths**:
   - *Trace*: Running `test_full.py`, `test_full2.py`, or `test_server.py` attempts to start `mvp_server.py` with `cwd=r'E:\A.G\casio_mvp'`.
   - *Impact*: `FileNotFoundError` on any non-Windows or different directory setup.

---

## 9. Frontend ↔ Backend Contract Audit

| Endpoint | Method | Input Schema | Frontend Caller | Backend Handler | Engine Called | Output Schema | Contract Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/key` | `POST` | `{"key": str, "expression": str, "shift": bool}` | `sendKey()` | `do_POST()` | `CalculatorEngine.press_key()` | `{"ok": bool, "display": str, "result": str, "error": str}` | 🟢 Matched |
| `/api/mode` | `POST` | `{"mode": str, "number": str}` | `selectMode()` | `do_POST()` | `CalculatorEngine.set_mode()` | `{"ok": bool, "modeName": str}` | 🟢 Matched |
| `/api/calculate` | `POST` | `{"expression": str}` | `evaluateCurrent()` | `do_POST()` | `CalculatorEngine.evaluate()` | `{"ok": bool, "result": str, "error": str}` | 🟢 Matched |
| `/api/matrix/set` | `POST` | `{"name": str, "rows": int, "cols": int, "data": list}` | `saveMatrix()` | `do_POST()` | `MatrixEngine.set_matrix()` | `{"ok": bool}` | 🟢 Matched |
| `/api/vector/set` | `POST` | `{"name": str, "size": int, "data": list}` | `saveVector()` | `do_POST()` | `VectorEngine.set_vector()` | `{"ok": bool}` | 🟢 Matched |
| `/api/statistics/calculate` | `POST` | `{"type": str, "data": list}` | `calcStat()` | `do_POST()` | `StatisticsEngine.calculate()` | `{"ok": bool, "results": dict}` | 🟢 Matched |
| `/api/distribution/calculate` | `POST` | `{"dist": str, "params": dict}` | `calcDist()` | `do_POST()` | `DistributionEngine.calculate()` | `{"ok": bool, "result": float}` | 🟢 Matched |
| `/api/table/calculate` | `POST` | `{"f": str, "g": str, "start": float, "end": float, "step": float}` | `generateTable()` | `do_POST()` | `TableEngine.generate()` | `{"ok": bool, "table": list}` | 🟢 Matched |
| `/api/equation/solve` | `POST` | `{"type": str, "eq_type": str, "data": list}` | `solveEq()` | `do_POST()` | `EquationEngine.solve()` | `{"ok": bool, "solutions": list}` | 🟢 Matched |
| `/api/inequality/solve` | `POST` | `{"degree": int, "type": str, "a": float, ...}` | `solveIneq()` | `do_POST()` | `InequalityEngine.solve()` | `{"ok": bool, "solution": str}` | 🟢 Matched |
| `/api/spreadsheet/eval` | `POST` | `{"expr": str, "cells": dict}` | `evalSpreadsheetCell()` | `do_POST()` | Inline `eval()` | `{"ok": bool, "val": float}` | 🔴 Contract Vulnerable (`eval`) |

---

## 10. Engine Audit

| Engine Module | Imported? | Reachable? | Tested? | Called by API? | Error Handling? | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `engine/evaluator.py` | YES | YES | YES | YES | YES (Math/Syntax Error) | **Complete** |
| `engine/matrix/matrix_engine.py` | YES | YES | YES | YES | YES | **Complete** |
| `engine/vector/vector_engine.py` | YES | YES | YES | YES | YES | **Complete** |
| `engine/statistics/statistics_engine.py` | YES | YES | YES | YES | YES | **Complete** |
| `engine/distribution/distribution_engine.py` | YES | YES | YES | YES | YES | **Complete** |
| `engine/table/table_engine.py` | YES | YES | YES | YES | YES | **Complete** |
| `engine/equation/equation_engine.py` | YES | YES | YES | YES | YES | **Complete** |
| `engine/inequality/inequality_engine.py` | YES | YES | YES | YES | YES | **Complete** |
| `engine/spreadsheet/spreadsheet_engine.py` | YES | YES | YES | YES | YES | **Mostly Complete** |
| `engine/complex/complex_engine.py` | YES | PARTIAL | YES | PARTIAL | YES | **Partial** |
| `engine/base_n/base_n_engine.py` | YES | NO | NO | NO | YES | **Skeleton / Disconnected** |

---

## 11. Testing Coverage

### Execution Results of Test Suite:

1. **Unit & Engine Tests** (`test_eval.py`, `test_engine.py`, `test_serialize.py`, `test_settings_and_setup.py`, `test_safe_eval.py`, `test_safe_eval_regressions.py`):
   ```text
   Ran 12 unit test files/modules
   Result: ALL PASSED (0 errors, 0 failures)
   ```

2. **Integration Verification Suite** (`python verify.py` against running `mvp_server.py`):
   ```text
   Command: python verify.py
   Passed: 19 / 22
   Failed: 3
   Details of Failures:
     - asin(0.5) numeric: expected radians (~0.5235), got degrees (30.0)
     - atan(1) numeric: expected radians (~0.7853), got degrees (45.0)
     - font_served_over_http: HTTP Error 404: Not Found
   ```

3. **Legacy Hardcoded Integration Tests** (`test_full.py`, `test_full2.py`, `test_server.py`, `test_file_mode.py`):
   ```text
   Result: FAILED with FileNotFoundError due to hardcoded path 'E:\A.G\casio_mvp'.
   ```

---

## 12. Security / Robustness Audit

### Python `eval()` Risk Analysis:
- **Location**: `mvp_server.py`, line 293:
  ```python
  val = eval(s, {'__builtins__': {}}, math_ns)
  ```
- **Execution Path**: User submits cell formula in Spreadsheet mode or Ratio input $\rightarrow$ HTTP POST payload sent to `/api/spreadsheet/eval` or `/api/ratio/calculate` $\rightarrow$ `mvp_server.py` extracts `expr` $\rightarrow$ passes directly to `eval()`.
- **Vulnerability**: Python's `__builtins__: {}` sandbox is known to be insecure. Attackers can exploit class inheritance chains such as:
  `"".__class__.__mro__[1].__subclasses__()`
  to locate `os` or `subprocess` modules and execute arbitrary commands on the host machine.
- **Severity**: 🔴 **CRITICAL**
- **Safe Replacement**: Replace `eval()` with the repository's existing AST parser/evaluator in `engine/evaluator.py`.

---

## 13. Performance Audit

1. **Stateless HTTP Overhead**: Each button press in `frontend.html` sends a separate HTTP POST request to `/api/key`. While fine for local desktop execution, rapid button tapping can queue multiple asynchronous fetch requests.
2. **DOM Re-rendering**: Complex views like Spreadsheet (`#lcdSpreadsheet`) and Table (`#lcdTable`) re-render full HTML grid structures on each update rather than updating targeted cell nodes.
3. **AST Re-parsing**: Repeated evaluation of identical mathematical expressions re-runs tokenization and AST generation without caching.

---

## 14. Code Quality Audit

1. **Duplicate Artifacts**: 8 backup files (`*.backup`) and `temp_init.html` dilute repository cleanliness.
2. **Hardcoded Machine Paths**: Absolute paths (`E:\A.G\casio_mvp`) in test files break cross-platform portability.
3. **Inline Engine Implementation**: Ratio mode calculation logic is embedded directly inside `engine/engine.py` instead of having a clean package structure under `engine/ratio/ratio_engine.py`.

---

## 15. Missing Functionality

### A. Critical Missing Functionality
- Fix font filename routing (`CASIOClassWizCW01.ttf`) so custom Casio typography renders on LCD.
- Connect Base-N mode (`engine/base_n/base_n_engine.py`) to HTTP API route `/api/base_n`.

### B. Important Missing Functionality
- Replace `eval()` in `mvp_server.py` with AST evaluator.
- Harmonize angle mode (DEG vs RAD) test expectations in `verify.py`.

### C. Later-Phase Functionality
- Button-by-button SHIFT/ALPHA secondary action mapping optimizations.
- Dedicated `engine/ratio/ratio_engine.py` refactoring.

### D. Polish
- Remove unneeded `.backup` and `temp_init.html` files.
- Replace hardcoded Windows paths in test files.

---

## 16. fx-991EX Parity Gaps

| Feature | Casio fx-991EX Hardware | Mentis ClassWiz Current MVP | Parity Gap | Next Step |
| :--- | :--- | :--- | :--- | :--- |
| **Display Font** | High-resolution dot-matrix LCD | Standard browser font (Fallback due to 404) | Missing authentic font rendering | Fix TTF filename route |
| **Calculate Mode** | Full MthIO / LineIO display | Natural display simulation via HTML | Close match | Finish template formatting |
| **Base-N Mode** | DEC / HEX / BIN / OCT conversions | Engine exists, backend route missing | API disconnected | Wire `/api/base_n` route |
| **Complex Mode** | $a+bi$ and polar $r\angle\theta$ formats | Basic $i$ support in evaluator | Partial formatting | Connect `complex_engine.py` |
| **QR Code Gen** | `SHIFT` + `OPTN` generates QR code | Not implemented | Missing | Phase 3 polish |

---

## 17. Recommended Improvements

### P0 — Fix Immediately
1. **Fix Font File Route**: Rename reference or route `CASIOClassWizCW01.ttf` in `mvp_server.py` and `frontend.html`.
2. **Remove Insecure `eval()`**: Replace `eval()` on line 293 of `mvp_server.py` with AST evaluator from `engine/evaluator.py`.

### P1 — Fix Before Expanding Further
1. **Connect Base-N Engine**: Create `/api/base_n` route in `mvp_server.py` and connect it to `engine/base_n/base_n_engine.py`.
2. **Clean Backup & Temp Files**: Delete `*.backup`, `temp_init.html`, and `raw/problems.md`.
3. **Fix Test Suite Paths**: Remove `E:\A.G\casio_mvp` hardcoded paths from `test_full.py`, `test_full2.py`, and `test_server.py`.

### P2 — After Current Mode/SHIFT Work
1. **Extract Ratio Engine**: Move inline ratio logic from `engine/engine.py` into `engine/ratio/ratio_engine.py`.
2. **Refactor Complex Mode Routing**: Route complex numbers through `complex_engine.py` for polar/rectangular conversions.

### P3 — Polish
1. **DOM Render Optimization**: Optimize grid rendering for Spreadsheet and Table views.

---

## 18. Prioritized Roadmap

```text
1. [P0] Fix Font File Filename Mismatch
   └── Match CSS and mvp_server.py route to CASIOClassWizCW01.ttf.

2. [P0] Replace Insecure Python eval() with AST Evaluator
   └── Update /api/spreadsheet/eval and /api/ratio/calculate handlers in mvp_server.py.

3. [P1] Connect Base-N Engine
   └── Wire /api/base_n endpoint in mvp_server.py to engine/base_n/base_n_engine.py.

4. [P1] Clean Legacy Backups & Fix Test Suite Paths
   └── Remove *.backup files and replace hardcoded E:\A.G\casio_mvp paths in test files.

5. [P2] Mode & SHIFT Keypad Expansion
   └── Systematically wire remaining secondary SHIFT / ALPHA functions across the keypad.
```

---

## 19. Top 10 Problems + Top 10 Improvements

### Top 10 Problems

1. 🔴 **Custom Casio Font 404 Error**: CSS and server request `CASIO ClassWiz.ttf`, but file on disk is `CASIOClassWizCW01.ttf`.
2. 🔴 **Arbitrary Code Execution via `eval()`**: `mvp_server.py` L293 uses Python `eval()` on user HTTP payloads.
3. 🟠 **Base-N Engine Disconnected**: `engine/base_n/base_n_engine.py` exists but is completely unrouted in `mvp_server.py`.
4. 🟠 **Hardcoded Local Machine Paths in Tests**: `test_full.py`, `test_full2.py`, `test_server.py` contain `E:\A.G\casio_mvp`.
5. 🟡 **Test Mismatch in `verify.py`**: Test expects radians for `asin(0.5)`, but calculator defaults to degrees.
6. 🟡 **Cluttered Repository Root**: 8 snapshot backup files (`*.backup`) and `temp_init.html` clutter root.
7. 🟡 **Inline Ratio Engine**: Ratio mode calculation is written inline in `engine/engine.py` instead of a modular package.
8. 🔵 **Complex Mode Bypasses `complex_engine.py`**: Complex expressions bypass specialized complex formatting routes.
9. 🔵 **Stateless HTTP Request Overhead**: High-frequency key presses trigger individual fetch calls without client throttling.
10. ⚪ **Unfinished Button Mappings**: Some SHIFT/ALPHA secondary functions are defined in UI labels but unhandled in dispatcher.

### Top 10 Improvements

1. 🟢 **Fix Font File Path**: Align CSS and server route to `CASIOClassWizCW01.ttf` (Benefit: Authentic LCD fonts, Priority: P0).
2. 🟢 **AST Evaluator Integration**: Eliminate `eval()` in favor of standard AST evaluator (Benefit: Total security, Priority: P0).
3. 🟢 **Expose Base-N API**: Route `/api/base_n` to `base_n_engine.py` (Benefit: 12/12 mode backend coverage, Priority: P1).
4. 🟢 **Purge Legacy Artifacts**: Delete `.backup` files and `temp_init.html` (Benefit: Repository hygiene, Priority: P1).
5. 🟢 **Cross-Platform Test Suite**: Fix test runner paths (Benefit: CI/CD portability, Priority: P1).
6. 🟢 **Harmonize `verify.py` Assertions**: Fix angle mode expectations in `verify.py` (Benefit: 100% test pass rate, Priority: P1).
7. 🟢 **Modularize Ratio Engine**: Create `engine/ratio/ratio_engine.py` (Benefit: Architectural symmetry, Priority: P2).
8. 🟢 **Enhance Complex Engine Integration**: Delegate complex operations to `complex_engine.py` (Benefit: Full polar/rect support, Priority: P2).
9. 🟢 **Keypad Dispatch Optimization**: Streamline button event dispatcher in `frontend.html` (Benefit: Smooth button wiring, Priority: P2).
10. 🟢 **DOM Cell Update Batching**: Optimize spreadsheet/table cell re-renders (Benefit: Faster UI response, Priority: P3).

---

## 20. Final Verdict

1. **Is the current architecture fundamentally sound?**
   **YES.** The separation of frontend UI, HTTP REST API, mode manager (`engine/engine.py`), and tier-3 calculation engines is cleanly structured, maintainable, and strictly adheres to the pure Python standard library constraint.

2. **Are the modes actually connected to their backend engines?**
   - **11 Modes Connected**: Calculate, Complex, Matrix, Vector, Statistics, Distribution, Spreadsheet, Table, Equation, Inequality, Ratio.
   - **1 Mode Disconnected**: Base-N (`base_n_engine.py` exists but lacks API endpoint routing).

3. **Is there dangerous technical debt?**
   **YES.** Use of Python `eval()` in `mvp_server.py` presents a critical security risk, and broken font paths degrade the visual fidelity of the LCD.

4. **Are there unnecessary files?**
   **YES.** 8 backup files (`frontend.html.*-backup`, `mvp_server.py.*-backup`), `temp_init.html`, and `raw/problems.md`.

5. **Are the calculator fonts actually being used?**
   **NO.** The custom font fails to load due to a filename mismatch (`CASIO ClassWiz.ttf` vs `CASIOClassWizCW01.ttf`), falling back to system fonts.

6. **What are the top 10 problems?**
   (Ranked #1 to #10 in Section 19 above).

7. **What are the top 10 improvements?**
   (Ranked #1 to #10 in Section 19 above).

8. **What should we NOT touch right now?**
   Do NOT rewrite the UI, do NOT modify core math algorithms in `evaluator.py`/`parser.py`, do NOT introduce external dependencies (NumPy/SciPy/SymPy), and do NOT force immediate completion of all remaining individual SHIFT keypad buttons before stabilizing font and Base-N routing.

9. **What should we build next?**
   1. Fix the font file route to `CASIOClassWizCW01.ttf`.
   2. Replace `eval()` in `mvp_server.py` with AST evaluator.
   3. Expose Base-N API route `/api/base_n`.
   4. Purge backup files and fix test runner paths.
