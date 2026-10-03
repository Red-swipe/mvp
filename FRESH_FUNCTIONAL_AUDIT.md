# Fresh Functional Audit

> Method: independent, from-scratch functional audit of the **current** working
> tree. No prior audit claim (`audit.md`, `final_audit.md`, `button_audit.md`,
> `raw/handover.md`) was taken on trust; every claim in section 14 was
> re-derived by reproduction. Where a prior claim turned out to be stale or
> false, that is stated explicitly.
>
> Two verification layers were used:
> * **Static** - source reading of `mvp_server.py`, `frontend.html`, `engine/`.
> * **Runtime** - (a) in-process calls into `CalculatorController` /
>   `safe_evaluate_expression`, (b) live HTTP against a real `mvp_server.py`
>   process, (c) `node` execution of the extracted frontend script.
>
> All probe harnesses lived in `%TEMP%\opencode\` and were removed afterwards.
> Nothing was added to the repository except the fix, its regression test, and
> this file.

---

## 1. Audit Metadata

| Field | Value |
|---|---|
| Repository | `E:\A.G\casio_mvp` |
| Remote | `https://github.com/Red-swipe/mvp` |
| Branch | `main` |
| Commit audited | `9e7b356a1f9629da64616710932fa8506b0b1321` - "fix: correct contextual percentage semantics" (2026-09-27 20:51:01 +0500) |
| Audit date | 2026-10-03 |
| Python | 3.11.15 (MSC v.1944 64-bit AMD64) |
| Node | v24.15.0 |
| Platform | win32 / Windows PowerShell 5.1 |
| Pytest | 9.1.1 |
| Browser used | none - frontend verified by static analysis + `node` execution of the extracted inline script |
| Source sizes | `mvp_server.py` 3769 lines, `frontend.html` 8278 lines |

---

## 2. Executive Summary

The emulator is in good shape. **One genuine functional bug** was found and
fixed: the infix `C` combinatorics operator was destroyed by the `C`-register
substitution pass, so every infix-`C` form whose operator sat next to a
non-word character returned `Math ERROR` while the identical `P` form worked.
This was a real defect (a *silent semantic asymmetry* between `nPr` and `nCr`),
and the frontend bridge had already solved the same hazard - the backend had
not.

Everything else examined was either **verified working**, an
**already-documented intentional limitation** (implicit multiplication), or
**latent/dead code that the frontend never reaches** (`mixed_frac(`, dead
`#shiftIndicator` CSS, a stale `raw/` reference snapshot).

Two important corrections to the previous audit record:

* `final_audit.md` "Issue A" claims `-2^2` returns `4` on the backend and calls
  it a pre-existing parser divergence. **That is stale.** The backend now
  returns `-4`, which is the correct fx-991EX behaviour (powers bind tighter
  than a leading minus). See section 14.1.
* `final_audit.md` M3 claims `(3+2)C(2)` was verified live and passing.
  **It was not.** It raised `Math ERROR`. See section 15.

Test suite: **289 passed** at baseline, **304 passed** after the fix
(+15 new). No pre-existing test was modified, skipped, or removed.

---

## 3. Test Baseline

All commands run from the repository root on the audited commit.

### 3.1 `python -m pytest -q`

```text
........................................................................ [ 24%]
............................................................ [ 45%]
............................................................ [ 70%]
............................................................ [ 95%]
.............                                                            [100%]
289 passed, 12 subtests passed in 17.47s
```

**289 passed, 0 failed, 0 skipped, 0 errors.** 289 tests collected across 20
`test_*.py` modules (`--collect-only -q` -> "289 tests collected in 7.98s").

| Module | Area |
|---|---|
| `test_parity_regressions.py` | FILE_MODE vs backend math parity, error contract, frontend wiring |
| `test_state_machine.py` | screen states, register isolation, CALC/SOLVE wiring, SHIFT/ALPHA routing, node-executed frontend bridge |
| `test_percent_contextual.py` | contextual `%` semantics (BUG-08) |
| `test_shift_zero_rnd.py` | SHIFT+0 -> `Rnd()` / round template |
| `test_lowercase_x_variable.py` | lowercase `x`/`y` -> X/Y variable |
| `test_dms_input.py` | DMS key input |
| `test_settings_and_setup.py` | settings validation |
| `test_safe_eval_regressions.py`, `test_safe_eval.py`, `test_eval.py`, `test_engine.py` | tokenizer/parser/evaluator + safe-eval guards |
| `test_frontend_fixture.py`, `test_file_mode.py`, `test_frontend.html`, `test_server.py`, `test_serialize.py`, `test_equation_workflow.py`, `test_full.py`, `test_full2.py` | misc / fixtures |

### 3.2 `python verify.py`

```text
Total calls: 7
LEGACY scrollIndUp: CLEAN
LEGACY scrollIndDown: CLEAN
LEGACY scrollIndLeft: CLEAN
LEGACY scrollIndRight: CLEAN
calc: up=True down=True left=True right=True
menu: up=False down=False left=True right=True
setup: up=True down=True left=False right=False
```

Exit code **0**.

> **Documentation discrepancy (not fixed - out of scope).** `README.md:46-55`
> states the repository "uses two verification entry points instead of
> pytest" and that `verify.py` "exercises arithmetic, scientific functions,
> integrals, mode switching, power on/off, font serving, and the frontend HTML,
> and exits non-zero on any failure." Neither statement is true today:
> `verify.py` is an 18-line scroll-indicator linter with no `sys.exit` path and
> no way to fail, and the real suite is pytest with 289 tests. See section 18.

### 3.3 `python main.py --smoke-test`

Exit code **0**, no output, no traceback. The PySide6 desktop app boots and
tears down cleanly. (PySide6 is installed in this environment, so the smoke
test really ran.)

### 3.4 `python -m py_compile mvp_server.py`

Exit code **0** - no syntax errors.

### 3.5 `node --check` on the extracted inline frontend script

The single inline `<script>` block of `frontend.html` (282 391 bytes, 1 block,
extracted to `%TEMP%`) was checked:

```text
node --check exit: 0
```

### 3.6 Live HTTP server (`mvp_server.py --port 8137 --no-browser`)

```text
GET /                        200  347486 B
GET /frontend.html           200  347486 B
GET /health                  200  {'ok': True}
GET /api/settings            200  {...}
GET /setup_get               200  {...}
POST /setup_update           200  {'ok': True, ...}      (angle_unit=Radian)
POST /api/settings           200
```

Live equals round-trip (11/11 correct):

```text
PASS 1+1 -> '2'      PASS (2+3)*4 -> '20'   PASS sqrt(16) -> '4'
PASS 2+3*4 -> '14'   PASS 2^10   -> '1024'  PASS sin(30)   -> '0.5'
PASS 5!   -> '120'   PASS 10P3   -> '720'   PASS 5C2      -> '10'
PASS 200+10% -> '220'  PASS log(100) -> '2'
```

Live error contract (all HTTP 400 with `ok:false`, `state:"ERROR"`):

```text
1/0     -> 'To infinity and beyonddd'      1++    -> 'Math ERROR'
log(0)  -> 'Math ERROR'                    asin(2)-> 'Math ERROR'
((1)    -> 'Math ERROR'                    ()     -> 'Math ERROR'
```

Live keypad sequence **without** an `expression` override
(`POST /api/key {"key":"2"}` ... `{"key":"equals"}`):

```text
2         expr='2'      cursor=1
plus      expr='2+'     cursor=2
3         expr='2+3'    cursor=3
multiply  expr='2+3*'   cursor=4
4         expr='2+3*4'  cursor=5
equals    result='14'
```

Reproduced identically with the frontend's real payload shape
(`menuPage`/`menuIndex` present) and with explicit `action` fields.

### 3.7 Concurrency smoke

10 threads posting `{"key":"equals","expression":"<i>+<i>"}` concurrently
against the live server returned exactly `{2,4,6,8,10,12,14,16,18,20}` -
one result per request, no cross-talk (`CONTROLLER_LOCK` holds).

---

## 4. Architecture Reviewed

```text
frontend.html (8278 lines, single file)
  |- <style>                       1 inline block  (36 678 chars)
  |- <script src=...>              CDN: KaTeX 0.16.11 (+ css, auto-render),
  |                                qrcodejs 1.0.0
  `- <script>                      1 inline block  (274 837 chars)
       serializeSlot()             Math-IO tree -> canonical string
       prepareExpressionForEvaluation()  infix P/C -> nPr()/nCr(), \bM\b
       _transformSpecial()         FILE_MODE bridge (own evaluator, no backend)
       renderMath()/exprToLatex()  KaTeX Math-IO rendering + plain-text fallback
       makeCursor()/.lcd-cursor    block cursor, per-mode-screen variants
       renderLCD()                 #indShift/#indAlpha .active toggles
mvp_server.py (3769 lines)
  CalculatorController (2135-3494) single global CONTROLLER + CONTROLLER_LOCK
    press_key(payload)             every physical key path
    set_mode / _token_for          SHIFT/ALPHA token tables
    calculate_matrix/vector/...    OPTN operations for the 12 modes
  safe_evaluate_expression (1164)  the real math boundary:
    Ans/pi/e/i substitution -> variable A-F,M,X,Y -> keypad aliases
    -> _transform_random -> _transform_dms -> _transform_percent
    -> _transform_combinatorics_infix -> ^ to ** -> _transform_special_functions
    -> x/y alias -> _transform_factorials -> 2nd special pass
    -> engine.tokenize/parse/evaluate
  evaluate_base_n (1349)           Base-N pipeline
  evaluate_matvec_expression (2082) typed Matrix/Vector parser (_MVParser)
  MvpHandler (3501)                do_GET / do_POST routing + validation
engine/                            tokenizer -> parser -> evaluator (+11 mode packages)
raw/code organisation/*.md         stale verbatim frontend decomposition (reference only)
```

**Single source of truth per concern:** the frontend owns the expression tree,
the cursor and all overlay menus; the backend owns arithmetic, registers and
mode state. The frontend bridge (`_transformSpecial`) exists so *local*
FILE_MODE math works without a server, and the backend pipeline mirrors it.

---

## 5. Basic Calculation Audit

Verified through both `safe_evaluate_expression` and live `POST /api/key`.

| Expression | Result | Expected | Verdict |
|---|---|---|---|
| `1+1` | `2` | 2 | PASS |
| `2+3*4` | `14` | 14 | PASS precedence |
| `(2+3)*4` | `20` | 20 | PASS |
| `2+3*4^2` | `50` | 50 | PASS |
| `10/4` | `2.5` | 2.5 | PASS true division |
| `8/2` | `4` | 4 | PASS |
| `-5+3` | `-2` | -2 | PASS |
| `5--3` | `8` | 8 | PASS |
| `2^10` | `1024` | 1024 | PASS |
| `2^0.5` | `1.414213562` | sqrt 2 | PASS |
| `9^(1/2)` | `3` | 3 | PASS |
| `sqrt(16)+2` | `6` | 6 | PASS |
| `1.5*2` | `3` | 3 | PASS |
| `0.1+0.2` | `0.3` | 0.3 (10 s.f.) | PASS |
| `(-2)^2` | `4` | 4 | PASS |
| `-2^2` | `-4` | **-4** | PASS fx-991EX: power binds tighter than leading minus |
| `-2^3` | `-8` | -8 | PASS |
| `0-2^2` | `-4` | -4 | PASS |
| `3^3^2` | `19683` | 3^9 = 19683 | PASS right-associative |
| `2*3+4*5` | `26` | 26 | PASS |
| `100-10-10` | `80` | 80 | PASS left-associative |
| `1/2`, `3/4+1/4` | `0.5`, `1` | - | PASS |
| `Ans*2` after `3+4` | `14` | 14 | PASS Ans chain |

**Fractions / mixed fractions.** The frontend serializes Math-IO fraction and
mixed-fraction templates (`frontend.html:2517-2525`) into `((n))/((d))` and
`((w))+((n))/(d)` (with a `((w))-((n))/(d)` form for negative wholes). All
verified against the backend:

```text
((3))/((4))          -> 0.75
((2))+((1))/((2))    -> 2.5     (mixed 2 1/2)
((-3))/((4))         -> -0.75
```

The `/api/fraction` endpoint (result-to-fraction conversion) was verified live:
`{"value":2.5,"mixed":true}` -> `2 1/2`; `{"value":0.75}` -> `3/4`.

**Roots.** `cbrt(27)`=3, `cbrt(-8)`=-2 (real odd root), `xroot(3,27)`=3,
`xroot(4,16)`=2, `xroot(3,-27)`=-3, `xroot(2,9)`=3.
Argument order is `xroot(index, radicand)` (`mvp_server.py:470-480`).

**Negative fractional powers.** `(-8)^(1/3)` -> complex `(1.0+1.732j)` ->
rejected as `Math ERROR` outside Complex mode, which is correct (the device
uses `cbrt`/`xroot` for real odd roots, which do work).

---

## 6. Cursor / Editing Audit

Backend cursor semantics (`mvp_server.py:3229-3243`, `3438-3462`,
`_update_viewport` 3487):

* `dpad_left` / `dpad_right` move the cursor one slot, clamped to
  `[0, len(expression)]`, and honour a frontend-supplied `cursorPosition`.
* **Default mode is overwrite, matching the fx-991EX.** Typing at a cursor
  inside the expression replaces the character under it: `1 2 3` then two
  `dpad_left` (pos 1) then `9` -> `193`.
  `SHIFT+DEL` toggles insertion mode; with insertion on, `9` at pos 1 of
  `1234` -> `91234`.
* `del` at end-of-line backspaces and decrements the cursor.
* `ALPHA+DEL` pops `undo_stack` and restores expression, cursor,
  `result_displayed` and `last_result` (`3191-3200`). Verified: `1` `2` then
  ALPHA+DEL -> `1`.
* `RESULT`/`ERROR` state plus any D-pad -> `_return_to_editing()` clears the
  result flag and parks the cursor at end of expression.
* Viewport: `_update_viewport` keeps the 22-slot window in range; a 30-digit
  expression produced `expressionViewport = 8` (= `30-22`).

**Frontend cursor.** `.lcd-cursor` (`frontend.html:850`, `1297`) is a blinking
block caret injected inline at `cursor.slot` / `cursor.index`, rebuilt by
`makeCursor()` (`4186`). It is used by the main expression renderer *and* by
every mode screen - matrix row/col counts (`4267`, `4281`), matrix cell entry
(`4327`), vector dim (`4398`) and cell (`4441`), statistics input (`4679`),
SETUP menu rows (`4744`, `4761`), distribution input (`5383`), inequality
coefficients (`5573`), equation coefficients (`5611`).

**Nested structures.** Template editing is fully slot-based
(`cursor.slot.items.splice` in insert mode, `insertTemplate(..., 'num')` /
`'whole'` / `'index'` / `'radicand'` etc.), so cursor position is per-slot
rather than a flat string index - the frontend does not rely on the backend's
flat `cursor_position` for template navigation.

**Verdict: VERIFIED WORKING.** The only unreachable pieces are the backend's
own `SHIFT+DEL` insert-mode and `ALPHA+DEL` undo branches, which the frontend
handles locally (`frontend.html:8150`, `8157`) and therefore never sends.
Latent, not broken.

---

## 7. Math-IO Audit

`serializeSlot()` (`frontend.html:2500-2544`) emits a canonical ASCII string
per Math-IO template; `exprToLatex()` (`2021`) converts it to LaTeX and
`renderMath()` (`2046`) drives KaTeX.

Verified round-trips (backend accepts every template's serialization):

| Template | Serialized form | Backend |
|---|---|---|
| fraction `3/4` | `((3))/((4))` | `0.75` PASS |
| mixed `2 1/2` | `((2))+((1))/((2))` | `2.5` PASS |
| cube root of 8 | `cbrt(8)` | `2` PASS |
| n-th root `3 root 27` | `xroot(3,27)` | `3` PASS |
| square root `sqrt 16` | `sqrt(16)` | `4` PASS |
| power `2^10` | `((2))^((10))` | `1024` PASS |
| log base `log_base(2,8)` | `log_base(2,8)` | `3` PASS |
| `Rnd` template | `Rnd(3.7)` | `3.7` PASS |
| integral template | `integral(x^2,0,3)` | `9` PASS |
| `d/dx` | `diff(x^2,3)` | `6` (5.999999959) PASS |
| sigma | `sigma(x,1,5)` | `15` PASS |
| `sin^-1` | `asin(0.5)` | `30` PASS |

`Sigma(` and `d/dx(` are additionally aliased at `mvp_server.py:1204`
(to `sigma(` / `diff(`), so raw keypad spellings work too.

**Graceful degradation:** `renderMath` falls back to `host.textContent = raw`
when `katex` is undefined (`2057`), and the auto-render hook at `2077`
re-renders on KaTeX load. Font assets are served from `/fonts/` and
`/ClassWizFontSet/` (`mvp_server.py:3574-3591`); a missing font returns a JSON
404 rather than a crash. `GET /ClassWizFontSet/` (a directory path) returning
404 is correct - only individual files are served.

**Superscript normalisation** is handled in `serializeSlot`:
`sin^-1(` -> `asin(`, `x10^` -> `*10^`, `x` -> `*`, `/` -> `/`, `-` -> `-`,
`pi` -> `pi`, `2` -> `^2`, `3` -> `^3`, `-1` -> `^(-1)`.

**Verdict: VERIFIED WORKING** (runtime-verified for the backend half;
statically verified for the KaTeX half, which needs a browser).

---

## 8. SHIFT / ALPHA Audit

`CalculatorController._token_for` (`mvp_server.py:3061-3102`) is the whole
SHIFT/ALPHA contract. Every mapping was verified by pressing SHIFT/ALPHA then
the key and reading the resulting expression.

**SHIFT (17/17 exact):**

```text
sin->asin(   cos->acos(   tan->atan(   log->10^(   ln->e^(    sqrt->cbrt(
square->^3   power->xroot(  scientific->pi  0->round(  decimal->rand()
fraction->mixed_frac(  integral->diff(  variable->sigma(  ellipsis->FACT(
right_paren->,          ans->%          eng-><
```

**ALPHA (14/14 exact):**

```text
negate->A  ellipsis->B  inverse->C  sin->D  cos->E  tan->F  right_paren->x
s_to_d->y  m_plus->M  scientific->e  decimal->RanInt(  integral->:  calc->=  eng->i
```

**Latch semantics (all correct):**

* `shift` toggles SHIFT on and forces ALPHA off (`3164-3167`).
* `alpha` toggles ALPHA on and forces SHIFT off (`3168-3171`).
* Both auto-clear after the next token (`3464-3465`) and after `equals`
  (`3327-3328`), matching the device's momentary-modifier behaviour.
* Complex mode remaps `eng` -> `i` (`3062`); Base-N mode remaps
  SHIFT+`square/^/log/ln` to `__BASE_SWITCH__DEC/HEX/BIN/OCT__` (`3064-3072`).

**Base-N base switching** was verified end-to-end: pressing SHIFT+`square`
converts the displayed result to DEC, and the sentinel is handled at
`3421-3435` (including the explicit `base_switch` key at `3410-3419`).

**Indicator feedback (frontend).** `#indShift` / `#indAlpha`
(`frontend.html:1628-1629`) are `display:none` by default (`.status-tag`,
`773-781`) and become visible via `.status-tag.active{display:inline-block}`
(`782`) toggled from `appState.shift` / `appState.alpha` (`5808-5809`). The
`rawKey === 'setup'` handler even reads the live indicator class to allow
SHIFT-independence (`6454-6455`). **VERIFIED WORKING.**

> Dead CSS, no functional impact: `#shiftIndicator::after` /
> `#alphaIndicator::after` keyed on `body.shift-on` / `body.alpha-on`
> (`frontend.html:1307-1310`) reference element IDs and body classes that
> **do not exist anywhere in the file**. See section 17.

---

## 9. Scientific Function Audit

Angle-unit awareness verified in all three units (Degree default, Radian,
Gradian) via `update_setup_setting("angle_unit", ...)` and the live
`POST /setup_update`.

| Function | Degree | Radian | Gradian |
|---|---|---|---|
| `sin` | `sin(30)`=0.5, `sin(90)`=1 | `sin(0)`=0 | - |
| `cos` | `cos(60)`=0.5 | - | - |
| `tan` | `tan(45)`=1 | - | - |
| `asin` | `asin(0.5)`=30 | - | - |
| `acos` | `acos(0.5)`=60 | - | - |
| `atan` | `atan(1)`=45 | - | - |

Live HTTP confirmed `sin(0)` returns `0` in Radian and Degree via
`POST /setup_update {"key":"angle_unit","value":"Radian"}`; a rejected value
`"Bogus"` returned
`{"ok": false, "error": "Invalid value for setting: angle_unit"}`.

**Logs / exponentials:** `log(100)`=2, `ln(e)`=1, `e^2`=7.389056099,
`e^e`=15.154, `10^3`=1000, `log_base(8,2)`=0.3333.
The standalone-`e` substitution (`mvp_server.py:1189`) is double-bounded so
`1e10`-style notation and identifiers are untouched.

**Hyperbolic / inverse-hyperbolic:** `sinh/cosh/tanh`, `asinh/acosh/atanh` are
in `_SPECIAL_FUNCS` with real and complex branches (`748-775`).

**Domain guards:** `log(0)`, `ln(0)`, `log(-1)`, `ln(-1)`, `sqrt(-1)`,
`asin(2)`, `acos(5)`, `tan(90)` -> `Math ERROR` in non-Complex modes. Complex
modes return true complex values (`sqrt(-1)` -> `i`).

**Factorial:** `0!`=1, `1!`=1, `5!`=120, `(3+2)!`=120, `3!!`=720,
`Ans!` (Ans=5)=120, `2!^2`=4, `(0)!`=1, `cos(0)!`=1 (function-call operands
resolve: the operand `cos(0)` is evaluated, then factorialed).
Errors: `(-3)!`, `(-0.5)!`, `0.5!`, `2.5!`, `171!`, `sin(30)!` (0.5 is not an
integer), `(pi)!` -> `Math ERROR`.
Implementation: `_transform_factorials` (`780`) resolves arbitrary operands
(bare runs, `)`-terminated groups, function calls) and caps at 170.
**VERIFIED WORKING.**

**nPr / nCr:** `5P2`=20, `5C2`=10, `(5)P(2)`=20, `(5)C(2)`=10 **(after fix,
section 15)**, `(3+2)P(2)`=20, `(3+2)C(2)`=15 **(after fix)**,
`(5)C((2))`=10, `5 C 2`=10, `Ans C 2`=10, `Ans P 2`=20, `10P0`=1, `5C5`=1,
`10C2`=45, `nPr(5,2)`=20, `nCr(5,2)`=10.
Errors: `5C6` (r > n), `(-3)C2` (n < 0), non-integer operands.
**The `C` half was broken before the fix; see section 15.**

**Sigma / integral / derivative** - and an important subtlety that looks like
a bug but is not: the active angle unit applies inside calculus too, because
`integral` and `diff` operate on *the function as the calculator evaluates it*.

```text
                          Degree          Radian         Gradian
integral(sin(x),0,pi)     0.08610697      2.0000000000    0.07749996
integral(cos(x),0,pi)     3.14001871      0.0             3.14031773
integral(x^2,0,3)         9.00000000      9.00000000      9.00000000
diff(sin(x),30)           0.015114995     0.15425145      -
```

In Radian mode `integral(sin(x),0,pi)` is the textbook `2` and
`integral(cos(x),0,pi)` is `0`, both exact. In Degree mode the integrand really
is *sin of a degree value*, so the exact value is
`(180/pi)(1 - cos(pi^2/180)) = 0.086107`, which is what the emulator returns
to 10 significant figures. Likewise `diff(sin(x))` at 30 is the derivative of
sin-degrees, `(pi/180) * cos(30 deg) = 0.015115`, exactly what is returned; in
Radian mode it is `cos(30 rad) = 0.15425145`, matching to 7 figures.
**Not a bug** - the engine is internally consistent and correct in all three
units.

Other calculus: `sigma(x,1,5)`=15, `sigma(x^2,1,3)`=14, `diff(x^2,3)`=6
(5.999999959), `integral(1/x,1,2)`=0.693147 (= ln 2),
`sigma(sin(x),1,3)`=0.104688 (= `sin1deg + sin2deg + sin3deg`, exact).

**DMS:** `30deg`=30, `30deg 15min`=30.25, `30deg 15min 20sec`=30.2555,
`1r`=57.29577951 (1 radian expressed in degrees), `100g`=90 (100 gradians =
90 degrees). The primes must be the typographic U+2032/U+2033 the keypad
inserts; ASCII `'` and `"` are not in the grammar, which is correct - they are
not calculator tokens.

**Pol / Rec:** `Pol(3,4)`=5, `Rec(5,60)`=2.5 (x-component only).

**S-to-D:** `s_to_d` under ALPHA yields `y`. The display conversion itself is a
frontend concern; the backend exposes the canonical number and the frontend
formats it (`format_display` / `_format_single_number`).

**Constants / conversions:** `get_constants()` returns 43 constants across 7
categories (Universal, Electromagnetic, Atomic and Nuclear, Physico-Chem,
Adopted Values, Other). `POST /api/convert {"category":"Length","from":"m",
"to":"cm","value":1}` -> `100` live.

**Random:** `rand()` -> [0,1); `RanInt(1,6)` -> integer in 1..6 (stdlib
`random` only - no `eval`/`exec` anywhere in `mvp_server.py`).

**`Rnd` semantics:** `round(2.5)`=2.5, `round(-2.5)`=-2.5, `Rnd(2.5)`=2.5,
`round(2.4)`=2.4. This is **correct fx-991EX behaviour**, not a bug: `Rnd`
rounds per the *Number Format* setting (Norm -> 10 significant digits,
`_rnd_value`, `mvp_server.py:100-135`); it is not "round to integer".

---

## 10. Memory / Variables / Register Audit

**Ans.** `3+4` then Ans=7; `Ans*2` -> 14. `Ans` is substituted numerically at
`mvp_server.py:1186` before anything else, so `Ans` works inside every function
(`integral` integrand, `sigma`, `diff`, `xroot`, `nCr`, ...).

**A-F, M, X, Y registers.** `set_variable` rejects unknown names and
non-numeric values. Verified: `A=5` then `A+1`=6, `A*2`=10, `A`=5, `B+1`=1
(default 0), `C+1`=100 with `C=99`, `2*C`=198, `C-100`=-1.
Also verified via the live endpoints: `POST /api/variables/set {"name":"A",
"value":5}` then `POST /api/calc {"expression":"A+1"}` -> `6`.

**CALC / SOLVE.** `POST /api/calc` substitutes caller-supplied values and
persists them (`calc_evaluate`, `2720`). `POST /api/solve
{"expression":"X^2-4","variable":"X","guess":1}` -> `2` (Newton).
`CalculatorController.solve_equation_newton` (2761) covers the in-mode path.

**Register / mode isolation - explicitly verified:**

```text
A=11, Ans=2, MatA=[[1,2],[3,4]] set
  -> after Matrix work : Ans still 2, var A still 11, MatA intact
  -> after Vector work : Ans still 2, var A still 11, VctA=[7,8,9] intact
  -> back in Calculate : A evaluates to 11
  -> back in Matrix    : MatA evaluates to [[1,2],[3,4]]
AC                      -> var A 11, MatA [[1,2],[3,4]], VctA [7,8,9], Ans kept
AC(OFF) then ON         -> registers all preserved
```

`AC` clears the expression, cursor, result, SHIFT/ALPHA, undo stack and screen
state - and **nothing else**. Power-cycling likewise preserves registers, which
matches the device (Casio's AC/ON does not clear the register file).

`reset_calculator("memory")` and `("all")` are the explicit clear paths and
both zero `variables`, `matrices`, `vectors`, `statistics` and `distribution`.

**Stale-state check.** After a `Math ERROR`, `error`/`display` are correct
(`Math ERROR`) and `getScreenState` in the frontend tests `st.error` **first**
(`frontend.html:2573`), so a stale `lastResult` in the payload cannot be
displayed as a fresh result. See section 17 for the residual payload-hygiene
nit.

**Verdict: VERIFIED WORKING.**

---

## 11. Twelve-Mode Audit

Mode entry is driven by `MENU_PAGES` (`mvp_server.py:45-51`) and confirmed by
`_sync_menu_from_payload` (3005) adopting the frontend's canonical
`menuPage`/`menuIndex` for digits, D-pad and equals-confirm alike.

All 12 modes enter successfully (`set_mode` -> `ok:true`, correct `modeName`),
**and each was exercised beyond opening its screen**:

| # | Mode | Representative functionality exercised | Result |
|---|---|---|---|
| 1 | Calculate | 40+ expressions, SHIFT/ALPHA maps, Ans, registers, percent | PASS |
| 2 | Complex | `1+i`=`1+1i`; `(1+i)*(1-i)`=2; `i*i`=-1; modulus, arg, conj, `sqrt(-4)` | PASS |
| 3 | Base-N | base2 `101+1`=`110`, `1010*11`=`11110`, `110/10`=`11`; base8 `17+1`=`20`; base16 `FF+1`=`100`, `A*F`=`96`; negative sign preserved (`-101` -> `-101` in base 2) | PASS |
| 4 | Matrix | `add`, `subtract`, `multiply` (incl. dimension mismatch -> `Dimension ERROR`), `scalar_multiply`, `transpose`, `determinant` (=-2), `inverse`, `power`, `identity(3)`, `abs`; inline `MatA`, `MatA+MatA` | PASS |
| 5 | Vector | `add`, `subtract`, `scalar_multiply`, `multiply`/`cross`, `dot`=14, `angle`=57.688, `unit`, `magnitude`=3.7417 | PASS |
| 6 | Statistics | `POST /api/statistics/set` + `/calculate {"type":1,"data":[{"x":1},{"x":2},{"x":3}]}` -> `n=3, mean=2, populationStd=0.8165, min=1, max=3` | PASS |
| 7 | Distribution | `POST /api/distribution/calculate {"type":1,"params":{"x":0,"mu":0,"sigma":1}}` -> `0.3989422804` (normal PDF) | PASS |
| 8 | Spreadsheet | `POST /api/spreadsheet/set A1=1`, `A2==2+3` -> formula cell, `eval` recalculates | PASS |
| 9 | Table | `POST /api/table/calculate {"expression":"x^2","start":1,"end":3,"step":1}` -> rows `f = 1, 4, 9` | PASS |
| 10 | Equation/Func | `POST /api/equation/solve {"kind":"quadratic","coefficients":[1,-5,6],"degree":2}` -> roots `3, 2`; Newton `x^2-4` -> `2` | PASS |
| 11 | Inequality | `POST /api/inequality/solve {"degree":2,"operator":">","coefficients":[1,-3,2]}` -> `(-inf,1) U (2,+inf)` | PASS |
| 12 | Ratio | `POST /api/ratio/calculate {"type":1,"a":2,"b":3,"c":4}` -> `2.666666667` | PASS |

**MENU navigation re-verified live:** `menu` -> `MENU`; digit `1` page 1 ->
`Calculate`; digit `9` page 1 -> `Table`; digit `2` page 2 ->
`Equation/Func`, each echoing the matching `menuPage`/`menuIndex`.

**Input validation** produces precise, non-crashing errors:
`{"matrix":"Z"}` -> "Invalid matrix name 'Z'. Must be A, B, C, or D.";
`{"expression":"x^","start":"a",...}` -> "Math ERROR: Invalid expression:
'x**'"; `{"target":"bogus"}` -> "Unknown reset target: bogus";
`{"value":"abc"}` on `/api/fraction` -> `400 Invalid JSON`.

**Verdict: VERIFIED WORKING** for all 12. No mode is merely a stub screen.

---

## 12. Error Handling Audit

Every case below returns `ok:false`, `state:"ERROR"`, `display:"Math ERROR"`
(or the divide-by-zero message) and **never raises out of `press_key`**.

| Input | Result |
|---|---|
| `''` (empty) + `equals` | `ok:true`, `state:RESULT`, `result:'0'` - see section 17 |
| `AC` on empty input | `ok:true`, `state:INPUT`, `expression:''` PASS |
| `1/0` | `To infinity and beyonddd` (the device's divide-by-zero string) |
| `1/0+2` | same |
| `1++`, `***`, `()`, `((`, `)`, `2^^3`, `1,2` | `Math ERROR` |
| `log(0)`, `ln(0)`, `log(-1)`, `ln(-1)`, `sqrt(-1)` | `Math ERROR` |
| `asin(2)`, `acos(5)` | `Math ERROR` (outside Complex mode) |
| `(-3)!`, `2.5!`, `171!`, `0.5!`, `(-0.5)!` | `Math ERROR` |
| `5C6`, `(-3)C2` | `Math ERROR` |
| Matrix dimension mismatch | `Dimension ERROR` |
| Undefined variable (`x`, `B` where unset) | `Math ERROR` |
| `POST /api/key {}` | `ok:true`, no state change, HTTP 200 |
| `POST /api/key {"key":null}` | `ok:true`, no crash |
| Key `"\x00"`, `"'; DROP TABLE"`, `"eval("`, `"__import__"`, `"../../etc/passwd"` | inserted/ignored, `ok:true`, **no crash, no code execution** |
| 500-char digit run, 200x `1+`, 60 nested parens | handled, no crash, no stack overflow |
| Malformed JSON body | `400 {"ok": false, "error": "Invalid JSON"}` |
| Wrong `Content-Type` | `400 Content-Type must be application/json` |

`press_key` has a top-level `except Exception` (`3472-3477`) that logs to
stderr and returns `Math ERROR`, so no user input can take the server down. The
server survived the entire audit with an **empty stderr tail**.

**Security note.** No `eval`, `exec`, `__import__`, `compile` or `globals`
appears in `mvp_server.py`; the math pipeline is tokenizer -> parser ->
interpreter, and the server binds `127.0.0.1` by default.

**Verdict: VERIFIED WORKING.**

---

## 13. UI / System Feature Audit

| Feature | Evidence | Verdict |
|---|---|---|
| **MENU** | `press_key` MENU branch `3358-3362`; digit branch `3364-3381`; D-pad branch `3383-3393`; equals/center `3245-3251`; `_move_menu` wraps page1 to page2 (`3030`) | PASS |
| **SETUP** | `POST /setup_update` (`3651`) -> `update_setup_setting` (`2266`) with a per-key validator (`2187-2238`); invalid value rejected, not raised | PASS |
| **OPTN** | `openOptnPanel`/`closeOptnPanel` (`6099`, `6155`); D-pad-while-open navigation (`6121-6126`); `AC`/`OPTN` close; `Escape` closes (`8272`); backend `calculate_matrix` (2868), `calculate_vector` (2905), `calculate_statistics`, `calculate_distribution`, `calculate_table`, `solve_equation`, `solve_inequality`, `calculate_ratio` and `convert_units_calc` power the items | PASS |
| **QR** | SHIFT+OPTN is labelled `QR` (`1886-1887`); `showQRinLCD()` (`6385-6396`) renders a real QR of `https://mentisai-delta.vercel.app/` into the LCD via `qrcodejs`; also reachable from SETUP (`2330`, `4782-4783`); `AC`/`OPTN` dismiss (`8112`); **falls back to the plain URL text when `QRCode` is undefined (offline)** | PASS (static + fallback) |
| **D-pad** | Backend `3225-3243`, `3395`; frontend `rawKey==='dpad_*'` handling with per-mode overlays | PASS |
| **SHIFT/ALPHA indicators** | `#indShift`/`#indAlpha` with `.active` (`1628`, `5808`) | PASS |
| **Scroll indicators** | `verify.py` reports 7 `updateScrollIndicators(...)` call sites and all four legacy IDs `scrollIndUp/Down/Left/Right` **CLEAN** | PASS |
| **Display rendering** | KaTeX Math-IO (`1567-1576`, `renderMath`) + ClassWiz font CSS; plain-text fallback | PASS |
| **Mode transitions** | `set_mode` (`3104-3129`) clears expression, cursor, viewport and result, and re-aligns the menu cursor; unknown mode -> `"{mode} unavailable"` | PASS |
| **Input state** | `screenState` in `EMPTY/EDITING/RESULT/ERROR` with `error` tested first (`2572-2577`); `routeResultInput` (`2621`) governs RESULT+key routing | PASS |
| **Result state** | `resultDisplayed` + `lastResult`; `_return_to_editing` (`3479`); digit after a result starts fresh (verified: `5+5`=`10`, then `3` -> `3`) | PASS |
| **Power on/off** | `on` (`3137`), `AC`+OFF (`3157`); keys ignored while off (verified: display stays `''`); `ON` restores | PASS |
| **Contrast / display settings** | `applyContrast`, `multiline_font`, `number_format`, `digit_separator`, `engineering_symbols` all present in `DEFAULT_SETUP_SETTINGS` | PASS |

---

## 14. Previous Audit Claims Rechecked

Each item was **reproduced**, not read.

| # | Claim | Classification | Evidence |
|---|---|---|---|
| 1 | **Cursor system** | **VERIFIED WORKING** | Backend overwrite/insert/backspace/undo/viewport all behave; frontend `makeCursor()`/`.lcd-cursor` used by the main renderer and all 8 mode screens (section 6). |
| 2 | **Math-IO rendering** | **VERIFIED WORKING** | All 12 template serializations evaluate correctly on the backend; `exprToLatex`/`renderMath` present with a plain-text fallback (section 7). |
| 3 | **raw HTML/CSS/JS split** | **DEFERRED - stale reference snapshot (documentation drift, not a defect)** | `raw/code organisation/{html,css,js}.md` was last touched in `a7c841e`; `frontend.html` has moved on since. Sampled-window overlap against the live file: **CSS 90 %, JS 97.5 %**. They are reference copies only - `frontend.html` is the single live artifact. Not repaired (regenerating 350 KB of reference docs is out of scope for a functional pass). |
| 4 | **mode-screen JavaScript** | **VERIFIED WORKING** | Each of the 12 modes has a real LCD screen with its own cursor and input handling (matrix `4267-4327`, vector `4398-4441`, stats `4679`, distribution `5383`, inequality `5573`, equation `5611`, SETUP `4744-4801`), and every mode's backend operation was exercised (section 11). |
| 5 | **SHIFT/ALPHA feedback** | **VERIFIED WORKING** | All 17 SHIFT and 14 ALPHA token mappings exact; latch/auto-clear/mutual-exclusion correct; `#indShift`/`#indAlpha` `.active` toggle wired (section 8). Dead CSS at `1307-1310` noted in section 17. |
| 6 | **QR functionality** | **VERIFIED WORKING** | Real QR generation via `qrcodejs`, reachable from SHIFT+OPTN and SETUP, dismissible, with an offline text fallback (section 13). |
| 7 | **register/state isolation** | **VERIFIED WORKING** | Scalar A-F/M/X/Y, `MatA-D`, `VctA-D`, statistics, distribution and spreadsheet all survive mode switches, AC and power cycles without cross-talk (section 10). |
| 8 | **factorial** | **VERIFIED WORKING** | Arbitrary operands (`(3+2)!`, `Ans!`, `cos(0)!`), 170 cap, all invalid forms rejected (section 9). |
| 9 | **nPr** | **VERIFIED WORKING** | `5P2`, `(5)P(2)`, `(5+1)P(2)`, `(5)P((2))`, `5 P 2`, `Ans P 2`, `nPr(5,2)` all correct. |
| 10 | **nCr** | **REAL BUG - found and fixed** | `5C2` worked only by accident; `(5)C(2)`, `(5+1)C(2)`, `(5)C((2))` and `5 C 2` all returned `Math ERROR` while every `P` counterpart worked. `final_audit.md` M3 explicitly listed `(3+2)C(2)` as a *passing live test* - that claim was false. See section 15. |
| 11 | **contextual percentage semantics** | **VERIFIED WORKING** | `200+10%`=220, `200-10%`=180, `200*10%`=20, `200/10%`=2000, `100+10%+10%`=121, `5%`=0.05. Covered by `test_percent_contextual.py` (9 classes). |

### 14.1 Additional stale claims found

**Issue A - `-2^2`.** `final_audit.md` "Remaining Known Issues -> Issue A"
states *"`-2^2` -> backend 4, local -4 ... confirmed pre-existing"*, and its
FILE_MODE Parity table lists `-2^2 / backend 4` as an accepted divergence.

**This is no longer true.** The backend now returns **`-4`** for `-2^2`
(`engine/parser.py:85-86` documents the fx-991EX precedence deliberately), and
the frontend bridge agrees. **Issue A is resolved.**

**Issue B - `integral(sin(x),0,pi)`.** `final_audit.md` claims the backend
integrand path rejects trig bodies and returns `Math ERROR`. **Also no longer
true.** It now returns a real number, and that number is *correct for the
active angle unit*: `0.086107` in Degree and `2.0000000000` in Radian (see
section 9 for the three-unit table and the closed-form cross-check).
**Issue B is resolved.**

**Issue C - `asin(2)`.** Still `Math ERROR` outside Complex mode.
**INTENTIONAL** - the engine refuses complex results in real modes
(`mvp_server.py:3317-3323`), which matches the device outside Complex mode.

**Issue D - the combined degree/minute/second placeholder.** Still not
evaluable; it is a UI template marker, not a number. **DEFERRED.**

---

## 15. Genuine Bugs Found

### BUG-01 - Infix `C` combinatorics operator destroyed by `C`-register substitution

* **Severity:** Medium. Silent semantic asymmetry between `nPr` and `nCr`; every
  parenthesised, spaced or nested infix-`C` form produced `Math ERROR`.
* **Component:** `mvp_server.py` -> `safe_evaluate_expression`

**Reproduction** (pre-fix; verified by stashing only `mvp_server.py`):

```python
from mvp_server import safe_evaluate_expression as S
V = {k: 0.0 for k in "ABCDEF MXY".replace(" ", "")}
S("(5)C(2)",   0.0, "Degree", V, False, ("Norm", 1))   # -> Math ERROR
S("(5+1)C(2)", 0.0, "Degree", V, False, ("Norm", 1))   # -> Math ERROR
S("(5)C((2))", 0.0, "Degree", V, False, ("Norm", 1))   # -> Math ERROR
S("5 C 2",     0.0, "Degree", V, False, ("Norm", 1))   # -> Math ERROR
S("(5)P(2)",   0.0, "Degree", V, False, ("Norm", 1))   # -> 20   (worked)
S("5 P 2",     0.0, "Degree", V, False, ("Norm", 1))   # -> 20   (worked)
S("5C2",       0.0, "Degree", V, False, ("Norm", 1))   # -> 10   (worked, by accident)
```

Measured with the fix stashed and restored: **5 failing -> 0 failing.**

**Expected behaviour:** `(5)C(2)` = 10, symmetric with `(5)P(2)` = 20.

**Actual behaviour:** `ValueError: Math ERROR: Unexpected trailing token
Token(kind=LPAREN, ...)`.

**Root cause.** `safe_evaluate_expression` substituted the word-bounded
register letters (pre-fix `mvp_server.py:1162-1169`):

```python
s = re.sub(rf'\b{_vname}\b', _lit(_vval), s)     # 'C' -> '(0.0)'
```

but `_transform_combinatorics_infix` - the pass that turns `...C...` into
`nCr(...)` - only ran **later**, at pre-fix line `1181`. So the `C` operator was
replaced by the register value before the operator could ever be recognised:

```text
(5)C(2)  ->  (5)(0.0)(2)   -> tokenizer: trailing LPAREN  -> Math ERROR
```

`5C2` escaped only because `\bC\b` finds no word boundary between `0` and `C`;
`(5)C2` and `Ans C 2` failed for the same reason as `(5)C(2)`. Bare `P` was
never affected because `P` is not a register.

The frontend bridge had already identified and fixed this exact hazard -
`frontend.html:3590-3603` places its infix pass **before** its variable
substitution and says so in a comment. The backend had the passes in the
opposite order.

**Fix made** (`mvp_server.py`, two edits, no other behaviour touched):

1. New helper `_infix_pc_operator_indices` (next to `_find_infix_pc`, line 986)
   that replays `_find_infix_pc`'s exact bounded scan and returns the set of
   operator indices, so the two can never disagree.
2. In the variable-substitution loop (lines 1189-1200), the `C` register skips
   substitution at those operator positions and substitutes everywhere else:

```python
if _vname == 'C':
    _pc_ops = _infix_pc_operator_indices(s)
    if _pc_ops:
        s = ''.join(ch if (i in _pc_ops or ch != 'C') else _lit(_vval)
                    for i, ch in enumerate(s))
        continue
s = re.sub(rf'\b{_vname}\b', _lit(_vval), s)
```

`P` handling is untouched, and the register `C` still reads normally whenever
it is not acting as an operator.

**Regression test:** `test_infix_combinatorics.py` (new, 15 tests / 41
subtests) covering

* the defect - `(5)C(2)`, `(5+1)C(2)`, `(10)C(3)`, `(5)C((2))`, `5 C 2`,
  `Ans C 2`, `Ans C Ans`;
* `P` counterparts unchanged, so the symmetry is asserted rather than assumed;
* `C` still a register (`C`, `C+1`, `(C)`, `C*2`, `2*C`, `C-100`) and a stored
  `C=99` **cannot** change nCr results;
* invalid forms still error (`5C6`, `(-3)C2`, `0 C 5`, `5 C x`);
* `_infix_pc_operator_indices` agrees with `_find_infix_pc` and never marks a
  function name (`nPr(`, `nCr(`, `Pol(`, `Rec(`, `RanInt(`, `xroot(`, ...);
* end-to-end through `CalculatorController.press_key`.

**Post-fix results**

```text
python -m pytest test_infix_combinatorics.py -q   -> 15 passed, 41 subtests passed
python -m pytest -q                               -> 304 passed, 41 subtests passed
```

Reverting only `mvp_server.py` (`git stash push -- mvp_server.py`) and
re-running the behavioural subset reproduced all 5 original failures,
confirming this is a true regression test rather than a tautology.

### Suspect findings investigated and dismissed (no code changed)

These looked wrong on first measurement and turned out to be correct. Recorded
so the next audit does not re-litigate them.

* **`integral(sin(x),0,pi)` -> 0.0861 instead of 2.** The active angle unit
  applies inside calculus, because `integral`/`diff` numerically operate on the
  function *as evaluated*. Degree gives `0.086107` (matches the closed form
  exactly), Radian gives `2.0000000000` (exact). **Correct in both units.**
* **`diff(sin(x))` at 30 -> 0.0151 instead of 0.8660.** Same cause: the
  derivative of *sin-degrees* is `(pi/180) * cos(30 deg) = 0.015115`, which is
  what is returned. Radian mode gives `cos(30 rad) = 0.15425145`, matching to 7
  figures. **Correct.**
* **`sigma(sin(x),1,3)` -> 0.1047.** Exactly
  `sin1deg + sin2deg + sin3deg = 0.104688`. **Correct.**
* **`sin(30)!` -> `Math ERROR`.** The operand `sin(30)` evaluates to `0.5`, and
  `0.5!` is undefined. `cos(0)! -> 1` confirms function-call operands do
  resolve. **Correct.**
* **`Rnd(2.5)` -> 2.5 rather than 3.** `Rnd` rounds per the Number Format
  setting (Norm -> 10 significant digits), not to an integer. **Correct per the
  fx-991EX User's Guide.**
* **`-2^2` -> -4.** Documented deliberately at `engine/parser.py:85-86`.
  **Correct.**
* **Keypad sequence returning 92.** Harness error. My probe sent the literal key
  `"+"` instead of the backend's key name `"plus"`; re-run correctly the
  sequence yields **14** in-process and over live HTTP.
* **`(5)C(2)` "masked" by the frontend.** Not a mitigation. `Ans C 2` and
  `(5)C((2))` are not covered by any of the 8 frontend regexes at
  `frontend.html:2549-2558`, so the backend defect was genuinely reachable.

---

## 16. Verified Working Features

* Arithmetic, precedence, parentheses, decimals, negation, left/right
  associativity, right-associative `^`.
* Math-IO fraction, mixed fraction, square root, cube root, n-th root,
  log-base, power and `Rnd` template serialization (12/12).
* fx-991EX-correct `-2^2` precedence; real odd roots for negatives.
* Overwrite/insert cursor editing, backspace, ALPHA+DEL undo, viewport scrolling.
* All 17 SHIFT and 14 ALPHA token mappings; SHIFT/ALPHA mutual exclusion and
  auto-clear; Complex-mode and Base-N-mode overrides.
* Trigonometry and inverse trigonometry in Degree/Radian/Gradian; hyperbolic
  family; log/ln/e/10/log_base; domain guards.
* Factorial (arbitrary operands, 170 cap), nPr, nCr (post-fix).
* Sigma, integral, derivative - angle-unit aware and numerically verified
  against closed forms in all three units.
* Pol, Rec, DMS, `r`/`g` suffixes, 43 constants, unit conversion, random and
  `RanInt`.
* Ans chaining; A-F/M/X/Y registers; CALC and SOLVE.
* Register, matrix, vector, statistics, distribution and spreadsheet isolation
  across mode switches, AC and power cycles.
* All 12 modes enter **and** compute.
* MENU (both pages, digits + D-pad + confirm), SETUP (with validation), OPTN,
  QR (with offline fallback), D-pad, SHIFT/ALPHA indicators, scroll indicators,
  display rendering, power on/off.
* Error contract: no user input crashes the app; empty input, malformed
  expressions, divide-by-zero, domain errors, oversized factorials, dimension
  errors and 500-character inputs are all handled.

---

## 17. Deferred / Intentional Limitations

1. **Implicit multiplication is unsupported by design.** `2(3+4)` and `3(4)`
   produce `Math ERROR`; the tokenizer has no rule for it. This is *explicitly
   documented* in `raw/handover.md:2713-2715` ("implicit multiplication is
   unsupported - the tokenizer has no rule for `2*x`; use an explicit `*`").
   The backend inserts an implicit `*` only for `Mat*`/`Vct*` names
   (`mvp_server.py:3287`). The code comment at `1158` claims implicit products
   "behave exactly as uppercase `X` already does" - that comment is
   **inaccurate** (`2X` also errors), but the behaviour itself is consistent.
2. **`mixed_frac(` has no evaluator.** `_token_for` maps SHIFT+`fraction` to
   the literal string `mixed_frac(` (`mvp_server.py:3078`), but `mixed_frac` is
   absent from `_SPECIAL_FUNCS` (line `55`) and has no handler, so the string
   would hit the tokenizer and raise `Math ERROR`. **Unreachable from the UI**:
   `frontend.html:8143` handles SHIFT+`fraction` locally
   (`insertMixedFraction()`), and the `mixed` template serializes to real
   arithmetic (section 5). The result-to-fraction conversion is served by
   `POST /api/fraction`. Latent dead mapping; not repaired because making it
   live would be new feature work, not a root-cause fix.
3. **Dead CSS** `#shiftIndicator::after` / `#alphaIndicator::after` keyed on
   `body.shift-on` / `body.alpha-on` (`frontend.html:1307-1310`) reference
   element IDs and body classes that exist nowhere in the file. The live
   indicator mechanism is `.status-tag.active` on `#indShift`/`#indAlpha`.
   Cosmetic only.
4. **`raw/code organisation/*.md` is a stale snapshot** (section 14, item 3).
5. **`Rec()` returns only the x-component** - a documented single-value display
   limitation carried over from `final_audit.md`.
6. **Spreadsheet formulas require a leading `=` and reject cell references.**
   `"2+3"` -> `Formula error`; `"=2+3"` -> 5; `"=A1*2"` -> `Formula error`.
   Each cell is evaluated independently.
7. **Backend `equals` on an empty expression returns `result:'0'`** rather than
   being a no-op. Frontend-safe (`shouldEvaluateScreen` at
   `frontend.html:2588` refuses to evaluate in `EMPTY`), so this is a lenient
   backend API contract, not a UI defect.
8. **`README.md:46-55` is inaccurate about verification** - it says the repo
   "uses two verification entry points instead of pytest" and describes
   `verify.py` as a functional suite that "exits non-zero on any failure".
   `verify.py` is a scroll-indicator linter with no failure path; pytest is the
   real suite. **Not edited** - documentation, not functionality, and out of
   scope for this pass. Flagged for the owner.
9. **A Base-N error leaves a stale `result` in the payload.** After a Base-N
   evaluation error, `display`/`error` are correct but the `result` field still
   carries the previous `lastResult` (and `resultDisplayed` stays `true`),
   because the error branches at `3268-3277` do not clear them. The frontend
   tests `error` first, so nothing stale is ever displayed. Low severity.
10. **Matrix `add` with mismatched dimensions reports `Math ERROR`, not
    `Dimension ERROR`** (multiplication does report `Dimension ERROR`
    correctly). Message-accuracy nit only.
11. **Tracked `__pycache__/*.pyc` files.** 18 `.pyc` files under
    `engine/*/__pycache__/` are tracked in git despite `.gitignore:2-3`. They are
    stale build artifacts that will keep appearing as spurious modifications.
    Removing them from the index is repository hygiene, not a functional fix, so
    it was **not** done here - flagged for the owner.

---

## 18. Environment Issues

* **No browser available.** KaTeX Math-IO rendering, the QR canvas, the OPTN /
  SETUP / QR overlays and the LCD CSS were verified by **static analysis plus
  `node` execution** of the extracted inline script (282 391 bytes,
  `node --check` -> exit 0), **not** by visual browser rendering. The
  `qrcodejs` and `katex` CDN scripts cannot load offline, so the documented
  fallbacks (`host.textContent = raw` at `frontend.html:2057`; QR URL text at
  `6395`) are the paths actually exercised.
* **`verify.py` cannot fail**, so it provides no regression signal (section 3.2).
* **`test_full.py`, `test_full2.py`, `test_server.py`, `test_engine.py`,
  `test_eval.py`, `test_safe_eval.py`** are ad-hoc scripts that define no
  `test_` functions. `pytest --collect-only` on that set reports
  *"no tests collected"*, so they contribute nothing to the suite; the first
  three would also collide on port 8080 if executed directly.
* Ports 8080 / 8137 / 8139 / 8141 were used during the audit; every spawned
  server process was terminated and no server was left running.
* All probe scripts were written to `%TEMP%\opencode\` and removed. The
  repository working tree contains only the intended changes (section 20).

---

## 19. Final Verdict

```text
Genuine bugs found ............ 1  (BUG-01 infix C combinatorics)
Bugs fixed .................... 1  (mvp_server.py, minimal root-cause fix)
Regression tests added ........ 15 tests / 41 subtests (test_infix_combinatorics.py)
Pre-existing tests broken ..... 0
Suite before fix .............. 289 passed, 12 subtests passed
Suite after fix ............... 304 passed, 41 subtests passed
Prior claims rechecked ........ 11  (9 verified working, 1 stale snapshot,
                                   1 real bug; plus 2 extra stale claims found)
Suspect findings dismissed .... 8   (recorded in section 15)
Deferred / intentional ....... 11 items (section 17)
Environment issues ............ 4 items (section 18)
```

**The emulator is functionally sound, and I found no evidence of a wrong
calculator answer.** Every arithmetic, scientific, memory, mode and error-path
result I could compute matched the fx-991EX specification, and no user input
crashed the application. The single real defect was an operator-recognition bug
in the infix-combinatorics path that made `nCr` unreachable for every
parenthesised or spaced form while `nPr` worked - now fixed, guarded by a
dedicated regression test, and aligned with the guard the frontend bridge had
already implemented.

I am **not** claiming the frontend is pixel-verified: without a browser, the
overlay menus and the KaTeX output rest on static analysis plus `node` syntax
and behavioural checks (section 18).

---

## 20. Evidence

### Files changed by this audit

```text
 M mvp_server.py                  +22 / -2   (BUG-01 fix)
?? test_infix_combinatorics.py    new, 15 tests / 41 subtests
?? FRESH_FUNCTIONAL_AUDIT.md      this file
```

Deliberately **not** changed: `frontend.html`, `engine/`, `README.md`, `raw/`,
`verify.py`, every pre-existing test, and the 18 tracked `.pyc` artifacts
(restored with `git checkout --` after they dirtied the tree).

### Key source locations

All `mvp_server.py` line numbers below are **post-fix**. `frontend.html` line
numbers are unchanged by this audit.

| Concern | Location |
|---|---|
| Infix-combinatorics operator scan | `mvp_server.py:_find_infix_pc` (895) |
| Infix-combinatorics rewrite | `mvp_server.py:_transform_combinatorics_infix` (1006) |
| **New** operator-index guard | `mvp_server.py:_infix_pc_operator_indices` (986) |
| **Fixed** register substitution | `mvp_server.py:safe_evaluate_expression` (1181-1201) |
| SHIFT/ALPHA token tables | `mvp_server.py:_token_for` (3061-3102) |
| `press_key` | `mvp_server.py` (3131-3494) |
| Backend menu sync | `mvp_server.py:_sync_menu_from_payload` (3005) |
| Cursor / result return / viewport | `mvp_server.py:_return_to_editing` (3479), `_update_viewport` (3487) |
| Factorial | `mvp_server.py:_transform_factorials` (780) |
| DMS | `mvp_server.py:_transform_dms` (850) |
| Percent | `mvp_server.py:_transform_percent` (271), `_percent_base` (226) |
| `Rnd` per Number Format | `mvp_server.py:_rnd_value` (100) |
| Base-N | `mvp_server.py:evaluate_base_n` (1349), `_convert_base` (2620) |
| Matrix/Vector expressions | `mvp_server.py:_MVParser` (1663), `evaluate_matvec_expression` (2082) |
| Matrix/Vector OPTN ops | `mvp_server.py:calculate_matrix` (2868), `calculate_vector` (2905) |
| CALC / SOLVE | `mvp_server.py:calc_evaluate` (2720), `solve_equation_newton` (2761) |
| SETUP validation | `mvp_server.py:update_setup_setting` (2266), `_validate_setting` (2187) |
| Complex-result rejection | `mvp_server.py` (3317-3323) |
| HTTP routing | `mvp_server.py:MvpHandler` (3501), `do_GET` (3561), `do_POST` (3615) |
| Font serving | `mvp_server.py` (3574-3591) |
| Frontend serialization | `frontend.html:serializeSlot` (2500) |
| Frontend infix guard (precedent) | `frontend.html` (3590-3603) |
| Frontend Math-IO rendering | `frontend.html:exprToLatex` (2021), `renderMath` (2046) |
| Frontend cursor | `frontend.html:makeCursor` (4186), `.lcd-cursor` (850, 1297) |
| Frontend indicators | `frontend.html` (1628-1629), (5808-5809) |
| Frontend QR | `frontend.html:showQRinLCD` (6385), (5961-5970), (8112) |

### Commands executed (verbatim)

```powershell
git status
git branch --show-current
git log -10 --oneline
python -m pytest -q
python -m pytest --collect-only -q
python verify.py
python main.py --smoke-test
python -m py_compile mvp_server.py
node --check <extracted frontend.html inline script>
python mvp_server.py --port 8137 --no-browser     # live HTTP probes, terminated
git stash push -- mvp_server.py ; python -m pytest test_infix_combinatorics.py ; git stash pop
git checkout -- engine/vector/__pycache__/vector_engine.cpython-311.pyc
```

### Reproduction of BUG-01 (post-fix tree)

```python
>>> from mvp_server import safe_evaluate_expression as S
>>> V = {k: 0.0 for k in "ABCDEF MXY".replace(" ", "")}
>>> S("(5)C(2)", 0.0, "Degree", V, False, ("Norm", 1))
10.0
>>> S("(5)P(2)", 0.0, "Degree", V, False, ("Norm", 1))
20.0
>>> S("(5+1)C(2)", 0.0, "Degree", V, False, ("Norm", 1))
15.0
>>> S("(5)C((2))", 0.0, "Degree", V, False, ("Norm", 1))
10.0
>>> S("5 C 2", 0.0, "Degree", V, False, ("Norm", 1))
10.0
>>> V2 = dict(V); V2["C"] = 99.0
>>> S("C", 0.0, "Degree", V2, False, ("Norm", 1)), S("5 C 2", 0.0, "Degree", V2, False, ("Norm", 1))
(99.0, 10.0)
```