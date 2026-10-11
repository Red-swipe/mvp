# Release Acceptance — Casio ClassWiz Emulator

**Date:** 2026-10-12 · **Target release:** 2026-10-15
**Overall verdict: PASS WITH CAVEATS** — one caveat is that the release is **not yet on `main`**; it is a verified, pushed release candidate awaiting review (see *Delivery status*).

---

## 1. What was tested

| Item | Value |
|---|---|
| Repository | `https://github.com/Red-swipe/mvp.git` |
| Branch tested | `frontend_fixes_october` |
| **Verified release commit** | **`a63b6981596bd606705c856133760f6c99d97bd7`** |
| Merge commit integrating `main` | `c872bd6` (`Merge origin/main into frontend_fixes_october`) |
| `origin/main` at test time | `6ca4ead1f3785d946c310216788914f5f44b6e9c` |
| Acceptance clone | `E:\A.G\casio_release_acceptance_20261011` (separate directory; original tree never used as a test clone) |
| Evidence directory | `E:\A.G\casio_release_evidence_20261011` |
| Python toolchain | Self-managed **CPython 3.12.8** at `E:\A.G\casio_release_toolchain\py3128e` |
| Browser | Google Chrome via Playwright (`channel="chrome"`), headless |

### Commits created this session

```
a63b698 fix(tests): derive the repo root in three suites instead of hardcoding it
2c639dd docs(readme): document the portable build and correct the test story
7c93572 chore(gitignore): ignore the generated calculator_portable/ build product
35e9caf docs(frontend): record why the KEY-TRACE-DROP trace is kept
ca0dccd chore: untrack 22 committed .pyc files
c872bd6 Merge origin/main into frontend_fixes_october
75188f7 test(lcd): browser geometry coverage for expression vs result regions
de456d9 fix(lcd): stop clipping the denominator of a stacked-fraction result
929bbbd fix(eqn): DEL must edit a committed simultaneous-equation coefficient
5123a89 fix(file://): S<->D must show the exact fraction, not 333/1000
```

### Initial and final working-tree status

Initial (before any change) and final (after) were both:

```
 M engine/equation/__pycache__/equation_engine.cpython-311.pyc
 M engine/vector/__pycache__/vector_engine.cpython-311.pyc
?? .codex_test_tmp/
?? CLAUDE_HANDOVER.md
?? audit.md
?? calculator_portable/
?? final_audit.md
?? raw/handover.md
```

with the final state adding only `calculator_portable/` moving from listed-untracked to *ignored* (still present on disk, verified running). The two `.pyc` modifications disappeared from the list because they were untracked in commit `ca0dccd` — the files remain on disk untouched. **No user artifact was deleted, reverted, stashed or committed.**

---

## 2. P0-A — Clean-clone portable acceptance: **PASS**

### Build

```
cd E:\A.G\casio_release_acceptance_20261011\portable
cmd /c "BUILD_ON_MY_PC.bat < nul"
→ exit code 0
```

Log: `FINAL_build.log`. `BUILD_ON_MY_PC.bat` sets `OUT=%~dp0..\calculator_portable`, so a clone builds into **its own** directory; the original `E:\A.G\casio_mvp\calculator_portable` was never written to (verified: its `python.exe` still reported `3.12.8` and its mtime was unchanged at `10/10/2026 2:23:48 AM`).

### `[SELFTEST]` transcript (verbatim, from the real launcher at `a63b698`)

```
[SELFTEST] Python executable: E:\A.G\casio_release_acceptance_20261011\calculator_portable\python\python.exe
[SELFTEST] Python version: 3.12.8
[SELFTEST] App directory: E:\A.G\casio_release_acceptance_20261011\calculator_portable
[SELFTEST] Isolated mode (site not loaded): YES
[SELFTEST] sys.path:
[SELFTEST]   E:\A.G\casio_release_acceptance_20261011\calculator_portable
[SELFTEST]   E:\A.G\casio_release_acceptance_20261011\calculator_portable\python\python312.zip
[SELFTEST]   E:\A.G\casio_release_acceptance_20261011\calculator_portable\python
[SELFTEST]   E:\A.G\casio_release_acceptance_20261011\calculator_portable
[SELFTEST] Engine import: OK
[SELFTEST] Engine module: E:\A.G\casio_release_acceptance_20261011\calculator_portable\engine\__init__.py
[SELFTEST] Evaluator source: E:\A.G\casio_release_acceptance_20261011\calculator_portable\engine\evaluator.py
[SELFTEST] Engine wiring: OK
[SELFTEST] Static assets: OK (7 files present, served locally, no CDN required)

  Calculator is running at http://127.0.0.1:8000/
```

Source: `FINAL_launcher_stdout.log` (1197 bytes, 22 lines). stderr: `FINAL_launcher_stderr.log` — **0 bytes**. No `calculator_log.txt` was produced, i.e. no exception was ever logged.

### System-Python independence — **proven, not assumed**

A claim that "the embedded interpreter works" proves nothing on a machine that has a system Python. So the bundled interpreter was run with a deliberately hostile environment (`P0A_isolation_probe.log`):

```
set PATH=C:\Windows\System32      (system Python made undiscoverable)
set PYTHONPATH=  PYTHONHOME=  PYTHONSTARTUP=  PYTHONUSERBASE=

where python  → INFO: Could not find files for the given pattern(s).
where py      → INFO: Could not find files for the given pattern(s).

[SELFTEST] Python version: 3.12.8
[SELFTEST] Isolated mode (site not loaded): YES
[SELFTEST] Engine import: OK
[SELFTEST] Static assets: OK (7 files present, served locally, no CDN required)
SELFTEST_RC=0

site loaded: False
site-packages on path: []
third-party pytest importable: False
```

**Residual environment limitation, stated plainly:** this machine does have a system Python (3.11.15 on `PATH`, plus 3.12.10 via `py -3.12`). No genuinely system-Python-free VM was available. The evidence above is the strongest available substitute: with system Python removed from `PATH`, `sys.path` provably contains only the three `_pth` entries, `site` is not loaded, and no `site-packages` is reachable — so system Python *cannot* be used even accidentally.

### Served assets (all local, correct content types)

| URL | Status | Content-Type | Bytes |
|---|---|---|---|
| `/` | 200 | `text/html` | 418297 |
| `/frontend.html` | 200 | `text/html` | 418297 |
| `/katex/katex.min.js` | 200 | `application/javascript` | 275414 |
| `/katex/katex.min.css` | 200 | `text/css` | 23336 |
| `/katex/fonts/KaTeX_Main-Regular.woff2` | 200 | `font/woff2` | 26272 |
| `/ClassWizFontSet/CASIOClassWizCW01.ttf` | 200 | `font/ttf` | 78324 |
| `/ClassWizFontSet/ClassWizCWDisplay-Regular.woff2` | 200 | `font/ttf` | 53152 |
| `/qrcode/qrcode.js` | 200 | `application/javascript` | 58991 |
| `/health` | 200 | `application/json` | 12 |

**Identity proof** — the served page is not "some HTTP response": it is SHA256-identical to the clone's `frontend.html`, and it carries all four of this session's fixes.

```
disk SHA256  : 11B94A8E8F69617BA43B866DDABDEDAA02A9877776B1F2763B66CE58BE304C0D
served SHA256: 11B94A8E8F69617BA43B866DDABDEDAA02A9877776B1F2763B66CE58BE304C0D
IDENTICAL    : True
  limitFraction helper      : True
  exactFractionString       : True
  DEL committed-coefficient : True
  LCD bottom:8px            : True
```

### Real application path (browser, `FINAL_browser.json`)

Driven with physical key clicks and the real `handleKey` dispatcher — not a direct engine import:

| Case | Result | Error |
|---|---|---|
| Keypad `7 × 8 =` | **56** | none |
| Scientific `√ → 9 =` (template key) | **3** | none |
| Definite integral `∫₀³x² dx` | **9** | none |
| S⇔D `1/3` → → back | `1/3` → `0.3333333333` | none |

- **External network requests: 0** (`external_requests: []`)
- **Page errors: 0**
- Console errors: 1 — the browser's automatic `/favicon.ico` probe. The page references no favicon; **no application asset 404s** (confirmed: a clean load produced *no* 4xx/5xx response at all).
- Screenshots: `GATE_1_7x8.png`, `GATE_2_sqrt9.png`, `GATE_3_integral_template.png`, `GATE_3b_integral_result.png`, `GATE_4_stod.png`, `GATE_full_final.png`

### QR decode evidence — **PASS**

Rendered on the running portable build via the real key path (SHIFT+OPTN), screenshotted, cropped from real pixels and decoded with OpenCV 5.0.0 (`FINAL_qr.json`, `P0A_qr_screen.png`):

```json
{"qrOpen": true, "hasCanvas": true, "px": 74, "styleW": "74px",
 "decoded": ["https://mentisai-delta.vercel.app/"], "decoded_count": 1,
 "DECODE_VERIFIED": true}
```

---

## 3. P0-B — Full test suite under Python 3.12.8: **PASS**

The MSI install of 3.12.8 into `%TEMP%` silently corrupted (`os.py` missing from `Lib`), so the toolchain was rebuilt from the **official 3.12.8 embeddable payload** into a stable path, with `python312._pth` removed so `site`/pip work normally. This is the exact same 3.12.8 the product ships.

```bash
python -m pip install pytest playwright opencv-python-headless pillow numpy fonttools
python -m pytest -q -rs
```

| Run | Tree | Result | Exit |
|---|---|---|---|
| `FINAL_fullsuite.log` | original, `a63b698` | **681 passed, 179 subtests, 0 failed, 0 skipped** | 0 |
| fresh clone, `a63b698` | acceptance clone | **679 passed, 2 skipped, 179 subtests** | 0 |

The 2 skips are `test_lcd_font_scope_and_calculus_slots.py:266,272 — no PyInstaller spec`. Cause is understood and benign: `.gitignore` excludes `*.spec`, so `MentisClassWiz.spec` is absent from any clone. In the original tree those same tests **run and pass** (37 passed for that file). This is the only difference between the two runs.

Baseline before this session was 642 passed + 1 skipped; the extra skip is gone because `fonttools` is now installed, and the added tests account for the rest.

---

## 4. P1-A — `file://` S⇔D fraction divergence: **FIXED**

**Root cause.** `toggleAnswerFormat()`'s `FILE_MODE` branch called `fractionString()`, which pins the denominator at 1000 (`Math.round(|v|*1000)/1000`). The served path instead asks `/api/fraction`, which uses `Fraction(value).limit_denominator(10000)`.

**Reproduced before the fix** (`P1A_repro_BEFORE.json`, real `file://`, `FILE_MODE: true`):

| Expression | Shown after S⇔D | Second S⇔D | Correct |
|---|---|---|---|
| `1/3` | **`333/1000`** | `0.333` | `1/3` → `0.3333333333` |
| `2/3` | **`667/1000`** | `0.667` | `2/3` → `0.6666666667` |
| `7/3` | **`2333/1000`** | `2.333` | `7/3` → `2.333333333` |

The bug was **not only cosmetic**: the second press read `333/1000` back as a number and printed `0.333`, permanently destroying the original precision.

**Fix** (`5123a89`). Added `limitFraction(value, maxDen)` — the same continued-fraction search `Fraction.limit_denominator` uses — and `exactFractionString()`, which mirrors `/api/fraction`'s shape (denominator 1 → plain integer; mixed mode → whole + remainder). `exactSolveFormat()` was deliberately left untouched because it backs SOLVE/EQN with its own 1e-9 tolerance.

**After** (`P1A_repro_AFTER.json`): `1/3`, `2/3`, `7/3`, `1/7` all exact and round-trip back to their original decimals.

**Tests** — `test_s_to_d_file_mode.py`, **17 passed / 12 subtests**. Asserts `appState.result` *and* `appState.lastAnswer` so a correct-looking LCD cannot hide a corrupted value. Covers exact→decimal→exact for repeating fractions, terminating `5/8` and `11/4`, negative and improper fractions, mixed mode, irrational not faked into a short fraction, and agreement with the served `/api/fraction` path.

**No regressions:** `test_output_modes.py`, `test_file_mode.py`, `test_eqn_output.py`, `test_frontend_math_io.py`, `test_issue5_solver.py`, `test_serialize.py` → **95 passed, 4 subtests**, exit 0.

---

## 5. P1-B — DEL on committed simultaneous-equation coefficients: **FIXED**

**Root cause** (`frontend.html:8515`): `else if (rawKey === 'del') eq.inputBuffer=eq.inputBuffer.slice(0,-1);` — a no-op when the buffer is empty. A committed coefficient lived only in `eq.coefficientValues[row][col]`, so the cell rendered blank while the old number remained in state, and pressing `=` silently re-committed the untouched value.

**Fix** (`929bbbd`): DEL on an empty buffer now restores the committed value into the editable buffer **and clears the stored field**, so the value is genuinely replaced rather than retained behind the visible entry.

**Live evidence on the final build** (`FINAL_del.json`, 4-unknown layout, real key handler):

```
layout_4_unknowns                      buffer=''    row0=['','','','','']   cells=['','','','','']
after_committing_3_4_5_6               buffer=''    row0=[3,4,5,6,'']       cells=['3','4','5','6','']
cursor_moved_back_to_field_1            buffer=''    row0=[3,4,5,6,'']       cells=['3','4','5','6','']
AFTER_DEL_restores_3_and_clears_field   buffer='4'   row0=[3,'',5,6,'']      cells=['3','4','5','6','']
after_second_del_erases_buffer          buffer=''    row0=[3,'',5,6,'']      cells=['3','','5','6','']
after_recommitting_9                    buffer=''    row0=[3,9,5,6,'']       cells=['3','9','5','6','']
```

The stored array and the rendered cells agree at every step — a blank cell never hides a retained value. Screenshots: `P1B_1_committed.png`, `P1B_2_after_del_restored.png` (shows the restored value in the highlighted cell), `P1B_3_recommitted_9.png`.

**Tests** — `test_eqn_del_coefficient.py`, **10 passed / 3 subtests**. Browser-level, driving the real key handler and asserting both the rendered `.eq-field` text and `eq.coefficientValues`. Covers 2-, 3- and 4-unknown layouts, retype-and-recommit, full erase, neighbour isolation, navigation after a DEL cycle, and DEL on an untouched field.

**Regression proof:** with the old one-liner restored, **7 tests fail**; with the fix, all 10 pass.

**No regressions:** `test_eqn_simultaneous.py`, `test_eqn_output.py`, `test_equation_workflow.py`, `test_issue5_solver.py`, `test_issue5_backend_solver.py`, `test_state_machine.py`, `test_issue4_editing.py` → **104 passed, 36 subtests**, exit 0.

---

## 6. P1-C — LCD expression/result positioning: **COVERAGE ADDED + DEFECT FIXED**

### The measurement that drove the work

Real geometry at a 520×1000 viewport, short expression:

| Element | top → bottom |
|---|---|
| `.lcd` | 262.00 → 365.00 (h=103) |
| `.lcd-status-bar` | 267.00 → 279.00 (h=12) |
| `.lcd-expr-viewport` | 279.00 → 337.00 (h=58) |
| `.lcd-expr-content` | 281.00 → 304.56 |
| visible expression **ink** | 277.00 → 300.00 |
| `.lcd-result-line` box | 331.52 → 358.00 |
| result **ink** | 333.52 → 354.52 |

**A trap avoided.** Because `.lcd-result-line` is *absolutely positioned*, its **box** (top 331.52) sits 5.5px above the viewport **bottom** (337). A box-vs-box "do not overlap" assertion would therefore be **false**, and the only way to make it pass would be to loosen tolerances until the check was meaningless — exactly what the brief warned against. Assertions here are instead made on **visible ink** (text client rects, expression clipped by its scrolling viewport) and on the **2D intersection** of those two rectangles. `TOL = 1.0`, never widened.

### Defect found and fixed

KaTeX renders a stacked `\frac` as a vlist ~37px tall while `line-height:1` keeps the line box ~20px, so the ink spills ~9px below the box. At `bottom:2px` the result ink reached **y=367.17** in an LCD ending at **365** — and `.lcd` is `overflow:hidden`, so **the denominator of an exact result was silently clipped** (visible in `P1C3_lcd_fraction.png`).

`bottom` was swept over 2, 4, 6, 8, 10, 12, 14px against `5/8`, `7/3`, `7*8` and a 20-term sum (`P1C_bottom_sweep.json`):

| `bottom` | tallest result ink vs LCD bottom (365) |
|---|---|
| 2px | **+2.17 — outside (clipped)** |
| 4px | +0.17 — flush |
| 6px | −1.83 |
| **8px** | **−3.83 — chosen** |
| 10px | −5.83 |

`8px` is the smallest offset that clears the screen while keeping the result in the lower band. The worst co-occurrence — a Sigma vlist expression (ink to 335.86) *and* a stacked-fraction result (`P1C_worst.json`) — stays **104.83px apart horizontally** at every offset, so raising the line can never collide.

**Fix** `de456d9`, **test** `75188f7`.

**After** (`P1C3_lcd_fraction.png`): `5/8` renders complete, ink 323.97→361.17, inside the LCD.

### Tests — `test_lcd_expression_result_geometry.py`, **11 passed / 9 subtests**

Covers: expression band directly under the 12px status bar and still 58px; no ink intersection across `LineI/LineO`, `DecimalO`, `MathI/MathO`; result stays below the status bar; **result ink and box stay inside the LCD**; a 20-term expression scrolls horizontally without moving or overlapping the result; Sigma vlist + fraction result coexist; stability at two viewports; empty result does not break measurement.

**Regression proof:** against the pre-fix CSS, **6 failures** including `result ink bottom 367.17 > lcd bottom 365`. Passes after the fix.

**No regressions:** `test_lcd_digit_typography.py`, `test_lcd_font_scope_and_calculus_slots.py`, `test_sigma_layout.py`, `test_keypad_typography.py`, `test_qr_lcd.py`, `test_output_modes.py` → **122 passed, 25 subtests**, exit 0.

---

## 7. Integration with `main`: **DONE**

```
merge base            : 2469d665f12920bb6ab036462f6382195ca0d919
origin/main           : 6ca4ead  (1 commit not on the feature branch)
feature branch        : 38 commits ahead, 1 behind  →  39 ahead, 0 behind after merge
```

`origin/main`'s extra commit `6ca4ead` is a merge whose **tree is byte-identical to the merge base** (both trees `4451f9a22fe2017a88a543873119107d381bcb9b`), so it introduces **no content change**. Verified in advance with `git merge-tree --write-tree --messages` → no conflict messages. Integrated with `--no-ff` as `c872bd6`.

Aggregate diff reviewed: `37 files changed, 8168 insertions(+), 176 deletions(-)`. **No force-push, no history rewrite, no `main` modification.**

---

## 8. Secondary cleanup

| Item | Outcome |
|---|---|
| 22 tracked `.pyc` files | **Untracked** (`ca0dccd`) via `git rm --cached` — files left on disk. They were stale `cpython-311` bytecode; the product ships 3.12.8, which ignores them. |
| `[KEY-TRACE-DROP]` | **Kept, deliberately** (`35e9caf`). It sits in the out-of-order-response guard of `backendKey()`: a slow reply to an earlier keypress is dropped, and without a marker that drop is invisible — which is how "the keypad went dead after a fast burst" gets misdiagnosed. `console.debug` is suppressed by default in shipped browsers. `test_equation_workflow.py:60` already asserts it exists. Behaviour unchanged; reasoning now documented at the call site. |
| README | **Rewritten** (`2c639dd`). It wrongly said the repo "uses two verification entry points instead of pytest"; it is a pytest suite. Added the portable build flow, offline behaviour, and a Known Limitations section. `--no-browser`, `--smoke-test`, the OFL font licence and the QR `THIRD-PARTY-NOTICES.txt` were each verified before being documented. |
| `calculator_portable/` | **Ignored** (`7c93572`). It is generated by `BUILD_ON_MY_PC.bat` — the same class as `build/` and `dist/`, already ignored — and bundles a ~24MB interpreter. Existing folder untouched and still runs (3.12.8). |
| Secrets | No matches for AWS/GitHub/OpenAI/Slack/Google/private-key patterns across tracked source. |
| Local paths | Fixed in three test files (`a63b698`) — see below. |

### A latent test-correctness defect found during hygiene

`test_full.py`, `test_full2.py` and `test_safe_eval.py` each did `sys.path.insert(0, r'E:\A.G\casio_mvp')`. Because `insert(0, …)` **outranks pytest's rootdir**, running them from the fresh clone reported **13 passed while actually exercising the original tree** — precisely the "green but wrong" result a clean-clone acceptance run exists to catch. After the fix, the clone imports its own module:

```
E:\A.G\casio_release_acceptance_20261011\mvp_server.py
```

---

## 9. Known limitations and incomplete checks

1. **Release is not on `main`.** The verified commit is `a63b698` on `frontend_fixes_october`, pushed, with **PR #5 open and `mergeable_state: clean`**. It has **not** been merged, pending human review. Do **not** tell anyone to use `main`.
2. **No genuinely system-Python-free machine was available.** Independence was proven by removing system Python from `PATH` and showing `sys.path` excludes all `site-packages` — the strongest substitute, but not a literal clean VM.
3. **Portable build is Windows-only** (embeddable CPython `.zip`/`._pth` layout plus a `.bat` launcher).
4. **Internet is needed once, at build time**, to fetch the embeddable runtime. The resulting folder is offline-capable (0 external requests verified).
5. **Two PyInstaller-spec tests skip in any clone** because `.gitignore` excludes `*.spec`. They pass where the spec exists.
6. **Browsers auto-request `/favicon.ico`**, which 404s. The page references no favicon and no application asset is missing. Cosmetic; not fixed (out of scope).
7. **SmartScreen** may warn on first launch of an unsigned `.bat`.
8. **`file://` is not a supported path.** It runs a reduced in-browser bridge with no backend; arithmetic and formatting work (and P1-A fixed its S⇔D) but the supported route is `RUN_CALCULATOR.bat`.
9. **The desktop PySide6 app (`main.py`) was not exercised** in browser-level acceptance; it is covered only by the existing test suite and `python main.py --smoke-test`.

---

## 10. Definition of done

| # | Item | Status |
|---|---|---|
| 1 | Fresh clone builds into a separate output location | **PASS** |
| 2 | Portable app launches from the fresh clone | **PASS** |
| 3 | Actual `[SELFTEST]` output captured | **PASS** — verbatim above |
| 4 | System-Python independence verified or limitation documented | **PASS WITH CAVEAT** — proven via hostile env; limitation stated |
| 5 | Complete suite recorded under Python 3.12.8 | **PASS** — 681 passed / 0 skipped (original), 679 + 2 explained skips (clone) |
| 6 | `file://` S⇔D fixed and tested | **PASS** — 17 tests |
| 7 | DEL edits committed coefficients, browser-tested | **PASS** — 10 tests + live DOM evidence |
| 8 | LCD geometry coverage | **PASS** — 11 tests; also fixed a real clipping defect |
| 9 | Release-critical calculator modes pass | **PASS** — full suite green |
| 10 | QR rendering has actual decode evidence | **PASS** — decoded `https://mentisai-delta.vercel.app/` |
| 11 | Final integration diff reviewed | **PASS** — 37 files reviewed; main's extra commit content-neutral |
| 12 | No user changes discarded, no force-push | **PASS** — verified, none occurred |
| 13 | Verified commit on the correct branch, or remaining human action documented | **PARTIAL** — on `frontend_fixes_october`; **PR #5 awaits human merge** |
| 14 | Docs match what was tested | **PASS** — README corrected against verified facts |
| 15 | No release-blocking defect hidden behind a passing count | **PASS** — every fix has a test proven to fail before it |

---

## 11. Delivery status

- **Branch pushed:** `frontend_fixes_october` → `a63b698` (fast-forward, `1a15f8a..a63b698`).
- **Pull request:** **https://github.com/Red-swipe/mvp/pull/5** — open, `mergeable_state: clean`, 44 commits, 64 files.
- **Not merged.** Required human action: **review and merge PR #5 into `main`.** I did not merge it myself, because merging to a shared branch is a governance decision and required review must not be bypassed.
- Once merged, `main` will contain the verified release at the merge commit.