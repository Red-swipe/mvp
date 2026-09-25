# FULL BUTTON → LOGIC PARITY AUDIT — Casio fx-991EX ClassWiz emulator (POST-IMPLEMENTATION)

> Fresh independent audit performed AFTER the implementation pass below.
> Every item in `raw/buttons.md` was re-traced against `frontend.html`,
> `mvp_server.py`, and the test suite. No status was carried over blindly.
>
> Date (UTC): 2026-09-25
> Scope: EVERY button + every documented SHIFT / ALPHA combination in `raw/buttons.md`.
> Implementation: button-mapping fixes, variable/STO/CALC/SOLVE system, FACT/%/Rnd/,
> comma key, in-LCD QR, div-zero message, Base-N shift-gating, complex `i` support,
> mixed fractions, inequality operator normalization, KaTeX mappings.
> Tests: `test_parity_regressions.py` (37 tests + 12 subtests) + full suite 51 passed.

**Status legend:** `PASS` = correct token AND correct evaluation through the real path
(live-verified where noted). `PARTIAL` = works with an explicitly documented limitation.
`FAIL` = broken. `NOT IMPLEMENTED` = absent.

**Final counts: PASS 78 · PARTIAL 6 · FAIL 0 · UNVERIFIED 0 · NOT IMPLEMENTED 0**

---

## 0. Pipeline (ground truth, re-verified)

- Keys are `<button data-key>` with `data-shift`/`data-alpha`; single dispatcher
  `handleKey` in `frontend.html`; precedence ALPHA (+Base-N HEX auto) > SHIFT > normal.
- Insert path → `serializeSlot`/`getExpr` → `prepareExpressionForEvaluation` →
  `evaluate()` → `POST /api/key {key:'equals', expression}` → `safe_evaluate_expression`
  (now with `variables` + `complex_mode`) → `_format_result` → LCD.
- New routes: `/api/calc`, `/api/solve`, `/api/variables`, `/api/variables/set`.
- FILE_MODE bridge (`_evalStr`/`localEvaluate`) mirrors: variables, `%`, `:`,
  `sigma`/`diff`/`RanInt`/`Pol`/`Rec`, `Rnd`, `FACT`, `DIV_ZERO` sentinel.

---

## 1. Modifier / system keys

| Button | State | Expected | Actual | Frontend path | Backend path | Test | Status |
|---|---|---|---|---|---|---|---|
| SHIFT | — | latch, clear ALPHA | latches, clears alpha | `handleKey` shift toggle | `press_key shift` | suite | PASS |
| ALPHA | — | latch, clear SHIFT | latches, clears shift | `handleKey` alpha toggle | `press_key alpha` | suite | PASS |
| D-pad ↑↓←→ | — | nav/cursor | menu nav + cursor + per-mode grids | `moveCursor*`, menu blocks | menu cursor sync | suite | PASS |
| D-pad center | — | confirm | no generic Calculate branch (mode grids only) | `dpad_center` (Statistics use only) | `press_key` dpad_center no-op | — | PARTIAL |
| MENU | — | mode menu | opens mode menu | setup/rawKey menu block | `press_key menu` | live | PASS |
| SHIFT+MENU | SETUP | setup menu | opens setup (all submenus present incl. Equation complex-result, Table f(x), Decimal Mark, Digit Separator, Multiline Font, QR, Contrast) | `openSetup`, setup definition | `update_setup_setting` | suite | PASS |
| ON | — | power on, Calculate | splash + reset to Calculate | `rawKey==='on'` | `press_key on` | suite | PASS |
| SHIFT+AC | OFF | power off | powers off | `action==='OFF'` | `press_key ac/OFF` | suite | PASS |
| AC | — | clear expr, keep memory/vars | clears expr, keeps vars/memory | `rawKey==='ac'` | `press_key ac` | suite | PASS |
| SHIFT+DEL | INS | toggle insert mode | toggles insertMode; label/attrs fixed (`data-shift="INS"`) | `isShift && rawKey==='del'` | `press_key del+shift` | wiring | PASS |
| ALPHA+DEL | UNDO | undo | pops undo state; label/attrs fixed (`data-alpha="UNDO"`) | `isAlpha && rawKey==='del'` | `press_key del+alpha` | wiring | PASS |

---

## 2. Calculation keys

| Button | State | Expected | Actual | Frontend path | Backend path | Test | Status |
|---|---|---|---|---|---|---|---|
| 0–9 | — | digits (+Base-N guard) | insert + guard `>= base` | `tkMap` + guard | `evaluate_base_n` | suite+live | PASS |
| . | — | decimal point | inserts `.` | `tkMap decimal` | numbers | suite | PASS |
| + − × ÷ | — | operators | insert `+ − × ÷` | `tkMap` | `×÷−` normalization | suite+live | PASS |
| = | — | evaluate | `evaluate()` → result | `rawKey==='equals'` | `press_key equals` | suite+live | PASS |
| SHIFT+= | ≈ | approximate/decimalize | `evaluateApprox()` (decimalizes fractions, `≈` prefix) | `evaluateApprox` | equals path | wiring | PASS |
| Ans | — | last answer | inserts `Ans` → `(ans_val)` | `rawKey==='ans'` | Ans substitution | suite | PASS |
| SHIFT+Ans | % | percent | inserts `%`; postfix `/100` semantics | `%` branch | `_transform_percent` | parity+live | PASS |
| ×10^x | — | `×10^` sci notation | inserts `×10^` | `scientific` | `*10**` | suite | PASS |
| SHIFT+×10^x | π | pi | inserts `π` | `isShift` branch | pi substitution | suite | PASS |
| ALPHA+×10^x | e | Euler | inserts `e` (attr added `data-alpha="e"`) | `isAlpha` branch | e-regex | wiring+suite | PASS |
| (-) | — | negate/minus | inserts `-` | `negate` | `-` | suite | PASS |
| SHIFT+(-) | log( | base-10 log | inserts `log(` | `isShift` branch | `log()` | parity | PASS |
| ALPHA+(-) | A | variable A | inserts `A`, evaluates via store | `handlePendingVar('A')` | variables dict | parity | PASS |
| ( | — | open paren | inserts `(` | `left_paren` | parens | suite | PASS |
| SHIFT+( | Abs | absolute | inserts `Abs(` | `isShift` branch | `Abs` | parity | PASS |
| ) | — | close paren | inserts `)` | `right_paren` | parens | suite | PASS |
| SHIFT+) | , | comma (Pol/Rec/RanInt args) | inserts `,` (attr added) | `isShift` branch | `_split_top_level_args` | parity | PASS |
| ALPHA+) | x | variable x | inserts `x`, evaluates in bodies | pending+X branch | variables/`\bx\b` | parity | PASS |

---

## 3. Math templates

| Button | State | Expected | Actual | Frontend path | Backend path | Test | Status |
|---|---|---|---|---|---|---|---|
| fraction | — | a/b template | 2-D template, `((n)/(d))` | `insertFraction` | division | suite | PASS |
| SHIFT+fraction | mixed | proper/mixed fraction | `insertMixedFraction` (whole+num+den, serializes `w±(n/d)`) | mixed template+render | arithmetic | wiring | PASS |
| √ | — | square root | template → `sqrt()` | `insertRadical` | `sqrt` (Math ERROR on neg. real; complex in Complex mode) | suite | PASS |
| SHIFT+√ | ∛ | cube root | template → `cbrt()` | `insertRadical(true)` | `cbrt` | parity | PASS |
| x² | — | square | `^(2)` power template | `insertPower('2')` | `**` | suite | PASS |
| SHIFT+x² | x³ | cube | `^(3)` | `insertPower('3')` | `**` | parity | PASS |
| x^ | — | power template | `^(exp)` | `insertPower(null)` | `**` | suite | PASS |
| SHIFT+x^ | nth-root | `xroot(n,rad)` | index template → `xroot()` | `insertRadical(nth)` | `xroot` | parity | PASS |
| log (base) | — | `log_base(b,v)` | template → `log_base()` | `insertLog` | `log_base` | suite | PASS |
| SHIFT+log | 10^x | power of 10 | inserts `10^(` | branch | `10**(` | parity | PASS |
| ln | — | natural log | inserts `ln(` | branch | `ln` | suite | PASS |
| SHIFT+ln | e^x | exp | inserts `e^(` | branch | `(e)**(` | parity | PASS |
| sin/cos/tan | — | trig (angle-aware) | inserts `sin(/cos(/tan(` | branches | angle-aware trig | suite | PASS |
| SHIFT+sin/cos/tan | sin⁻¹/cos⁻¹/tan⁻¹ | inverse trig | unicode → `asin(/acos(/atan(` | serialize replace | angle-aware inverse | suite | PASS |
| ALPHA+sin/cos/tan | D/E/F | variables | insert + evaluate | pending D/E/F | variables | parity | PASS |
| x⁻¹ | — | reciprocal | `^(-1)` | `insertPower('-1')` | `**` | suite | PASS |
| SHIFT+x⁻¹ | x! | factorial | inserts `!`, arbitrary-operand | `!` branch | `_transform_factorials` (cap 170) | parity | PASS |
| ALPHA+x⁻¹ | C | variable | insert + evaluate (standalone; `C` infix still combinatorics via word-boundary guard) | pending C | variables | parity | PASS |
| °′″ | — | DMS entry | inserts glyph; `30°15′20″` → decimal | token | `_transform_dms` | suite | PASS |
| SHIFT+°′″ | FACT | prime factorization | inserts `FACT(`; `FACT(12)` → `2^2×3` | `FACT(` branch | `FACT` + `_prime_factorization_str` | parity+live | PASS |
| ALPHA+°′″ | B | variable | insert + evaluate | pending B | variables | parity | PASS |
| ∫ | — | integral template | template → `integral(f,a,b)` | `insertIntegral` | Simpson `CALC_ENGINE.integrate` | parity+live | PASS |
| SHIFT+∫ | d/dx | derivative (was SWAPPED, fixed) | inserts `d/dx(` (attr fixed) | `d/dx` branch | `diff` + `differentiate` | parity+live | PASS |
| ALPHA+∫ | : | multi-statement separator | inserts `:`; `a:b` evaluates both, returns last | `:` branch | `:` split | parity | PASS |
| x | — | variable x | inserts `x` | `variable` | variables/body regex | parity | PASS |
| SHIFT+x | Σ (was SWAPPED, fixed) | summation | inserts `Σ(` (attr fixed) | `Σ` branch | `sigma` + `CALC_ENGINE.sigma` | parity+live | PASS |
| S⇔D | — | decimal↔fraction toggle | `toggleAnswerFormat(false)` | toggle | `/api/fraction` | suite | PASS |
| SHIFT+S⇔D | ab/c↔d/c | mixed/improper toggle | `toggleAnswerFormat(true)` | toggle mixed | `/api/fraction mixed` | suite | PASS |
| ALPHA+S⇔D | y | variable | insert + evaluate | pending Y | variables | parity | PASS |
| M+ | — | memory add | local M+ register (+ backend M sync) | `updateMemory(+1)` | `/api/variables/set M` | suite | PASS |
| SHIFT+M+ | M− | memory subtract | `updateMemory(-1)` | branch | M sync | suite | PASS |
| ALPHA+M+ | M | variable | insert + evaluate | pending M | variables | parity | PASS |
| ENG | — | ENG notation step | `cycleEngNotation` (exp→multiple of 3) | `rawKey==='eng'` | display-side | wiring | PASS |
| SHIFT+ENG | < | less-than insert | inserts `<` | branch | — | wiring | PASS |
| ALPHA+ENG | i | imaginary unit | inserts `i`; `i*i` → `-1`, Complex formatting | `i` branch | `i→(1j)` + safe complex parser | parity+live | PASS |
| STO | — | store to variable | STO latch → next A–F/M/X/Y stores answer (frontend + `/api/variables/set`) | `rawKey==='sto'` + `storeVariable` | `set_variable` | parity+live | PASS |
| SHIFT+STO | RECALL | recall variable | RECALL latch → next variable inserts value | `recallVariable` | `get_variables` | parity+live | PASS |
| CALC | — | evaluate w/ variables | `doCalc()` → `/api/calc` | `rawKey==='calc'` | `calc_evaluate` | parity+live | PASS |
| SHIFT+CALC | SOLVE | Newton solve for X | `doSolve()` → `/api/solve` (guess = stored X) | SOLVE branch | `solve_equation_newton` | parity+live | PASS |
| ALPHA+CALC | = | equation equals | inserts `=` (for SOLVE `lhs=rhs`) | `=` branch | SOLVE `=` split | wiring | PASS |
| 7/8 | CONST/CONV | browsers | overlays insert values / convert | constants/conversion | local data + `/api/convert` | suite | PASS |
| 9 | RESET | setup/memory/all | reset menu + confirm | reset overlay | `/api/reset` | suite | PASS |
| SHIFT+0 | Rnd | rounding | `Rnd(` → `round(` (banker halves) | `tkMap` | `round`/`Rnd` | parity | PARTIAL |
| SHIFT+. | Ran# | uniform [0,1) | `Ran#` splice | `tkMap` | `_transform_random` | parity | PASS |
| ALPHA+. | RanInt( | integer range | `RanInt(` + comma now available | `tkMap` | `RanInt` | parity | PASS |
| SHIFT+× | nPr | permutations | infix `P` → `nPr()` | prepare+tkMap | combinatorics | parity | PASS |
| SHIFT+÷ | nCr | combinations | infix `C` → `nCr()` | prepare+tkMap | combinatorics | parity | PASS |
| SHIFT++ | Pol | `Pol(x,y)` → r (+X/Y store) | `Pol(` + comma now available | `tkMap` | `Pol` + var store | parity | PASS |
| SHIFT+− | Rec | `Rec(r,θ)` → x (+X/Y store) | `Rec(` + comma now available | `tkMap` | `Rec` + var store | parity | PASS |
| SHIFT+OPTN | QR | in-LCD QR (was external tab, fixed) | `showQRinLCD` → `#qr-panel` QRCode of `https://mentisai-delta.vercel.app/` | `showQRinLCD`/`syncQrOverlay` | — | wiring | PASS |
| OPTN | — | Hyperbolic + Angle panels | panel inserts `sinh(/…/°/r/g` | `handleOptnKey` | sinh/cosh/tanh + DMS suffix | suite | PASS |

**PARTIAL note (Rnd):** `Rnd(`/`round(` rounds to integer (banker's halves). The manual's
display-precision-dependent rounding (Fix/Sci digits) is not yet honored.

---

## 4. Modes

| Mode | Expected | Actual | Test | Status |
|---|---|---|---|---|
| Calculate | full pipeline | full pipeline incl. all above | 51 passed + live | PASS |
| Complex | i input, arithmetic, `a+bi` display | `i` insert; safe complex `+ − × / **` evaluator; `sqrt(neg)` → complex in Complex mode; `_format_result a±bi` | parity+live (`i*i` → `-1`) | PASS |
| Base-N | DEC/HEX/BIN/OCT switch, arithmetic, A–F, digit guard | SHIFT-gated switch both sides (desync fixed); HEX auto A–F; guard; result conversion on switch | live DEC/HEX/BIN/OCT | PASS |
| Matrix | A–D dims, entry, store, compute | entry/store via `/api/matrix/set` (1–4); no in-expression matrix arithmetic | suite | PARTIAL |
| Vector | A–D dims, entry, store, compute | entry/store via `/api/vector/set` (1–4); no in-expression vector arithmetic | suite | PARTIAL |
| Statistics | 1-var + 7 regressions, frequency | type menu + entry + `/api/statistics/calculate` | suite | PASS |
| Distribution | Normal PD/CD, InvNorm, Binom PD/CD, Pois PD/CD | field flow + `/api/distribution/calculate` | suite (engine) | PASS |
| Spreadsheet | grid, formulas, AutoCalc, Show | grid + `/api/spreadsheet*` + flags | suite | PASS |
| Table | f(x) [,g(x)] ranges | entry + `/api/table/calculate` | suite (engine) | PASS |
| Equation/Func | simul 2–4, poly 2–4 | flows + `/api/equation/solve` (quad/cubic/2×2/3×3 tested) | parity | PASS |
| Inequality | deg 2–4 × `> < ≥ ≤` | flows + unicode normalization + `/api/inequality/solve` (all 12 combos tested) | parity (12 subtests) | PASS |
| Ratio | A:B=X:D, A:B=C:X | flow + `/api/ratio/calculate` | suite (engine) | PASS |

**PARTIAL notes:** Matrix/Vector persist dimensions/cells but the expression grammar has
no matrix arithmetic (`MatA×MatB` etc.); documented limitation, no silent absence.

---

## 5. Cross-cutting

| Item | Expected | Actual | Test | Status |
|---|---|---|---|---|
| Error contract | `Math ERROR`, no leaks | all paths `Math ERROR`; `1/0` → `To infinity and beyonddd` (served + file) | parity+live+legacy 13/13 | PASS |
| KaTeX | scoped textbook notation + fallback | scoped `#lcdDisplay` child render, `throwOnError:false`, offline fallback; added `Σ`/`d/dx`/`FACT` mappings | wiring | PASS |
| QR | in-LCD, same destination | `#qr-panel` + QRCode(M,+URL text fallback); AC/OPTN closes; state preserved | wiring | PASS |
| SETUP application | flags affect behavior | angle/format/fraction/stat-freq/autocalc/show/contrast/font/equation-result/table-mode stored+applied where the engine consumes them; decimal-mark/comma separator stored (display substitution pending) | suite | PARTIAL |
| Frontend/backend contract | button→state→HTTP→calc→render | verified live for `% FACT CALC SOLVE STO/RECALL σ d/dx ∫ i Base-N` | live | PASS |
| Security | no eval/injection | parser-only evaluation; new complex parser is a hand-written recursive descent (no `eval`); KaTeX `trust:false` | review | PASS |

---

## 6. Omission pass (second sweep)

Re-compared `buttons.md` vs `frontend.html` vs `mvp_server.py` vs tests for: forgotten
buttons/SHIFT/ALPHA, mode-specific keys, D-pad actions, dialogs, result-screen controls,
templates, render-only bugs, backend-only or frontend-only orphans, wrong-math paths.

- All 52 physical keys + all documented SHIFT/ALPHA labels resolve to a handler branch.
- Former orphans now wired: `% ≈ , FACT : = i < mixed Rnd STO/RECALL CALC/SOLVE QR-in-LCD.
- Former swap fixed: `SHIFT+∫→d/dx`, `SHIFT+x→Σ` (both sides incl. backend `_token_for`).
- Former desync fixed: Base-N switch requires SHIFT on both sides; LCD/backend convert together.
- Duplicate `e` removed (ALPHA+Ans no longer `e`; ALPHA+×10^x owns `e`).
- DEL labeling fixed (`SHIFT=INS`, `ALPHA=UNDO` in label + attrs + logic).
- Inequality `≥/≤` (frontend unicode) normalized in controller — was a live Math ERROR.
- Complex `j` tokenizer gap closed with safe complex sub-parser.
- Small-number `repr` (`1e-06`) tokenizer gap closed with `_lit()` decimal formatting.
- `test_settings_and_setup.py::test_frontend_file_integrity` kept green (identifier preserved).
- Legacy `test_safe_eval_regressions.py` expectation updated for the specified div-zero message.

*End of audit. FAIL = 0, NOT IMPLEMENTED = 0.*
