
## PHASE 3: DELIVERABLES & SECTION A DOCUMENTATION
- **Status**: DONE
- **Verified**:
  - `docs/audit/AUDIT_REPORT.md` created with complete 46-case table (Paths A, B, C) and Section A root cause analysis.
  - Documented file and line causes for Bug D1 (`100×1.05^2`), Bug D2 (`(-2)^2`, `2(3+4)^2`), and Bug D3 (`√(9+16)`).
  - Documented full analysis of 226 skipped pytest tests.
  - Updated `README.md` with Casio implicit multiplication precedence rules.
- **Next**: Phase 4a - Automated Test Suite for Battery & Variants.

## PHASE 4A: AUTOMATED TEST SUITE (FAILING BASELINE)
- **Status**: DONE
- **Verified**:
  - Created `test_expression_battery.py` covering all 46 expression battery cases and variant inputs.
  - Baseline execution confirmed expected failures for implicit multiplication precedence and adjacent bracket expressions.
  - Committed test file prior to fix application (`17ec1ef`).
- **Next**: Phase 4b - Modular Fixes (One Concern Per Commit).

## PHASE 4B: MODULAR FIXES
- **Status**: DONE
- **Verified**:
  - Fix 1 (`bc690a5`): Allowed adjacent bracket groups `(1+2)(3+4)` as implicit multiplication.
  - Fix 2 (`92fde39`): Adjusted precedence so implicit multiplication binds tighter than explicit `*` and `/`. Evaluated `8÷2(2+2)` as `1`.
  - Fix 3 (`d18e478`): Fixed power template base extraction in `frontend.html` to extract multi-digit numbers and full bracketed groups. Corrected `100×1.05^2` (110.25), `(-2)^2` (4), and `2(3+4)^2` (98).
  - All 46 automated battery cases in `test_expression_battery.py` now PASS 100%.
  - Pytest results: 501 passed, 226 skipped, 0 failed (increased from 455 baseline due to +46 battery cases).
- **Next**: Phase 4c - Post-Fix 46-Case Re-evaluation across Paths A, B, and C.

## PHASE 4C: POST-FIX RE-EVALUATION
- **Status**: DONE
- **Verified**:
  - Re-ran 46-case battery across Path A (`file://`), Path B (`http://`), and Path C (Python engine).
  - 100% PASS rate achieved across all three paths on all 46 cases.
  - Updated `docs/audit/AUDIT_REPORT.md` Section B with the verified post-fix 46-case table.
- **Next**: Phase 5 - Browser Compatibility Audit.

## PHASE 5: BROWSER COMPATIBILITY
- **Status**: DONE
- **Verified**:
  - Ran cases 1–10 on Path A (`file://`) across Chromium, Firefox, and WebKit using Playwright.
  - All 10 test cases passed with 100% agreement across all three browser engines.
- **Next**: Phase 6 - Support for Windows Release & Hardening.

## PHASE 6: RELEASE SUPPORT & HARDENING
- **Status**: DONE
- **Verified**:
  - Rewrote `RUN_CALCULATOR.bat` with directory navigation (`cd /d "%~dp0"`), quoted relative paths, unbuffered Python logging to `launcher.log`, and clear error instructions. [Marked UNTESTED on Windows].
  - Verified server startup self-test `mvp_server.run_startup_selftest()` passes on Linux.
  - Created `build_release.py` script to package clean releases and verify asset completeness.
- **Next**: Final Verification & Submission.
