# Comparator architecture

Every interface below was verified against the source before being used.
Line numbers are from `release_fix_v0_1_1` @ `a65d1f9` plus the uncommitted
`engine/parser.py` change.

## Input format: the internal template string

All five collectors receive `internal_expr`, not the ASCII the teacher types.
This is the string the keypad actually builds, and the string
`POST /api/key {"expression": ...}` expects.

Evidence: driving the real keypad and reading `getExpr()`
(`audit/evidence/phase-c-20261015/internal_expr_from_keypad.json`) shows e.g.
the `×` key emits `*`, `÷` emits `/`, `x^[` emits `((b)^(  ))`, and `√` emits
`sqrt(  )`. The ASCII column in `cases.json` is the human-facing form from
`raw/context.md` and is never sent to anything.

Each case records `internal_expr_source`:

- `keypad-verified` (30 cases) — read from `getExpr()` on the live page.
- `harness-derived` (15 cases) — no keypad sequence exists in
  `probe_path_a.CASES`; syntax taken from `test_file_mode.CASES_OK`, a list the
  engine demonstrably accepts. **Not** keypad-verified.
- `unresolved` (case 35) — a two-step Ans-chaining scenario, not a single
  expression.

---

## Collector 1 — `engine`

- **Invocation:** `engine.engine.Engine().evaluate(text) -> float`
- **Verified at:** `engine/engine.py:107`
- **Input:** raw core syntax only. It does **not** accept template strings such
  as `((-2)^(2))`, `sqrt(16)` or `100(1.05^2)`; those raise `TokenizerError`.
  This is a property of the entry point, not a product defect — Phase B briefly
  misread it as one.
- **Output:** a float. Exceptions: `ZeroDivisionError`, `TokenizerError`,
  `ParseError`.
- **Limitation:** not the right entry point for anything the keypad produces.
  Retained because it isolates the parser/evaluator core from all
  preprocessing.

## Collector 2 — `safe_eval`

- **Invocation:** `mvp_server.safe_evaluate_expression(expr_str, ans_val=0.0,
  angle_unit="Degree", variables=None, complex_mode=False, rnd_setting=None)`
- **Verified at:** `mvp_server.py:1224`
- **Input:** the preprocessed expression. Handles `^`, `sqrt`, `pi`, `sin`,
  `log`, `!` and the rest.
- **Output:** a float, or an exception.
- **Limitation:** defaults matter. The comparator uses the defaults, so
  `Ans = 0`, angle `Degree`, real (not complex) mode. Case 35 (Ans chaining)
  cannot be expressed because it needs a non-default `ans_val` and a second
  call.

## Collector 3 — `node_bridge`

- **Invocation:** extract `frontend.html` between
  `// ── LOCAL EVALUATION BRIDGE` (`frontend.html:3144`) and
  `// ── END LOCAL EVALUATION BRIDGE ──` (`frontend.html:4231`), prepend a stub
  `window`/`appState`, append a loop calling `localEvaluate(c)`, run under
  `node`.
- **Verified against:** `test_file_mode.py:176` `run_bridge()`, which the
  existing suite already uses. The comparator uses the same markers, the same
  `appState` shape, and calls the same `localEvaluate`.
- **Input:** the internal template string.
- **Output:** the JS value string, or the thrown `e.message`.
- **Limitation:** `window.location.protocol` is stubbed as `file:`, so the
  bridge believes it is in FILE_MODE. That is the intent, but it means the node
  path does not exercise fetch/network code paths. It is **not** a browser: no
  DOM, no layout, no real network.
- **Known behaviour:** the frontend collapses most internal failures into the
  single string `Math ERROR` (`frontend.html:5034`). The comparator therefore
  classifies a thrown `Math ERROR` as `system`, not `calculator`, because the
  string carries no information about which layer failed. This is a direct
  consequence of the `a65d1f9` revert and is itself worth reporting.

## Collector 4 — `http`

- **Invocation:** spawn `python mvp_server.py --port N --no-browser`, poll
  `GET /health` until HTTP 200, then `POST /api/reset` and
  `POST /api/key {"key":"equals","expression":expr}`.
- **Verified at:** `mvp_server.py:3771` dispatch (`path == "/api/key"` →
  `CONTROLLER.press_key(payload)`); schema table `mvp_server.py:3610`;
  the same fixture already exists at `test_file_mode.py:63`.
- **Input:** the internal template string.
- **Output:** `{"display":..., "result":..., "error":..., "state":...}` plus the
  HTTP status.
- **Limitation:** one long-lived server shared by all cases, so controller state
  (variables, matrices, statistics, `Ans`) can leak between cases. The comparator
  calls `/api/reset {"target":"all"}` before every case, which is what
  `test_parity_calculate` does. Case 35 still cannot be expressed this way,
  because it needs two deliberate `=` presses with no reset between them.

## Collector 5 — `browser_file`

- **Invocation:** launch the system chromium
  (`ms-playwright\chromium-1228\chrome-win64\chrome.exe`, headless), open
  `file:///<repo>/frontend.html`, then click real `[data-key="..."]` elements.
- **Verified:** `probe_path_a.py` already drives this page this way and the
  Phase B runs completed with zero missing keys.
- **Input:** a real key sequence, read from `cases.json`
  `keypad_sequences`, copied from `probe_path_a.CASES`.
- **Output — two values per case, both mandatory:**
  1. `getExpr()` read from the page **before** evaluating. Verified to exist:
     `const getExpr = () => serializeSlot(rootSlot);` at `frontend.html:3005`.
  2. `.lcd` inner text after the `=` click.
- **Input-construction rule:** if `getExpr()` does not equal the case's
  `internal_expr`, the case is reported as `input_construction_failure` /
  `status: unexecuted`. It is **never** reported as an evaluator defect. This
  rule already fires on two cases (see below).
- **Limitation:** chromium only. Firefox and WebKit are not installed and are
  not run. Headless, so no visual confirmation.

### Two cases are already proven input-construction failures

Read from `getExpr()` on the live page:

| case | declared internal | actual `getExpr()` |
|---|---|---|
| 16 | `((-2)^(2))` | `(-2(())^(2))` |
| 45 | `2(3+4)^2` | `2(3+4(())^(2))` |

Both are the `power` key mis-wrapping a preceding group. The server evaluates
`((-2)^(2))` to 4 and `2(3+4)^2` to 98 correctly, so the maths is right and the
keypad is wrong. This is a **UI defect**, not a parser defect, and it is why
Phase C records `getExpr()` alongside the LCD.

---

## Comparison rules

`parse_num` and `close_enough` are **copied verbatim** from `test_file_mode.py`
into `audit/tools/collectors.py` (attribution in the source) so the comparator
canonicalises exactly like the existing suite. Tolerance `1e-6`, matching
`test_file_mode.close_enough`'s default.

`parse_num` raises `ValueError` on anything it cannot canonicalise. It is
**never** coerced to zero. An unparseable output becomes verdict `unparseable`,
which is distinct from `pass` and from `fail`.

Verdicts emitted per cell:

| verdict | meaning |
|---|---|
| `pass` | matches the declared expectation (numeric, or error-raised-as-contracted) |
| `fail` | contradicts the expectation |
| `unresolved` | the case's expectation is itself unresolved |
| `input_construction_failure` | the keypad built a different expression; nothing evaluated |
| `unparseable` | output did not canonicalise |
| `collector_error` | the collector failed — infrastructure, not calculator |
| `unexecuted` | no observation available |

## Isolation

Each collector is invoked inside its own `try`. A collector that raises is
recorded as `collector_error` for every case rather than aborting the run, so
one broken path cannot hide the results of another. The browser collector
additionally guards each case individually.

## Outputs

- `comparator_results.json` — raw observations and verdicts, nothing discarded.
- `divergence_matrix.md` — 46 rows x 5 collectors.
- `divergence_matrix.csv` — same, machine-readable, includes the `why` for
  every cell.