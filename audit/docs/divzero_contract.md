# Divide-by-zero contract — DECISION GATE

Status: **PARTIALLY UNRESOLVED.** The *classification* of divide-by-zero is
settled by source evidence; the *displayed string* is contradicted by the
project's own documents. Phase C changes no application behaviour.

Battery case affected: **31**, `(5+3)/(2−2)`.

## What the source actually says

| evidence | says |
|---|---|
| `raw/context.md` 46-case table, row 31 | `Math ERROR (genuine, must still show)` |
| `mvp_server.py:129` | `DIV_ZERO_MSG = "To infinity and beyonddd"` |
| `frontend.html:7417` | `const DIV_ZERO_MSG = 'To infinity and beyonddd';` |
| `frontend.html:7154` | the string is still in the sentinel guard list |
| `test_file_mode.py:284` | `DIV_ZERO = "To infinity and beyonddd"` |
| `test_file_mode.py:309-314` | asserts **both** paths show `"To infinity and beyonddd"` |
| `raw/september_handover.md:1403` | documents it as *deliberate*: "Matches fx-991EX", shown as the **result**, not an error, and `Ans` is preserved |
| `mvp_server.py` (HTTP) | division by zero returns **HTTP 400** with `{"error": "To infinity and beyonddd", "display": "To infinity and beyonddd"}` |

The string is not a joke left in by accident. `raw/september_handover.md` records
it as an intentional fidelity feature matching the fx-991EX, where `1÷0` displays
`To infinity and beyonddd` as a *value* and leaves `Ans` untouched.

## What Phase C measured

| path | response | classification |
|---|---|---|
| `Engine()` | raises `ZeroDivisionError` | genuine calculator error |
| `safe_evaluate_expression()` | raises `ZeroDivisionError` | genuine calculator error |
| `Engine()` via `POST /api/key` | **HTTP 400**, `display = "To infinity and beyonddd"`, `error = "To infinity and beyonddd"` | genuine calculator error, surfaced as 400 |
| node bridge `localEvaluate()` | throws `DIV_ZERO` | genuine calculator error |
| Chromium `file://` | LCD shows `Math ERROR` | genuine calculator error, wrong string |

## Settled by evidence

1. Divide-by-zero is a **calculator error**, never a system error. Every path
   raises or reports a division-specific condition, never an internal failure.
   `mvp_server.py` routes it to `DIV_ZERO_MSG`, not to a generic error branch.
2. It must **remain an error** in the sense that `Ans` must not be overwritten
   with a bogus value, and it must not read as a successful number.
3. The Python side raises `ZeroDivisionError`; the browser side catches it.

## UNRESOLVED — the displayed string

Two incompatible requirements:

- `raw/context.md` (the 46-case battery, the document this audit treats as the
  source of expectations) demands **`Math ERROR`**.
- `mvp_server.py`, `frontend.html`, `test_file_mode.py` and the September
  handover all demand **`To infinity and beyonddd`**, documented as deliberate
  fx-991EX fidelity.

These cannot both hold. Phase C does **not** guess. `collectors.py` accepts any
of `{"To infinity and beyonddd", "Math ERROR", "System ERROR", "DIV_ZERO",
"Division ERROR"}` for case 31 and reports the *observed* string verbatim, so the
divergence stays visible instead of being normalised away.

Note that `System ERROR` must **never** be acceptable here. Per
`raw/context.md:351`, `System ERROR` is reserved for non-maths failures
(network, missing asset, internal bug). A stopped server showing `Math ERROR`
was itself listed as a bug. Feeding `System ERROR` into the accepted set is
defensive only, so an unexpected value still surfaces in the matrix.

## Additional unresolved sub-question: result vs error

`raw/september_handover.md:1403` says `1÷0` is shown as the **result** with `Ans`
preserved. `mvp_server.py` returns it in **both** `error` and `display` with
HTTP 400. The frontend revert commit (`a65d1f9`) removed the code that treated
it as a result and now reports `Math ERROR` through `reportEvaluationFailure`.

So three behaviours are in play and only one is implemented consistently:

| path | status | where it lands | Ans |
|---|---|---|---|
| September handover (intended) | result | LCD value | preserved |
| HTTP server (implemented) | **error** | HTTP 400, body `error` | frontend maps to Math ERROR |
| Frontend post-`a65d1f9` | error | LCD `Math ERROR` | lost |

That is a third, independent defect: **`Ans` handling after a divide-by-zero
differs between the server and the browser.** It was not measured in Phase C and
is listed in the report as untested.

## To close the gate

1. Owner decides: is the fx-991EX string a product feature or a bug?
   - **Keep it** → amend `raw/context.md` row 31 to expect
     `To infinity and beyonddd`, and fix the frontend to match the server
     (including preserving `Ans`).
   - **Remove it** → replace `DIV_ZERO_MSG` everywhere with a real maths error
     string, update `test_file_mode.py:284` and `test_parity_div_zero`, and
     update `raw/september_handover.md`.
2. Decide separately whether `1÷0` is a result or an error (HTTP 200 vs 400).
3. Record the decision here with a date, then update
   `audit/data/cases.json` `_meta.divzero_decision`.
4. Add an explicit two-path assertion: one for HTTP status/body, one for the
   browser LCD, both against the ratified string.

Until then case 31 is reported as an observation, not a pass or a fail.