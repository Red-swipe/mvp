# FRONTEND MATH I/O VISUAL PARITY AUDIT — fx-991EX ClassWiz Emulator

Scope: frontend visual + interaction parity of `frontend.html` (Math I/O,
typography, KaTeX integration, templates, symbols, SHIFT/ALPHA, mode screens).
The backend/calculation layer was **not** re-audited; where a backend value is
quoted it is used only as evidence that a frontend representation is wrong.

---

## 1. Baseline

```
HEAD:   1195232  "audit: fresh functional parity pass"
        11952321ecef641d26015a09b7ab1b59edd64ae9
branch: main
pytest: 304 passed, 41 subtests passed in 19.30s
```

Browser tooling used for Phase 13: **Playwright (Python) + Google Chrome
(channel=`chrome`)** — both present, so the audit is based on real rendered
DOM, computed styles and real key dispatch, not static reading. No limitation
to document.

Independent ground truth for glyph coverage was obtained with `fontTools`
against the real asset `ClassWizFontSet/CASIOClassWizCW01.ttf`.

---

## 2. Findings

| Area | Status | Evidence | Fix |
|---|---|---|---|
| Fonts | **FAIL → PASS** | `.lcd-expr-content`/`.lcd-result-line` declared `font-family: monospace`, bypassing the LCD face entirely (computed style read back as `monospace`). `CASIOClassWizCW01.ttf` carries only 116 glyphs — ASCII plus 18 extras — so 36 of 67 audited math code points had **no glyph** and the browser substituted an arbitrary face for exactly those while digits stayed correct. `Courier New` additionally lacks `⁻` U+207B and `⁹` U+2079. | Removed the two `font-family` overrides so both lines inherit `.lcd`. Declared the stack `'CASIO ClassWiz', "Cambria Math", "Segoe UI Symbol", monospace` (per-character CSS fallback). Added `.math-sym` and routed every text token containing a code point the LCD face lacks through it. `Cambria Math`/`Segoe UI Symbol` cover 38/38 audited glyphs. |
| KaTeX | **PARTIAL → PASS** | `#lcdSpreadsheet *` and `#lcdDistribution *` forced Courier New on every descendant; an id selector (1,0,0) outranks KaTeX's own `.katex` (0,1,0), so `.katex` computed to `"Courier New"`. Wrapper className was `"katex-lcd-wrapkatex-inline"` (missing space). The no-KaTeX fallback printed raw LaTeX. Pressing `=` re-typeset the **editable input line** with KaTeX, deleting the cursor and every slot and jumping the font to KaTeX_Main. | Removed both universal font rules (container stacks now name a math face). Fixed the wrapper className. `renderMath()` takes a plain-text fallback. The editable line is no longer re-typeset; KaTeX owns the result/error/matrix lines only. |
| Fractions | PASS | Real stacked template (`math-fraction` / `math-numerator` / `math-fraction-bar` / `math-denominator`), cursor owns both slots, ▲▼ traverse, nested fractions work, `((1)/(2))` serializes. | Exact-answer **results** (`1/2`, `1 23/45`) reached KaTeX as inline slashes; now typeset as `\frac{1}{2}` / `1\frac{23}{45}`. |
| Mixed fraction | PASS | `math-mixed-row` with whole + nested fraction; `((1)+((23)/(45)))`. | — |
| d/dx | **FAIL → PASS** | `SHIFT+∫` emitted the raw text token `d/dx(`: no template, no slot, unbalanced paren, and `localEvaluate('d/dx(2)')` threw Math ERROR. Only the backend `diff(x^2,3)=6` worked. | New `derivative` template (`d` over a fraction bar over `dx` + one editable box) per `raw/buttons.md`. Cursor starts in the body slot. Serializes to `diff(body, <X register>)`. |
| Sigma | **FAIL → PASS** | `SHIFT+x` emitted the raw text token `Σ(`: no template, no bounds slots, unbalanced paren. | New `sigma` template rendering `ⁿΣₘ x=[term]` with upper above, lower beneath and `x=` in front, per `raw/buttons.md`. Reading order lower→upper→body. Serializes to `sigma(body,lower,upper)`. |
| Integral | PASS | Already a real template: `∫` with upper/lower/body/`dx`, ▲▼ reach the bounds, `integral(x^2,0,3)=9`. | Navigation generalised to cover `sigma` identically. |
| Powers | PASS | `x²`/`x³`/`x⁻¹` use the `power` template with a real `math-power-exp` slot. | — |
| Roots | PASS | `√`, `∛` (root index `3`), `ˣ√` (editable `math-root-index`) all templates. | — |
| Log | PASS | `math-log-sub` + `math-log-arg` slots → `log_base(2,8)`. | — |
| Symbols | **FAIL → PASS** | 36 audited code points absent from the LCD face; `sin⁻¹(` contains U+207B which neither the LCD face nor Courier New can draw; keycap legends used Times New Roman, which lacks ∛ ∇ ∈ ∅ ∀ ∃ ∥. | All non-LCD-font characters in a text token now render inside `.math-sym`; keycap/legend/OPTN stacks name a math face. Verified: **0 of 36** escape the wrapper. |
| SHIFT/ALPHA | **FAIL → PASS** | The printed legends and `data-shift` attributes for the ∫ and x keys were **swapped** relative to `raw/buttons.md` and the real device (∫ printed `Σ`, x printed `d/dx`). ALPHA on the x key was entirely unmapped, so `ALPHA+x` produced `X` instead of `y`. | Legends and attributes corrected to `SHIFT+∫ → d/dx`, `SHIFT+x → Σ`; `ALPHA+x → y` wired (legend, attribute and routing). |
| Statistics | PASS | Inherits the corrected LCD stack; `σ`/`μ` labels resolve. | — |
| Spreadsheet | **FAIL → PASS** | `#lcdSpreadsheet *` re-typed KaTeX output in Courier New. | Universal rule removed. |
| Equation | PASS | Inherits the corrected LCD stack. | — |
| Matrix | PASS | Result typeset by KaTeX inside `#lcdDisplay`; brackets/dimensions/cells intact. | — |
| Vector | PASS | As Matrix. | — |
| Distribution | **FAIL → PASS** | `#lcdDistribution *` re-typed KaTeX output in Courier New. | Universal rule removed. |

---

## 3. Confirmed Bugs

### TYPO-1 — Math I/O lines bypassed the calculator typeface
* **File** `frontend.html`
* **Component** `.lcd-expr-content`, `.lcd-result-line`
* **Observed** computed `font-family` was `monospace`; the LCD's own
  `'CASIO ClassWiz'` face was never used on the expression or result line.
* **Expected** both lines inherit `.lcd`, i.e. the ClassWiz LCD face.
* **Root cause** a `font-family: monospace` override on both rules, contradicting
  the file's own comment that the LCD keeps the ClassWiz TTF.
* **Fix** removed both declarations.
* **Regression test** `TestTypographyRendered::test_expression_and_result_lines_use_the_calculator_typeface`,
  `TestTypographySource::test_expression_and_result_lines_do_not_declare_their_own_font`

### TYPO-2 — 36 mathematical code points had no glyph and were silently substituted
* **File** `frontend.html` + `ClassWizFontSet/CASIOClassWizCW01.ttf`
* **Component** whole LCD
* **Observed** the reported symptom exactly: digits and ASCII letters rendered in
  the calculator face while π √ ∛ Σ ∫ ∞ × ÷ − ° ≠ ≤ ≥ ⁻ ⁹ ′ ″ · ± ∂ ∇ ∈ ∅ ∀ ∃ ≡ ≈ Ω
  α β θ λ ∥ ³ fell back to a different font — the "gibberish" mathematics.
* **Expected** mathematics drawn from a face that has those glyphs.
* **Root cause** the LCD face carries 116 glyphs (ASCII + 18 extras) and no maths;
  CSS per-character fallback therefore substituted an arbitrary system font for
  precisely those code points. This is a font-coverage defect, not a
  random-fallback-band-aid.
* **Fix** named a real math face after the LCD face in the stack, **and** added
  `.math-sym`, applied at render time to any text token containing a code point
  the LCD face lacks (`LCD_TEXT_FONT_CHARS` / `needsMathFont` / `appendTokenDOM`).
* **Regression test** `TestTypographyRendered::test_every_math_symbol_the_lcd_font_lacks_gets_a_math_face`
  plus `test_lcd_font_really_lacks_those_code_points`, which cross-checks the
  assertion against the TTF cmap with `fontTools`.

### TYPO-3 — Universal font rules re-typed every KaTeX glyph
* **File** `frontend.html`
* **Component** `#lcdSpreadsheet *`, `#lcdDistribution *`
* **Observed** rendering `\sqrt{25}+\pi` into those hosts produced
  `.katex` computed to `"Courier New", Courier, monospace` instead of `KaTeX_Main`.
* **Expected** KaTeX controls the fragment it renders.
* **Root cause** CSS specificity: id selector (1,0,0) beats class (0,1,0).
* **Fix** removed both rules; container stacks now name a math face.
* **Regression test** `TestKatexIsolation::test_katex_is_not_installed_over_the_mode_screens`,
  `TestTypographySource::test_no_universal_font_override_in_mode_screens`

### KATEX-1 — Inline wrapper className lost its separator
* **File** `frontend.html` / `renderMath`
* **Observed** `class="katex-lcd-wrapkatex-inline"`.
* **Root cause** the non-display branch omitted the leading space.
* **Fix** `' katex-inline'`.
* **Regression test** `TestKatexIsolation::test_katex_wrapper_classname_has_separated_tokens`

### KATEX-2 — No-KaTeX fallback printed raw LaTeX
* **File** `frontend.html` / `renderMath`
* **Observed** with the CDN unavailable the LCD showed `\sqrt{25}` / `\sum_{1}^{5}`.
* **Fix** `renderMath(latex, id, displayMode, plainFallback)`; all call sites pass
  readable text.
* **Regression test** covered by the same class plus the source-level assertions.

### KATEX-3 — Pressing `=` destroyed the editable input line
* **File** `frontend.html` / `renderLCD`
* **Observed** after `=`, `#lcdExprContent .katex` count was 1, the slot DOM and
  `.lcd-cursor` were gone, and the input line's computed font jumped to
  `KaTeX_Main` while the rest of the LCD stayed ClassWiz.
* **Expected** the ClassWiz keeps the input line as typed; only the result line
  is typeset.
* **Root cause** an unconditional `renderMath(exprToLatex(getExpr()),'lcdExprContent',true)`.
* **Fix** removed; the editable line is always the manual slot DOM.
* **Regression test** `TestKatexIsolation::test_katex_does_not_touch_the_editable_input_line_after_equals`,
  `test_input_line_font_does_not_change_when_a_result_appears`

### FRAC-1 — Exact fractions rendered as inline slashes
* **File** `frontend.html` / `exprToLatex`, `renderMatrixResult`
* **Observed** `1/2` and the `ab/c` form `1 23/45` reached KaTeX verbatim and
  displayed as `1/2`, `1 23/45`.
* **Root cause** no mapping from the exact-answer forms to `\frac`.
* **Fix** anchored mappings in `exprToLatex`; `renderMatrixResult` promotes only
  exact-fraction shapes so engineering notation is not rewritten with `\cdot`.
* **Regression test** `TestFractionsRendered::test_exact_fraction_result_is_typeset_as_a_stacked_fraction`,
  `test_engineering_notation_is_not_corrupted_by_latex_conversion`,
  `TestLatexConversion::test_fractions_become_stacked_latex`

### DDX-1 — SHIFT+∫ produced a raw `d/dx(` text token
* **File** `frontend.html` / `handleKey`, `serializeSlot`, `renderSlotDOM`
* **Observed** rendered DOM `<span class="math-slot">d/dx(2…</span>`; no template,
  no editable slot, unbalanced parenthesis, no way to delete just the operator.
* **Root cause** the branch called `insertToken('d/dx(')`.
* **Fix** new `derivative` template + `insertDerivative()`, rendering
  `math-deriv-diff` / `math-deriv-bar` / `math-deriv-dx` / `math-deriv-body`,
  with cursor, ▲▼/◀▶, delete, undo and serialization wired through the existing
  slot machinery.
* **Regression test** `TestDerivativeTemplate` (6 tests)

### DDX-2 — The derivative body serialized `X`, which the engine rejects
* **File** `frontend.html` / `serializeSlot`
* **Observed** `d/dx` of `X²` serialized to `diff(((X)^(2)),3)`. The backend
  rejects it (`Math ERROR: Unexpected character 'X'`), and in FILE_MODE the
  bridge substituted `X` from the register *before* reducing the special
  function, so it differentiated a constant and **silently returned 0**.
* **Root cause** the calculus engines bind the dummy as lowercase `x`, while the
  `x` key emits the canonical register `X`.
* **Fix** `calculusBody()` maps the standalone token `X`→`x` inside
  diff/sigma/integral bodies only; bounds and the differentiation point keep
  their own meaning. The point comes from the X register via `derivativePoint()`
  in plain positional notation.
* **Regression test** `TestDerivativeTemplate::test_derivative_uses_the_x_register_as_the_differentiation_point`
  (d/dx(X²) = 6/4/0 at X = 3/2/0), `TestIntegralTemplate::test_integral_evaluates`,
  `TestSigmaTemplate::test_summation_evaluates_correctly`

### SIG-1 — SHIFT+x produced a raw `Σ(` text token
* **File** `frontend.html` / `handleKey`, `serializeSlot`, `renderSlotDOM`
* **Observed** `<span class="math-slot">Σ(5…</span>` — no bounds slots, no Σ
  arrangement, unbalanced parenthesis.
* **Fix** new `sigma` template + `insertSigma()`, rendering
  `math-sigma-upper` / `math-sigma-sym` / `math-sigma-lower` /
  `math-sigma-prefix` (`x=`) / `math-sigma-body`, with the full
  lower→upper→body reading order and ▲▼ navigation.
* **Regression test** `TestSigmaTemplate` (5 tests)

### SHIFT-1 — Keycap legends and data attributes were swapped
* **File** `frontend.html` (keypad markup)
* **Observed** the ∫ key printed SHIFT `Σ` and the x key printed SHIFT `d/dx`,
  and carried the same swapped `data-shift` values. `raw/buttons.md` and the real
  fx-991EX both specify `SHIFT+∫ → d/dx` and `SHIFT+x → Σ`; the *routing* was
  right and the *print* was wrong.
* **Fix** corrected both legends and both attributes so legend, attribute and
  routing agree with `raw/buttons.md`.
* **Regression test** `TestShiftLegendParity` (2 tests),
  `TestShiftAlphaBehaviour::test_shift_fraction_is_the_mixed_fraction_template`

### ALPHA-1 — ALPHA on the x key was unmapped
* **File** `frontend.html`
* **Observed** `ALPHA + x` produced `X` (the key had no `data-alpha` and no ALPHA
  branch).
* **Fix** `data-alpha="y"`, `y` legend, and routing that inserts `y` (while
  `ALPHA + )` still inserts `X`, and the plain x key still inserts `X`).
* **Regression test** `TestShiftAlphaBehaviour::test_alpha_on_the_x_key_inserts_y`,
  `test_plain_x_key_still_inserts_the_x_register`,
  `test_alpha_right_paren_still_inserts_x`

### TESTHARNESS-1 — a node stub in an existing test was always truthy
* **File** `test_lowercase_x_variable.py`
* **Observed** `NODE_STUBS` defined `function useAlphaForHex(){return false}`,
  but the real code uses it as a *boolean*. A function object is truthy, so every
  non-ALPHA press was silently routed into the ALPHA branches. It was masked only
  because no ALPHA-mapped key previously sat ahead of the plain branch.
* **Fix** the harness now declares `const useAlphaForHex = false;` per press, and
  stubs `insertSigma`, `insertDerivative`, `insertIntegral`, `insertLog` and
  `nextDmsSymbol` so the sliced router runs to completion.
* **Note** no product code changed for this; it was a latent test defect exposed
  by adding an ALPHA branch.

### LEGEND-2 — keycap/OPTN legends could not draw their own symbols
* **File** `frontend.html` (CSS)
* **Observed** `.math-key`, `.root-sign`, `.int-glyph`, `.pow-glyph`,
  `.xroot-legend` used `"Times New Roman", Cambria, serif`, which has no glyph for
  ∛ ∇ ∈ ∅ ∀ ∃ ∥; `.lbl` and `.menu-overlay` used Arial, which has none for
  U+207B (the `sin⁻¹` / `sinh⁻¹` legends).
* **Fix** those stacks now name `"Cambria Math", "Segoe UI Symbol"` (Arial stays
  first for `.lbl`/`.menu-overlay`, so every ASCII legend is byte-identical and
  only the unrenderable code points change face).

---

## 4. Tests

Exact results, no estimates:

```
pytest (full suite, final):        358 passed, 41 subtests passed in 81.50s
pytest (pre-existing tests only):  308 passed, 41 subtests passed in 18.75s
subtests:                          41 passed
legacy tests:                      308 passed  (unchanged count of pre-existing tests:
                                   4 assertions inside them were updated, see below)
frontend checks (new file):        50 passed in 59.65s
```

`test_frontend_math_io.py` is new (50 tests). It drives the real
`frontend.html` in Chrome and asserts on rendered DOM, computed styles, real key
routing, cursor ownership and evaluated results.

**Proof the new tests are not vacuous** — the same file was run against
`git show HEAD:frontend.html`:

```
29 failed, 21 passed
```

Every one of the 11 recorded bugs is detected by at least one failing test on
the pre-fix code. The 21 that pass on both sides are guards for behaviour that
was already correct (fraction/integral/power/root/log templates, SHIFT indicator
state machine, ASCII typography, structural tests).

### Pre-existing tests updated (not deleted)

Four assertions pinned the defective behaviour and were rewritten to pin the
correct behaviour; no test was removed.

| Test | Was | Now |
|---|---|---|
| `test_state_machine::test_dom_shift_alpha_attributes` | pinned the swapped `data-shift` values | pins `integral → data-shift="Sigma"`, `variable → data-shift="d/dx"` + `data-alpha="y"` |
| `test_state_machine::test_shift_token_branches` | asserted the literal source string `insertToken('d/dx(')` existed | asserts `insertDerivative()` / `insertSigma()` are the routed branches, plus the `sin⁻¹` escape form |
| `test_parity_regressions::test_swapped_mappings_fixed` | asserted `insertToken(isShift ? '\u03a3(' : 'X')` | asserts the template calls and that the raw tokens are **absent** |
| `test_lowercase_x_variable::test_shift_x_key_still_inserts_sigma` | asserted `[["Σ("]]` | asserts `[["<sigma-template>"]]`; new tests for `ALPHA+x → y`, `SHIFT+∫ → derivative`, and a guard that neither key can emit a raw `Σ(`/`d/dx(` |

`test_lowercase_x_variable`'s node harness also had its `useAlphaForHex` stub
corrected (TESTHARNESS-1 above).

---

## 5. Remaining Issues

Genuine, still open. None is listed merely because it differs from an ideal
architecture.

1. **KaTeX is loaded from a CDN.** `katex.min.css`, `katex.min.js` and
   `auto-render.min.js` come from `cdn.jsdelivr.net`. The app is packaged with
   PyInstaller (`MentisClassWiz.spec`, `dist/`) and is expected to run as a local
   desktop emulator, so an offline machine gets no typesetting at all and falls
   back to the plain-text path. Vendoring KaTeX into `ClassWizFontSet/` (or a new
   `vendor/` directory) and serving it locally would remove the dependency. This
   was **not** changed here because it adds ~300 KB of third-party assets and a
   packaging change, which is outside "fix the actual defects" for this pass.

2. **Empty template slots serialize to a placeholder value.** An untouched
   fraction serializes as `((0)/(1))`, a summation as `sigma(0,0,0)`, a
   derivative as `diff(x,0)`. This is pre-existing behaviour that the backend
   evaluates to 0 rather than reporting an incomplete expression; the real
   ClassWiz would refuse to evaluate an unfilled template. It is a *semantics*
   question about the incomplete-input state machine, not a rendering defect, so
   it was left alone.

3. **Trigonometric and hyperbolic functions are still raw text.** `sin(`, `cos(`,
   `tan(`, `ln(`, `10^(`, `e^(`, `Abs(`, `FACT(` and the `sin⁻¹` forms are text
   tokens with unbalanced parentheses, not templates with editable argument
   slots. They now render correctly (`.math-sym` covers `sin⁻¹`), and they
   serialize and evaluate correctly, but they do not yet have the editable-slot
   treatment the fx-991EX gives them. Same for `sinh⁻¹` etc. from the OPTN menu.

4. **`10^` and `e^` share one slot.** On the real device these are superscript
   templates with an editable exponent; here they are text tokens
   (`insertToken('10^(')`), so the exponent cannot be entered as a structured
   slot and the closing parenthesis must be typed.

5. **Statistics and Spreadsheet cells are plain text.** Cells can contain
   `√`, `∫`, `Σ` and are now rendered in a face that has those glyphs, but they
   are not Math I/O templates — matching the real ClassWiz, where those modes are
   grid entry screens rather than Math I/O.

6. **`exprToLatex` is now only reached through the exact-fraction path.** After
   removing the destructive input-line re-typeset, its general input-expression
   role disappeared. It is retained deliberately as the module's documented LaTeX
   conversion helper (mirrored in `raw/code organisation/js.md`) and is covered
   by `TestLatexConversion`. Removing it would be an unrelated refactor.

---

## FINAL STATUS

```
FINAL STATUS:      COMPLETE — all confirmed defects fixed and covered by tests

HEAD:              1195232  audit: fresh functional parity pass
                   (becomes the commit below)

TESTS:             pytest:  358 passed, 41 subtests passed in 81.50s
                   new file: 50 passed in 59.65s
                   pre-fix replay of the new file against HEAD's frontend.html:
                                 29 failed, 21 passed
                   subtests: 41 passed
                   legacy:   308 passed (4 assertions updated, 0 removed)
                   frontend checks: 50 passed (real Chrome, rendered DOM)

CHANGED FILES:     frontend.html                          (source fix)
                   test_frontend_math_io.py               (new, 50 tests)
                   test_lowercase_x_variable.py           (assertions + harness stub)
                   test_parity_regressions.py             (assertions)
                   test_state_machine.py                  (assertions)

REMAINING ISSUES:  6, listed in section 5 — CDN-hosted KaTeX, incomplete-input
                   serialization, non-template function arguments, 10^/e^,
                   grid-mode cells, retained exprToLatex helper.
```