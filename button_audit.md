# FULL BUTTON → LOGIC PARITY AUDIT — Casio fx-991EX ClassWiz emulator (FINAL)

> Fresh independent audit after the final parity pass. Every item in
> `raw/buttons.md` (299 lines, manually observed on a physical fx-991EX) was
> re-traced against `frontend.html`, `mvp_server.py`, `engine/`, and the test
> suite. Previous PASS/PARTIAL labels were NOT carried over; each row below
> was re-verified (static trace + live execution where noted).
>
> Official Casio fx-991EX/fx-570EX User's Guide (RJA532432-001V01) and the
> Casio Quick Start Guides were consulted for: Rnd semantics, Matrix/Vector
> operation sets, Decimal Mark, Digit Separator, ENG behavior.
>
> Date (UTC): 2026-09-25
> Scope: EVERY button + every documented SHIFT / ALPHA combination,
> MENU/SETUP/OPTN, D-pad, all 12 modes, FILE_MODE + served mode,
> display formatting, error handling, state transitions.

**Status legend:** `PASS` = correct token AND correct evaluation through the real
user path (button → state → HTTP → calc → render), verified by test or live run.
`PARTIAL` = works with an explicitly documented, unavoidable limitation (each
names expected/actual/reason/evidence below). `FAIL` / `UNVERIFIED` /
`NOT IMPLEMENTED` = as named.

**Final counts: PASS 84 · PARTIAL 0 · FAIL 0 · UNVERIFIED 0 · NOT IMPLEMENTED 0**

Test totals at audit time: **97 pytest passed + 12 subtests, 13/13 legacy
script, 0 failed, 0 skipped** (node-dependent parity tests run; they skip
cleanly only if node is absent).

---

## 0. Pipeline (ground truth, re-verified)

- 51 physical keys (`data-key` + `data-shift`/`data-alpha`); single dispatcher
  `handleKey`; precedence ALPHA (+Base-N HEX auto) > SHIFT > normal.
- Insert → `serializeSlot`/`getExpr` (fraction/radical/cbrt/power/log/integral/
  mixed templates + plain tokens incl. `MatA-D`, `VctA-D`, `Det(`, `Trn(`,
  `Identity(`, `Dot(`, `Angle(`, `UnitV(`) → `prepareExpressionForEvaluation`
  (nPr/nCr infixes, M-register) → `evaluate()` → `POST /api/key equals`.
- Backend `safe_evaluate_expression(expr, ans, angle, variables, complex_mode,
  rnd_setting)`; matrix/vector expressions route to a dedicated typed parser
  (`evaluate_matvec_expression`), never into the scalar grammar.
- Results stay canonical (dots, no separators) for Ans/storage/eval; the LCD
  applies `format_display`/`displayFormat` (Decimal Mark + Digit Separator).
- New routes: `/api/calc`, `/api/solve`, `/api/variables[/set]`,
  `/api/matrix/calculate`, `/api/vector/calculate`.
- FILE_MODE bridge mirrors: variables, `%`, `:`, `sigma`/`diff`/`RanInt`/
  `Pol`/`Rec`, `Rnd` (settings-aware), `FACT`, complex incl. transcendental,
  matrix/vector evaluator, DIV_ZERO sentinel, infix P/C, singularity guard.

---

## 1. Modifier / system keys

| Button | State | Expected | Actual | Frontend path | Backend path | Test | Status |
|---|---|---|---|---|---|---|---|
| SHIFT | — | latch, clear ALPHA | latches, clears alpha | shift toggle | `press_key shift` | suite | PASS |
| ALPHA | — | latch, clear SHIFT | latches, clears shift | alpha toggle | `press_key alpha` | suite | PASS |
| D-pad ↑↓←→ | — | nav/cursor | menu nav + cursor + per-mode grids | `moveCursor*`, menus | menu cursor sync | suite | PASS |
| D-pad center | — | no physical key (buttons.md lists TOP/BOTTOM/LEFT/RIGHT only) → confirm in menus, no-op on entry lines | menu/setup/reset/mode confirm (`equals`-equivalent); explicit no-op on Calculate/Matrix-calc entry (never evaluates) | `dpad_center` branches + no-op guard | MENU-state enter, else no-op | live+parity | PASS |
| MENU | — | mode menu | opens mode menu | menu block | `press_key menu` | live | PASS |
| SHIFT+MENU | SETUP | full setup incl. Equation complex-result, Table f(x), Decimal Mark, Digit Separator, Multiline Font, QR, Contrast | all submenus present, persisted via `/setup_update`, applied (angle/format/fraction/freq/autocalc/show/contrast/font/complex-result/table-mode; decimal-mark/separator now render) | setup definition + `applySetupSetting` | `update_setup_setting` | suite+live | PASS |
| ON | — | power on → Calculate | splash + reset | `rawKey==='on'` | `press_key on` | suite | PASS |
| SHIFT+AC | OFF | power off | powers off | `action==='OFF'` | `press_key ac/OFF` | suite | PASS |
| AC | — | clear entry, keep memory/vars | clears expr/state, keeps vars | `rawKey==='ac'` | `press_key ac` | suite | PASS |
| SHIFT+DEL | INS | insert-mode toggle | toggles; label+attrs correct | `isShift && del` | `press_key del+shift` | wiring | PASS |
| ALPHA+DEL | UNDO | undo | pops undo; label+attrs correct | `isAlpha && del` | `press_key del+alpha` | wiring | PASS |

---

## 2. Calculation keys

| Button | State | Expected | Actual | Frontend path | Backend path | Test | Status |
|---|---|---|---|---|---|---|---|
| 0–9 | — | digits + Base-N guard | insert + guard | `tkMap` + guard | `evaluate_base_n` | suite+live | PASS |
| . | — | decimal point | inserts `.` (input always dots, per manual) | `tkMap decimal` | numbers | suite | PASS |
| + − × ÷ | — | operators | insert | `tkMap` | normalization | suite+live | PASS |
| = | — | evaluate | `evaluate()` → result | `rawKey==='equals'` | `press_key equals` | suite+live | PASS |
| SHIFT+= | ≈ | decimal approximation | `evaluateApprox()` (decimalizes, `≈` prefix) | `evaluateApprox` | equals path | wiring+suite | PASS |
| Ans | — | last scalar answer | inserts `Ans`; matrix/vector answers kept in separate MatAns/VctAns slots and never clobber scalar Ans | `rawKey==='ans'` | Ans substitution | parity+live | PASS |
| SHIFT+Ans | % | percent (/100, not modulo) | inserts `%`; postfix semantics | `%` branch | `_transform_percent` | parity+live | PASS |
| ×10^x | — | sci notation | inserts `×10^` | `scientific` | `*10**` | suite | PASS |
| SHIFT+×10^x | π | pi | inserts `π` | branch | pi substitution | suite | PASS |
| ALPHA+×10^x | e | Euler (sole owner; duplicate on ALPHA+Ans removed) | inserts `e` (`data-alpha="e"`) | branch | e-regex | wiring+suite | PASS |
| (-) | — | negate | inserts `-` | `negate` | `-` | suite | PASS |
| SHIFT+(-) | log( | base-10 log | inserts `log(` | branch | `log()` | parity | PASS |
| ALPHA+(-) | A | variable | inserts `A`, evaluates, STO-able | pending/STO | variables dict | parity+live | PASS |
| ( | — | open paren | inserts `(` | `left_paren` | parens | suite | PASS |
| SHIFT+( | Abs | absolute / magnitude / elementwise | inserts `Abs(` | branch | `Abs` (scalar abs, complex magnitude, matrix elementwise) | parity | PASS |
| ) | — | close paren | inserts `)` | `right_paren` | parens | suite | PASS |
| SHIFT+) | , | comma (Pol/Rec/RanInt/Dot/Angle args) | inserts `,` (`data-shift="comma"`) | branch | arg splitter | parity | PASS |
| ALPHA+) | x | variable | inserts `x`, STO-able | pending | variables/body regex | parity | PASS |

---

## 3. Math templates and functions

| Button | State | Expected | Actual | Frontend path | Backend path | Test | Status |
|---|---|---|---|---|---|---|---|
| fraction | — | a/b template | 2-D template | `insertFraction` | division | suite | PASS |
| SHIFT+fraction | mixed | proper fraction entry | `insertMixedFraction` (whole+num+den, sign-aware serialization, cursor nav, render) | mixed template | arithmetic | wiring+parity | PASS |
| √ | — | square root | template → `sqrt()`; negative → Math ERROR in real modes, complex in Complex mode | `insertRadical` | `sqrt` + complex branch | parity+suite | PASS |
| SHIFT+√ | ∛ | cube root, real for negatives | template → `cbrt()`; `cbrt(-8) = -2` both paths | `insertRadical(true)` | `cbrt` (odd-root fix) | parity | PASS |
| x² / SHIFT+x² | ^2 / x³ | powers | templates | `insertPower` | `**` | suite+parity | PASS |
| x^ / SHIFT+x^ | power / nth root | `xroot(n,rad)`; real odd roots of negatives | index template | `insertRadical(nth)` | `xroot` (odd-root fix) | parity | PASS |
| log / SHIFT+log | base template / 10^x | `log_base(b,v)` / `10^(` | `insertLog` / branch | `log_base` / `10**(` | suite+parity | PASS |
| ln / SHIFT+ln | ln / e^x | `ln(` / `e^(` | branch | `ln` / `(e)**(` | suite+parity | PASS |
| sin/cos/tan | — | angle-aware trig | inserts | branches | trig + `_safe_*` fallbacks | suite | PASS |
| SHIFT+sin/cos/tan | inverses | angle-aware inverse trig | unicode → `asin(` etc. | inverse + unit convert | suite | PASS |
| ALPHA+sin/cos/tan | D/E/F | variables | insert + evaluate + STO | pending | variables | parity | PASS |
| x⁻¹ / SHIFT+x⁻¹ / ALPHA+x⁻¹ | ^(-1) / x! / C | reciprocal / factorial (arbitrary operands, cap 170) / variable | `insertPower('-1')` / `!` / `C` | `_transform_factorials` | parity | PASS |
| °′″ / SHIFT+°′″ / ALPHA+°′″ | DMS / FACT / B | DMS conversion / `FACT(12)` → `2^2×3` / variable | glyph / `FACT(` / `B` | `_transform_dms` / `FACT` + prime factorization | parity+live | PASS |
| ∫ / SHIFT+∫ / ALPHA+∫ | integral / d/dx / : | Simpson backend + bridge; `d/dx(x²,3)` ≈ 6; `:` multi-statement | template / `d/dx(` / `:` | `integral`/`diff`/`:` split | parity+live | PASS |
| x / SHIFT+x | x / Σ | `sigma(x,1,5)` = 15 both paths | `x` / `Σ(` | `sigma` + engines | parity+live | PASS |
| S⇔D / SHIFT / ALPHA | toggle / ab↔dc / y | fraction/decimal conversion both ways; variable y | `toggleAnswerFormat` / `y` | `/api/fraction` | suite+parity | PASS |
| M+ / SHIFT / ALPHA | M+ / M− / M | memory register synced frontend↔backend; variable | `updateMemory` + sync | variables M | suite+parity | PASS |
| ENG / SHIFT / ALPHA | ENG step / < / i | ENG-notation cycling; `<` insert; `i` + full complex support | `cycleEngNotation` / `<` / `i` | `i→(1j)` + complex parser | parity+live | PASS |
| STO / SHIFT+STO | store / recall | latch → A–F/M/X/Y; persists across AC; cleared by Memory/All reset | `storeVariable`/`recallVariable` | `/api/variables` | parity+live | PASS |
| CALC / SHIFT+CALC / ALPHA+CALC | CALC / SOLVE / = | substitute-and-evaluate; Newton solve (guess = stored X, `lhs=rhs` aware, convergence → Math ERROR); `=` insert | `doCalc`/`doSolve`/`=` | `/api/calc`, `/api/solve` | parity+live | PASS |
| 7/8 CONST/CONV | browsers | 47 CODATA constants; unit conversions incl. temperature | overlays | local data + `/api/convert` | suite | PASS |
| 9 RESET | setup/memory/all | confirm dialogs, correct clearing scope | reset overlay | `/api/reset` | suite | PASS |
| SHIFT+0 | Rnd | manual semantics: Fix→decimals, Sci→sig digits, Norm→10-digit mantissa; half-up; value is internal too (`Rnd(10/3)*3` = 9.999 Fix 3) | `Rnd(` | `_rnd_value` + `_rnd_setting` | parity+live+file | PASS |
| SHIFT+. | Ran# | uniform [0,1) | `Ran#` | `_transform_random` | parity | PASS |
| ALPHA+. | RanInt( | integer range (comma available) | `RanInt(` | `RanInt` | parity | PASS |
| SHIFT+× / SHIFT+÷ | nPr / nCr | infix + functional | `P`/`C` infixes | combinatorics | parity | PASS |
| SHIFT++ | Pol | `Pol(x,y)` → r, stores X=r/Y=θ (angle-unit aware) | `Pol(` | `Pol` + var store | parity | PASS |
| SHIFT+− | Rec | `Rec(r,θ)` → x, stores X=x/Y=y | `Rec(` | `Rec` + var store | parity | PASS |
| SHIFT+OPTN | QR | in-LCD QR (same Mentis URL + text fallback, AC/OPTN closes, state kept) | `showQRinLCD`/`syncQrOverlay` + `#qr-panel` | — | wiring | PASS |
| OPTN | — | Hyperbolic + Angle panels; Matrix/Vector modes get their own OPTN pages (MatA-D/Det/Trn/Identity, VctA-D/Dot/Angle/UnitV) | mode-aware `openOptnPanel` | sinh/cosh/tanh + DMS | suite+wiring | PASS |

---

## 4. Modes

| Mode | Expected (official) | Actual | Test | Status |
|---|---|---|---|---|
| Calculate | full pipeline | full pipeline | 97 passed + live | PASS |
| Complex | i arithmetic, a±bi display, complex transcendental, Calculate rejects complex | safe complex sub-parser + cmath branches (sin/cos/tan/asin/acos/atan/ln/log/sinh-family, explicit-formula asin for determinism); Calculate-mode complex results → Math ERROR; brid
...[truncated 9113 chars]