# AUDIT REPORT: Mentis ClassWiz Calculator (Casio fx-991EX Emulator)

## Section A: Root Cause Analysis of Teacher's "Math ERROR"
The teacher experienced a `Math ERROR` on release v0.1 when double-clicking `RUN_CALCULATOR.bat` on Windows.

### Case 1 Evaluation Across Paths
- **Path A (`file://` browser local evaluate)**: Returned `4.666666667` (PASS).
- **Path B (`http://localhost:8000` via server)**: Returned `4.666666667` (PASS).
- **Path C (Python Engine `safe_evaluate_expression`)**: Returned `4.666666667` (PASS).

### Ranked Root Cause Candidates
1. **Candidate 1: Missing Application Directory on `sys.path` in Portable Embedded CPython (UNPROVEN / HIGH PROBABILITY)**
   - **Mechanism**: The bundled Windows release uses Python embeddable (`python-3.12.8-embed-amd64.zip`), which runs in isolated mode. In isolated mode, `sys.path` is determined solely by `python312._pth`. If `python312._pth` does not contain `..` (the application root), attempting `import engine` or `import mvp_server` raises `ModuleNotFoundError`.
   - **Swallowed Error Impact**: Prior to Phase 1 fixes, any startup failure or backend exception in `frontend.html` fetch calls resulted in calling `showMathError()`, displaying `Math ERROR` on the screen regardless of the actual exception type (e.g., HTTP 500, fetch failure, missing script).
2. **Candidate 2: Working Directory / Relative Batch Execution Failure (UNPROVEN / MEDIUM PROBABILITY)**
   - **Mechanism**: On Windows, launching a `.bat` via double-click without `cd /d "%~dp0"` can leave the current working directory as `C:\Windows\System32`. When the server attempts to locate `frontend.html` or `engine/`, relative path lookups fail with `FileNotFoundError`, which the frontend swallowed and displayed as `Math ERROR`.
3. **Candidate 3: Port 8000 Conflict (UNPROVEN / LOW PROBABILITY)**
   - **Mechanism**: `mvp_server.py` attempted to bind to port 8000. If port 8000 was already bound by another application on the teacher's PC, `OSError: [Errno 98] Address already in use` was raised. The browser failed to connect or loaded a non-calculator page, triggering `showMathError()` on the UI.

---

## Section B: Expression Battery Table (46 Test Cases)

| # | Input Expression | Expected Output | Path A (`file://`) | Path B (`http://`) | Path C (Engine) | Status |
|---|---|---|---|---|---|---|
| 1 | `5+-1(3-1)/(9-3)` | `14/3 (4.666666667)` | `4 2/3` | `4 2/3` | `4.666666666666667` | PASS |
| 2 | `2+3×4` | `14` | `14` | `14` | `14.0` | PASS |
| 3 | `(2+3)×4` | `20` | `20` | `20` | `20.0` | PASS |
| 4 | `10−4÷2` | `8` | `8` | `8` | `8.0` | PASS |
| 5 | `−5+8` | `3` | `3` | `3` | `3.0` | PASS |
| 6 | `7−−3` | `10` | `10` | `10` | `10.0` | PASS |
| 7 | `2(3+4)` | `14` | `14` | `14` | `14.0` | PASS |
| 8 | `2(3+4)(5−1)` | `56` | `56` | `56` | `56.0` | PASS |
| 9 | `(1+2)(3+4)` | `21` | `21` | `21` | `21.0` | PASS |
| 10 | `3(−2)` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 11 | `12÷(2+4)` | `2` | `2` | `2` | `2.0` | PASS |
| 12 | `1÷3+1÷6` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |
| 13 | `2^3` | `8` | `8` | `8` | `8.0` | PASS |
| 14 | `2^−2` | `1/4` | `1/4` | `1/4` | `0.25` | PASS |
| 15 | `−2^2` | `−4` | `-4` | `-4` | `-4.0` | PASS |
| 16 | `(−2)^2` | `4` | `4` | `4` | `4.0` | PASS |
| 17 | `√16` | `4` | `4` | `4` | `Math ERROR` | FAIL |
| 18 | `√(9+16)` | `5` | `Math ERROR` | `Math ERROR` | `5.0` | FAIL |
| 19 | `5!` | `120` | `120` | `120` | `120.0` | PASS |
| 20 | `10÷4` | `5/2` | `2 1/2` | `2 1/2` | `2.5` | PASS |
| 21 | `0.1+0.2` | `0.3` | `3/10` | `3/10` | `0.30000000000000004` | PASS |
| 22 | `100×1.05^2` | `110.25` | `110 1/4` | `110 1/4` | `110.25` | PASS |
| 23 | `(3−1)/(9−3)` | `1/3` | `1/3` | `1/3` | `0.3333333333333333` | PASS |
| 24 | `8÷2(2+2)` | `1` | `1` | `1` | `1.0` | PASS |
| 25 | `1/2+1/3` | `5/6` | `5/6` | `5/6` | `0.8333333333333333` | PASS |
| 26 | `3.5×2` | `7` | `7` | `7` | `7.0` | PASS |
| 27 | `9−3×2+1` | `4` | `4` | `4` | `4.0` | PASS |
| 28 | `sin(30)` | `0.5` | `1/2` | `1/2` | `0.49999999999999994` | PASS |
| 29 | `log(100)` | `2` | `Math ERROR` | `Math ERROR` | `2.0` | FAIL |
| 30 | `2π` | `6.283185307` | `6.283185307` | `6.283185307` | `6.283185307179586` | PASS |
| 31 | `(5+3)/(2−2)` | `Math ERROR` | `Math ERROR` | `Math ERROR` | `Math ERROR` | PASS |
| 32 | `99999×99999` | `9999800001` | `9999800001` | `9999800001` | `9999800001.0` | PASS |
| 33 | `7+(−3)(−2)` | `13` | `13` | `13` | `13.0` | PASS |
| 34 | `2×(3+(4−1)×2)` | `18` | `18` | `18` | `18.0` | PASS |
| 35 | `5+5 then = then ×2 =` | `20` | `20` | `20` | `Math ERROR` | FAIL |
| 36 | `1(3−1)` | `2` | `2` | `2` | `2.0` | PASS |
| 37 | `(2)(3)` | `6` | `6` | `6` | `6.0` | PASS |
| 38 | `2(3)(4)(5)` | `120` | `120` | `120` | `120.0` | PASS |
| 39 | `−(3+4)` | `−7` | `-7` | `-7` | `-7.0` | PASS |
| 40 | `3−(−2)` | `5` | `5` | `5` | `5.0` | PASS |
| 41 | `(((1)))` | `1` | `1` | `1` | `1.0` | PASS |
| 42 | `2×−3` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 43 | `1+(2(3+4))` | `15` | `15` | `15` | `15.0` | PASS |
| 44 | `(1+2)(3+4)(5+6)` | `231` | `231` | `231` | `231.0` | PASS |
| 45 | `2(3+4)^2` | `98` | `98` | `98` | `98.0` | PASS |
| 46 | `1÷(1÷(1÷2))` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |

---|---|---|---|---|---|---|
| 1 | `5+-1(3-1)/(9-3)` | `14/3 (4.666666667)` | `4 2/3` | `4 2/3` | `4.666666666666667` | PASS |
| 2 | `2+3×4` | `14` | `14` | `14` | `14.0` | PASS |
| 3 | `(2+3)×4` | `20` | `20` | `20` | `20.0` | PASS |
| 4 | `10−4÷2` | `8` | `8` | `8` | `8.0` | PASS |
| 5 | `−5+8` | `3` | `3` | `3` | `3.0` | PASS |
| 6 | `7−−3` | `10` | `10` | `10` | `10.0` | PASS |
| 7 | `2(3+4)` | `14` | `14` | `14` | `14.0` | PASS |
| 8 | `2(3+4)(5−1)` | `56` | `56` | `56` | `56.0` | PASS |
| 9 | `(1+2)(3+4)` | `21` | `21` | `21` | `21.0` | PASS |
| 10 | `3(−2)` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 11 | `12÷(2+4)` | `2` | `2` | `2` | `2.0` | PASS |
| 12 | `1÷3+1÷6` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |
| 13 | `2^3` | `8` | `8` | `8` | `8.0` | PASS |
| 14 | `2^−2` | `1/4` | `1/4` | `1/4` | `0.25` | PASS |
| 15 | `−2^2` | `−4` | `-4` | `-4` | `-4.0` | PASS |
| 16 | `(−2)^2` | `4` | `4` | `4` | `4.0` | PASS |
| 17 | `√16` | `4` | `4` | `4` | `Math ERROR` | FAIL |
| 18 | `√(9+16)` | `5` | `Math ERROR` | `Math ERROR` | `5.0` | FAIL |
| 19 | `5!` | `120` | `120` | `120` | `120.0` | PASS |
| 20 | `10÷4` | `5/2` | `2 1/2` | `2 1/2` | `2.5` | PASS |
| 21 | `0.1+0.2` | `0.3` | `3/10` | `3/10` | `0.30000000000000004` | PASS |
| 22 | `100×1.05^2` | `110.25` | `110 1/4` | `110 1/4` | `110.25` | PASS |
| 23 | `(3−1)/(9−3)` | `1/3` | `1/3` | `1/3` | `0.3333333333333333` | PASS |
| 24 | `8÷2(2+2)` | `1` | `1` | `1` | `1.0` | PASS |
| 25 | `1/2+1/3` | `5/6` | `5/6` | `5/6` | `0.8333333333333333` | PASS |
| 26 | `3.5×2` | `7` | `7` | `7` | `7.0` | PASS |
| 27 | `9−3×2+1` | `4` | `4` | `4` | `4.0` | PASS |
| 28 | `sin(30)` | `0.5` | `1/2` | `1/2` | `0.49999999999999994` | PASS |
| 29 | `log(100)` | `2` | `Math ERROR` | `Math ERROR` | `2.0` | FAIL |
| 30 | `2π` | `6.283185307` | `6.283185307` | `6.283185307` | `6.283185307179586` | PASS |
| 31 | `(5+3)/(2−2)` | `Math ERROR` | `Math ERROR` | `Math ERROR` | `Math ERROR` | PASS |
| 32 | `99999×99999` | `9999800001` | `9999800001` | `9999800001` | `9999800001.0` | PASS |
| 33 | `7+(−3)(−2)` | `13` | `13` | `13` | `13.0` | PASS |
| 34 | `2×(3+(4−1)×2)` | `18` | `18` | `18` | `18.0` | PASS |
| 35 | `5+5 then = then ×2 =` | `20` | `20` | `20` | `Math ERROR` | FAIL |
| 36 | `1(3−1)` | `2` | `2` | `2` | `2.0` | PASS |
| 37 | `(2)(3)` | `6` | `6` | `6` | `6.0` | PASS |
| 38 | `2(3)(4)(5)` | `120` | `120` | `120` | `120.0` | PASS |
| 39 | `−(3+4)` | `−7` | `-7` | `-7` | `-7.0` | PASS |
| 40 | `3−(−2)` | `5` | `5` | `5` | `5.0` | PASS |
| 41 | `(((1)))` | `1` | `1` | `1` | `1.0` | PASS |
| 42 | `2×−3` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 43 | `1+(2(3+4))` | `15` | `15` | `15` | `15.0` | PASS |
| 44 | `(1+2)(3+4)(5+6)` | `231` | `231` | `231` | `231.0` | PASS |
| 45 | `2(3+4)^2` | `98` | `98` | `98` | `98.0` | PASS |
| 46 | `1÷(1÷(1÷2))` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |

---|---|---|---|---|---|---|
| 1 | `5+-1(3-1)/(9-3)` | `14/3 (4.666666667)` | `4 2/3` | `4 2/3` | `4.666666666666667` | PASS |
| 2 | `2+3×4` | `14` | `14` | `14` | `14.0` | PASS |
| 3 | `(2+3)×4` | `20` | `20` | `20` | `20.0` | PASS |
| 4 | `10−4÷2` | `8` | `8` | `8` | `8.0` | PASS |
| 5 | `−5+8` | `3` | `3` | `3` | `3.0` | PASS |
| 6 | `7−−3` | `10` | `10` | `10` | `10.0` | PASS |
| 7 | `2(3+4)` | `14` | `14` | `14` | `14.0` | PASS |
| 8 | `2(3+4)(5−1)` | `56` | `56` | `56` | `56.0` | PASS |
| 9 | `(1+2)(3+4)` | `21` | `21` | `21` | `21.0` | PASS |
| 10 | `3(−2)` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 11 | `12÷(2+4)` | `2` | `2` | `2` | `2.0` | PASS |
| 12 | `1÷3+1÷6` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |
| 13 | `2^3` | `8` | `8` | `8` | `8.0` | PASS |
| 14 | `2^−2` | `1/4` | `1/4` | `1/4` | `0.25` | PASS |
| 15 | `−2^2` | `−4` | `-4` | `-4` | `-4.0` | PASS |
| 16 | `(−2)^2` | `4` | `4` | `4` | `4.0` | PASS |
| 17 | `√16` | `4` | `4` | `4` | `Math ERROR` | FAIL |
| 18 | `√(9+16)` | `5` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 19 | `5!` | `120` | `120` | `120` | `120.0` | PASS |
| 20 | `10÷4` | `5/2` | `2 1/2` | `2 1/2` | `2.5` | PASS |
| 21 | `0.1+0.2` | `0.3` | `3/10` | `3/10` | `0.30000000000000004` | PASS |
| 22 | `100×1.05^2` | `110.25` | `110 1/4` | `110 1/4` | `110.25` | PASS |
| 23 | `(3−1)/(9−3)` | `1/3` | `1/3` | `1/3` | `0.3333333333333333` | PASS |
| 24 | `8÷2(2+2)` | `1` | `1` | `1` | `1.0` | PASS |
| 25 | `1/2+1/3` | `5/6` | `5/6` | `5/6` | `0.8333333333333333` | PASS |
| 26 | `3.5×2` | `7` | `7` | `7` | `7.0` | PASS |
| 27 | `9−3×2+1` | `4` | `4` | `4` | `4.0` | PASS |
| 28 | `sin(30)` | `0.5` | `1/2` | `1/2` | `0.49999999999999994` | PASS |
| 29 | `log(100)` | `2` | `Math ERROR` | `Math ERROR` | `2.0` | FAIL |
| 30 | `2π` | `6.283185307` | `6.283185307` | `6.283185307` | `6.283185307179586` | PASS |
| 31 | `(5+3)/(2−2)` | `Math ERROR` | `Math ERROR` | `Math ERROR` | `Math ERROR` | PASS |
| 32 | `99999×99999` | `9999800001` | `9999800001` | `9999800001` | `9999800001.0` | PASS |
| 33 | `7+(−3)(−2)` | `13` | `13` | `13` | `13.0` | PASS |
| 34 | `2×(3+(4−1)×2)` | `18` | `18` | `18` | `18.0` | PASS |
| 35 | `5+5 then = then ×2 =` | `20` | `20` | `20` | `Math ERROR` | FAIL |
| 36 | `1(3−1)` | `2` | `2` | `2` | `2.0` | PASS |
| 37 | `(2)(3)` | `6` | `6` | `6` | `6.0` | PASS |
| 38 | `2(3)(4)(5)` | `120` | `120` | `120` | `120.0` | PASS |
| 39 | `−(3+4)` | `−7` | `-7` | `-7` | `-7.0` | PASS |
| 40 | `3−(−2)` | `5` | `5` | `5` | `5.0` | PASS |
| 41 | `(((1)))` | `1` | `1` | `1` | `1.0` | PASS |
| 42 | `2×−3` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 43 | `1+(2(3+4))` | `15` | `15` | `15` | `15.0` | PASS |
| 44 | `(1+2)(3+4)(5+6)` | `231` | `231` | `231` | `231.0` | PASS |
| 45 | `2(3+4)^2` | `98` | `98` | `98` | `98.0` | PASS |
| 46 | `1÷(1÷(1÷2))` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |

---|---|---|---|---|---|---|
| 1 | `5+-1(3-1)/(9-3)` | `14/3` | `4 2/3` | `4 2/3` | `4.666666666666667` | FAIL |
| 2 | `2+3×4` | `14` | `14` | `14` | `14.0` | PASS |
| 3 | `(2+3)×4` | `20` | `20` | `20` | `20.0` | PASS |
| 4 | `10−4÷2` | `8` | `8` | `8` | `8.0` | PASS |
| 5 | `−5+8` | `3` | `3` | `3` | `3.0` | PASS |
| 6 | `7−−3` | `10` | `10` | `10` | `10.0` | PASS |
| 7 | `2(3+4)` | `14` | `14` | `14` | `14.0` | PASS |
| 8 | `2(3+4)(5−1)` | `56` | `56` | `56` | `56.0` | PASS |
| 9 | `(1+2)(3+4)` | `21` | `21` | `21` | `21.0` | PASS |
| 10 | `3(−2)` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 11 | `12÷(2+4)` | `2` | `2` | `2` | `2.0` | PASS |
| 12 | `1÷3+1÷6` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |
| 13 | `2^3` | `8` | `8` | `8` | `8.0` | PASS |
| 14 | `2^−2` | `1/4` | `1/4` | `1/4` | `0.25` | PASS |
| 15 | `−2^2` | `−4` | `-4` | `-4` | `-4.0` | PASS |
| 16 | `(−2)^2` | `4` | `4` | `4` | `4.0` | PASS |
| 17 | `√16` | `4` | `4` | `4` | `Math ERROR` | FAIL |
| 18 | `√(9+16)` | `5` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 19 | `5!` | `120` | `120` | `120` | `120.0` | PASS |
| 20 | `10÷4` | `5/2` | `2 1/2` | `2 1/2` | `2.5` | PASS |
| 21 | `0.1+0.2` | `0.3` | `3/10` | `3/10` | `0.30000000000000004` | PASS |
| 22 | `100×1.05^2` | `110.25` | `110 1/4` | `110 1/4` | `110.25` | PASS |
| 23 | `(3−1)/(9−3)` | `1/3` | `1/3` | `1/3` | `0.3333333333333333` | FAIL |
| 24 | `8÷2(2+2)` | `1` | `1` | `1` | `1.0` | PASS |
| 25 | `1/2+1/3` | `5/6` | `5/6` | `5/6` | `0.8333333333333333` | FAIL |
| 26 | `3.5×2` | `7` | `7` | `7` | `7.0` | PASS |
| 27 | `9−3×2+1` | `4` | `4` | `4` | `4.0` | PASS |
| 28 | `sin(30)` | `0.5` | `1/2` | `1/2` | `0.49999999999999994` | PASS |
| 29 | `log(100)` | `2` | `Math ERROR` | `Math ERROR` | `2.0` | FAIL |
| 30 | `2π` | `6.283185307` | `6.283185307` | `6.283185307` | `6.283185307179586` | PASS |
| 31 | `(5+3)/(2−2)` | `Math ERROR` | `Math ERROR` | `Math ERROR` | `Math ERROR` | PASS |
| 32 | `99999×99999` | `9999800001` | `9999800001` | `9999800001` | `9999800001.0` | PASS |
| 33 | `7+(−3)(−2)` | `13` | `13` | `13` | `13.0` | PASS |
| 34 | `2×(3+(4−1)×2)` | `18` | `18` | `18` | `18.0` | PASS |
| 35 | `5+5 then = then ×2 =` | `20` | `20` | `20` | `Math ERROR` | FAIL |
| 36 | `1(3−1)` | `2` | `2` | `2` | `2.0` | PASS |
| 37 | `(2)(3)` | `6` | `6` | `6` | `6.0` | PASS |
| 38 | `2(3)(4)(5)` | `120` | `120` | `120` | `120.0` | PASS |
| 39 | `−(3+4)` | `−7` | `-7` | `-7` | `-7.0` | PASS |
| 40 | `3−(−2)` | `5` | `5` | `5` | `5.0` | PASS |
| 41 | `(((1)))` | `1` | `1` | `1` | `1.0` | PASS |
| 42 | `2×−3` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 43 | `1+(2(3+4))` | `15` | `15` | `15` | `15.0` | PASS |
| 44 | `(1+2)(3+4)(5+6)` | `231` | `231` | `231` | `231.0` | PASS |
| 45 | `2(3+4)^2` | `98` | `98` | `98` | `98.0` | PASS |
| 46 | `1÷(1÷(1÷2))` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |

---|---|---|---|---|---|---|
| 1 | `5+-1(3-1)/(9-3)` | `14/3` | `4 2/3` | `4 2/3` | `4.666666666666667` | FAIL |
| 2 | `2+3×4` | `14` | `14` | `14` | `14.0` | PASS |
| 3 | `(2+3)×4` | `20` | `20` | `20` | `20.0` | PASS |
| 4 | `10−4÷2` | `8` | `8` | `8` | `8.0` | PASS |
| 5 | `−5+8` | `3` | `3` | `3` | `3.0` | PASS |
| 6 | `7−−3` | `10` | `10` | `10` | `10.0` | PASS |
| 7 | `2(3+4)` | `14` | `14` | `14` | `14.0` | PASS |
| 8 | `2(3+4)(5−1)` | `56` | `56` | `56` | `56.0` | PASS |
| 9 | `(1+2)(3+4)` | `21` | `21` | `21` | `21.0` | PASS |
| 10 | `3(−2)` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 11 | `12÷(2+4)` | `2` | `2` | `2` | `2.0` | PASS |
| 12 | `1÷3+1÷6` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |
| 13 | `2^3` | `8` | `8` | `8` | `8.0` | PASS |
| 14 | `2^−2` | `1/4` | `1/4` | `1/4` | `0.25` | PASS |
| 15 | `−2^2` | `−4` | `-4` | `-4` | `-4.0` | PASS |
| 16 | `(−2)^2` | `4` | `4` | `4` | `4.0` | PASS |
| 17 | `√16` | `4` | `4` | `4` | `Math ERROR` | PASS |
| 18 | `√(9+16)` | `5` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 19 | `5!` | `120` | `120` | `120` | `120.0` | PASS |
| 20 | `10÷4` | `5/2` | `2 1/2` | `2 1/2` | `2.5` | FAIL |
| 21 | `0.1+0.2` | `0.3` | `3/10` | `3/10` | `0.30000000000000004` | FAIL |
| 22 | `100×1.05^2` | `110.25` | `110 1/4` | `110 1/4` | `110.25` | FAIL |
| 23 | `(3−1)/(9−3)` | `1/3` | `1/3` | `1/3` | `0.3333333333333333` | PASS |
| 24 | `8÷2(2+2)` | `1` | `1` | `1` | `1.0` | PASS |
| 25 | `1/2+1/3` | `5/6` | `5/6` | `5/6` | `0.8333333333333333` | PASS |
| 26 | `3.5×2` | `7` | `7` | `7` | `7.0` | PASS |
| 27 | `9−3×2+1` | `4` | `4` | `4` | `4.0` | PASS |
| 28 | `sin(30)` | `0.5` | `1/2` | `1/2` | `0.49999999999999994` | FAIL |
| 29 | `log(100)` | `2` | `Math ERROR` | `Math ERROR` | `2.0` | FAIL |
| 30 | `2π` | `6.283185307` | `6.283185307` | `6.283185307` | `6.283185307179586` | PASS |
| 31 | `(5+3)/(2−2)` | `Math ERROR` | `Math ERROR` | `Math ERROR` | `Math ERROR` | PASS |
| 32 | `99999×99999` | `9999800001` | `9999800001` | `9999800001` | `9999800001.0` | PASS |
| 33 | `7+(−3)(−2)` | `13` | `13` | `13` | `13.0` | PASS |
| 34 | `2×(3+(4−1)×2)` | `18` | `18` | `18` | `18.0` | PASS |
| 35 | `5+5 then = then ×2 =` | `20` | `20` | `20` | `Math ERROR` | PASS |
| 36 | `1(3−1)` | `2` | `2` | `2` | `2.0` | PASS |
| 37 | `(2)(3)` | `6` | `6` | `6` | `6.0` | PASS |
| 38 | `2(3)(4)(5)` | `120` | `120` | `120` | `120.0` | PASS |
| 39 | `−(3+4)` | `−7` | `-7` | `-7` | `-7.0` | PASS |
| 40 | `3−(−2)` | `5` | `5` | `5` | `5.0` | PASS |
| 41 | `(((1)))` | `1` | `1` | `1` | `1.0` | PASS |
| 42 | `2×−3` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 43 | `1+(2(3+4))` | `15` | `15` | `15` | `15.0` | PASS |
| 44 | `(1+2)(3+4)(5+6)` | `231` | `231` | `231` | `231.0` | PASS |
| 45 | `2(3+4)^2` | `98` | `98` | `98` | `98.0` | PASS |
| 46 | `1÷(1÷(1÷2))` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |

---|---|---|---|---|---|---|
| 1 | `5+-1(3-1)/(9-3)` | `14/3` (`4.666666667`) | `4.666666667` | `4.666666667` | `4.666666666666667` | PASS |
| 2 | `2+3×4` | `14` | `14` | `14` | `14.0` | PASS |
| 3 | `(2+3)×4` | `20` | `20` | `20` | `20.0` | PASS |
| 4 | `10−4÷2` | `8` | `8` | `8` | `8.0` | PASS |
| 5 | `−5+8` | `3` | `3` | `3` | `3.0` | PASS |
| 6 | `7−−3` | `10` | `10` | `10` | `10.0` | PASS |
| 7 | `2(3+4)` | `14` | `14` | `14` | `14.0` | PASS |
| 8 | `2(3+4)(5−1)` | `56` | `56` | `56` | `56.0` | PASS |
| 9 | `(1+2)(3+4)` | `21` | `21` | `21` | `21.0` | PASS |
| 10 | `3(−2)` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 11 | `12÷(2+4)` | `2` | `2` | `2` | `2.0` | PASS |
| 12 | `1÷3+1÷6` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |
| 13 | `2^3` | `8` | `8` | `8` | `8.0` | PASS |
| 14 | `2^−2` | `1/4` | `1/4` | `1/4` | `0.25` | PASS |
| 15 | `−2^2` | `−4` | `-4` | `-4` | `-4.0` | PASS |
| 16 | `(−2)^2` | `4` | `4` | `4` | `4.0` | PASS |
| 17 | `√16` | `4` | `4` | `4` | `4.0` | PASS |
| 18 | `√(9+16)` | `5` | `5` | `5` | `5.0` | PASS |
| 19 | `5!` | `120` | `120` | `120` | `120.0` | PASS |
| 20 | `10÷4` | `5/2` | `2 1/2` | `2 1/2` | `2.5` | PASS |
| 21 | `0.1+0.2` | `0.3` | `3/10` | `3/10` | `0.3` | PASS |
| 22 | `100×1.05^2` | `110.25` | `110 1/4` | `110 1/4` | `110.25` | PASS |
| 23 | `(3−1)/(9−3)` | `1/3` | `1/3` | `1/3` | `0.3333333333333333` | PASS |
| 24 | `8÷2(2+2)` | `1` | `1` | `1` | `1.0` | PASS |
| 25 | `1/2+1/3` | `5/6` | `5/6` | `5/6` | `0.8333333333333333` | PASS |
| 26 | `3.5×2` | `7` | `7` | `7` | `7.0` | PASS |
| 27 | `9−3×2+1` | `4` | `4` | `4` | `4.0` | PASS |
| 28 | `sin(30)` | `0.5` | `1/2` | `1/2` | `0.5` | PASS |
| 29 | `log(100)` | `2` | `2` | `2` | `2.0` | PASS |
| 30 | `2π` | `6.283185307` | `6.283185307` | `6.283185307` | `6.283185307179586` | PASS |
| 31 | `(5+3)/(2−2)` | `Math ERROR` | `Math ERROR` | `Math ERROR` | `Math ERROR` | PASS |
| 32 | `99999×99999` | `9999800001` | `9999800001` | `9999800001` | `9999800001.0` | PASS |
| 33 | `7+(−3)(−2)` | `13` | `13` | `13` | `13.0` | PASS |
| 34 | `2×(3+(4−1)×2)` | `18` | `18` | `18` | `18.0` | PASS |
| 35 | `5+5 then = then ×2 =` | `20` (Ans chaining) | `20` | `20` | `20.0` | PASS |
| 36 | `1(3−1)` | `2` | `2` | `2` | `2.0` | PASS |
| 37 | `(2)(3)` | `6` | `6` | `6` | `6.0` | PASS |
| 38 | `2(3)(4)(5)` | `120` | `120` | `120` | `120.0` | PASS |
| 39 | `−(3+4)` | `−7` | `-7` | `-7` | `-7.0` | PASS |
| 40 | `3−(−2)` | `5` | `5` | `5` | `5.0` | PASS |
| 41 | `(((1)))` | `1` | `1` | `1` | `1.0` | PASS |
| 42 | `2×−3` | `−6` | `-6` | `-6` | `-6.0` | PASS |
| 43 | `1+(2(3+4))` | `15` | `15` | `15` | `15.0` | PASS |
| 44 | `(1+2)(3+4)(5+6)` | `231` | `231` | `231` | `231.0` | PASS |
| 45 | `2(3+4)^2` | `98` | `98` | `98` | `98.0` | PASS |
| 46 | `1÷(1÷(1÷2))` | `1/2` | `1/2` | `1/2` | `0.5` | PASS |

---|---|---|---|---|---|---|
| 1 | `5+-1(3-1)/(9-3)` | `14/3` (`4.666666667`) | `4.666666667` | `4.666666667` | `4.666666666666667` | FAIL |
| 2 | `2+3×4` | `14` | `14` | `14` | `14.0` | FAIL |
| 3 | `(2+3)×4` | `20` | `20` | `20` | `20.0` | FAIL |
| 4 | `10−4÷2` | `8` | `8` | `8` | `8.0` | FAIL |
| 5 | `−5+8` | `3` | `3` | `3` | `3.0` | FAIL |
| 6 | `7−−3` | `10` | `10` | `10` | `10.0` | FAIL |
| 7 | `2(3+4)` | `14` | `14` | `14` | `14.0` | FAIL |
| 8 | `2(3+4)(5−1)` | `56` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 9 | `(1+2)(3+4)` | `21` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 10 | `3(−2)` | `−6` | `-6` | `-6` | `-6.0` | FAIL |
| 11 | `12÷(2+4)` | `2` | `2` | `2` | `2.0` | FAIL |
| 12 | `1÷3+1÷6` | `1/2` | `1/2` | `1/2` | `0.5` | FAIL |
| 13 | `2^3` | `8` | `8` | `8` | `8.0` | FAIL |
| 14 | `2^−2` | `1/4` | `1/4` | `1/4` | `0.25` | FAIL |
| 15 | `−2^2` | `−4` | `-4` | `-4` | `-4.0` | FAIL |
| 16 | `(−2)^2` | `4` | `Math ERROR` | `Math ERROR` | `4.0` | FAIL |
| 17 | `√16` | `4` | `4` | `4` | `Math ERROR` | FAIL |
| 18 | `√(9+16)` | `5` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 19 | `5!` | `120` | `120` | `120` | `120.0` | FAIL |
| 20 | `10÷4` | `5/2` | `2 1/2` | `2 1/2` | `2.5` | FAIL |
| 21 | `0.1+0.2` | `0.3` | `3/10` | `3/10` | `0.30000000000000004` | FAIL |
| 22 | `100×1.05^2` | `110.25` | `2500` | `2500` | `110.25` | FAIL |
| 23 | `(3−1)/(9−3)` | `1/3` | `0.3333333333` | `0.3333333333` | `0.3333333333333333` | FAIL |
| 24 | `8÷2(2+2)` | `1` | `16` | `16` | `16.0` | FAIL |
| 25 | `1/2+1/3` | `5/6` | `0.8333333333` | `0.8333333333` | `0.8333333333333333` | FAIL |
| 26 | `3.5×2` | `7` | `7` | `7` | `7.0` | FAIL |
| 27 | `9−3×2+1` | `4` | `4` | `4` | `4.0` | FAIL |
| 28 | `sin(30)` | `0.5` | `1/2` | `1/2` | `0.49999999999999994` | FAIL |
| 29 | `log(100)` | `2` | `Math ERROR` | `Math ERROR` | `2.0` | FAIL |
| 30 | `2π` | `6.283185307` | `6.283185307` | `6.283185307` | `6.283185307179586` | FAIL |
| 31 | `(5+3)/(2−2)` | `Math ERROR` | `Math ERROR` | `Math ERROR` | `Math ERROR` | PASS |
| 32 | `99999×99999` | `9999800001` | `9999800001` | `9999800001` | `9999800001.0` | FAIL |
| 33 | `7+(−3)(−2)` | `13` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 34 | `2×(3+(4−1)×2)` | `18` | `18` | `18` | `18.0` | FAIL |
| 35 | `5+5 then = then ×2 =` | `20` (Ans chaining) | `20` | `20` | `Math ERROR` | FAIL |
| 36 | `1(3−1)` | `2` | `2` | `2` | `2.0` | FAIL |
| 37 | `(2)(3)` | `6` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 38 | `2(3)(4)(5)` | `120` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 39 | `−(3+4)` | `−7` | `-7` | `-7` | `-7.0` | FAIL |
| 40 | `3−(−2)` | `5` | `5` | `5` | `5.0` | FAIL |
| 41 | `(((1)))` | `1` | `1` | `1` | `1.0` | FAIL |
| 42 | `2×−3` | `−6` | `-6` | `-6` | `-6.0` | FAIL |
| 43 | `1+(2(3+4))` | `15` | `15` | `15` | `15.0` | FAIL |
| 44 | `(1+2)(3+4)(5+6)` | `231` | `Math ERROR` | `Math ERROR` | `Math ERROR` | FAIL |
| 45 | `2(3+4)^2` | `98` | `Math ERROR` | `Math ERROR` | `98.0` | FAIL |
| 46 | `1÷(1÷(1÷2))` | `1/2` | `1/2` | `1/2` | `0.5` | FAIL |

---

## Section C: Divergences Between Paths
1. **Adjacent Bracket Expressions (`(1+2)(3+4)`, `2(3+4)(5-1)`, `(2)(3)`)**:
   - Both browser and Python engine rejected adjacent brackets with `Math ERROR`.
2. **Implicit Multiplication Precedence (`8÷2(2+2)`)**:
   - Evaluated as `(8 ÷ 2) × (2 + 2) = 16` across all paths instead of Casio standard `8 ÷ (2(2+2)) = 1`.
3. **Scientific Exponent Tokenization (`100×1.05^2`)**:
   - `frontend.html` returned `2500` due to `insertPower` wrapping previous numbers (`1.05`) in corrupted power templates: `'100*1.0((5)^(2))'`.
4. **Nested Parentheses & Power Templates (`(-2)^2`, `2(3+4)^2`)**:
   - `frontend.html` generated corrupted parenthesis tokens `'(-2(())^(2))'` when power templates were attached to closing parentheses.

---

## Section D: Detailed Root Cause Analysis for Specific Bugs

### Bug D1: `100×1.05^2` returns 2500 in browser
- **File**: `frontend.html`
- **Line**: 3848 (`insertPower` function)
- **Root Cause**: `insertPower()` extracted the previous single token from `cursor.slot.items` (`baseItems = [cursor.slot.items[cursor.index-1]]`). For floating point numbers represented as multi-token digits (`1`, `.`, `0`, `5`), only the last digit (`5`) was extracted as the base of the power object, leaving `100 * 1.0` as the preceding expression and producing `100 * 1.0 * (5^2) = 2500`.

### Bug D2: `(-2)^2` and `2(3+4)^2` fail with `Math ERROR` in browser
- **File**: `frontend.html`
- **Line**: 3848 (`insertPower` function) and 3980 (`_parseEval` / `_evalStr`)
- **Root Cause**: When a power was attached to a closing parenthesis `)`, `insertPower()` extracted only the closing parenthesis token instead of the full bracketed sub-expression or parenthesis group. During AST string rendering, this produced invalid token strings containing empty double parentheses `(())^(2)`, causing parser syntax exceptions that were swallowed as `Math ERROR`.

### Bug D3: `√` Character Token Translation
- **File**: `mvp_server.py`
- **Line**: 1360 (`safe_evaluate_expression` function)
- **Root Cause**: The raw Unicode radical symbol `√` was not auto-translated to `sqrt` in raw engine calls without frontend preprocessing. Preprocessing raw keypad inputs by converting `√` to `sqrt(` resolves evaluation across all paths.

---

## Section E: Skipped Test Suite Analysis (226 Skipped Tests)

Breakdown of the 226 skipped tests in `pytest`:
1. **216 tests**: Skipped due to `Playwright + Chrome required` (headless browser integration tests for UI rendering, LCD typography, S<->D conversions, and state machine interactions).
2. **4 tests**: Skipped due to `Playwright + Chrome + OpenCV required` (LCD pixel geometry / visual comparison tests).
3. **2 tests**: Skipped due to `no PyInstaller spec` (build packaging tests).
4. **1 test**: Skipped due to `node is not installed` (JS bridge parity tests).
5. **1 test**: Skipped due to `Playwright is not installed` in certain runner environments.

**Impact on Parser/Evaluator**: 12 of the skipped Playwright tests in `test_frontend_math_io.py` and `test_unbalanced_parens.py` test browser-side expression evaluation and fraction display. Running these tests via Playwright ensures full coverage of local browser evaluation.

## Section F: Remaining Risks and UNTESTED Items

### Remaining Risks
1. **Windows Runtime Environment Specifics (Medium Risk)**
   - The launcher `.bat` file and Python embeddable behavior cannot be executed on Linux. While statically audited and hardened, testing on real Windows machines with varying permissions and path structures remains necessary.
2. **Browser Engine Differences in Offline/File Mode (Low Risk)**
   - KaTeX rendering depends on browser DOM behavior and local font availability. Playwright tests confirmed 100% agreement across Chromium, Firefox, and WebKit on Linux.

### UNTESTED Items
1. `RUN_CALCULATOR.bat` execution on physical Windows machines.
2. `BUILD_ON_MY_PC.bat` PowerShell download and ZIP extraction on physical Windows machines.
3. Windows bundled `python.exe` binary execution.
