# Decision record A — implicit multiplication and precedence

Status: **BLOCKED FOR HUMAN DECISION.** Not approved. Nothing in this phase
changes adjacency or precedence semantics.

Date raised: 2026-10-15 · Raised by: Phase D commit `acc304d`
Decision owner: **unassigned — requires the product owner**

## Scope

Five behaviours that are all one grammar question:

| case | expression | expected | source |
|---|---|---|---|
| 37 | `(2)(3)` | 6 | `raw/context.md` 46-case battery |
| 9 | `(1+2)(3+4)` | 21 | same |
| 8 | `2(3+4)(5−1)` | 56 | same |
| 24 | `8÷2(2+2)` | 1 | same |
| — | `10%10%` | **error** | `test_percent_contextual.py` |

The question: **when a value is immediately followed by a parenthesised group,
is that an implicit multiplication, and how tightly does it bind against an
explicit `×` or `÷`?**

## What the repository asserts today — and it contradicts itself

Two mutually exclusive contracts are enforced by **live tests at the same
time**. Both pass-through today only because the second one is already broken
by uncommitted work.

### Contract A — adjacency is LEGAL and binds tighter than explicit × ÷

- 8 of the 46 battery rows are unreachable without it: cases 7, 8, 9, 24, 36,
  37, 38, 44.
- Owner decision 2 (`AUDIT_PROGRESS.md:16`): "`)(` juxtaposition becomes
  **legal** on every path (non-negotiable)."
- The physical device (fx-991EX) evaluates `(1+2)(3+4)` as 21.
- The **uncommitted** `engine/parser.py` change implements exactly this. Phase 0
  hand-traced it: `8/2(2+2)`→1, `2+3*4`→14, `2(3+4)*5`→70, `1/3+1/6`→0.5.

### Contract B — adjacency is an ERROR

- `engine/parser.py::_implicit_multiply_allowed()` exists in HEAD precisely to
  reject group-group adjacency.
- `test_file_mode.py:CASES_ERR` lists `"(2)(3)"`.
- `test_constant_implicit_mult.py::test_group_adjacent_to_group_stays_an_error`
  asserts it raises.
- `mvp_server.py` still honours this.

## Why they cannot both hold

The postfix-`%` rewrite (`_transform_percent`) rewrites `10%10%` into the
**same string shape** as `(2)(3)`. No syntactic marker survives to distinguish
them.

This is not theoretical. Phase B observed the exact side effect with the parser
change applied:

```
test_percent_contextual.py::test_trailing_percent_expression
E   AssertionError: ValueError not raised : 10%10%
```

So Contract A additionally requires making `_transform_percent` emit a form the
parser rejects — which owner decision 2 already anticipates, with an explicit
fallback of documenting the `10%10%` limitation if that fix is too large.

## Measured current behaviour (Phase D, `acc304d`)

| path | `(2)(3)` | `(1+2)(3+4)` | `2(3+4)(5−1)` | `8÷2(2+2)` |
|---|---|---|---|---|
| `Engine()` | 6 | 21 | 56 | **1** |
| `safe_evaluate_expression` | 6 | 21 | 56 | **1** |
| `POST /api/key` | 6 | 21 | 56 | **1** |
| node bridge `localEvaluate` | `Math ERROR` | `Math ERROR` | `Math ERROR` | **16** |
| Chromium `file://` | `Math ERROR` | `Math ERROR` | `Math ERROR` | **16** |

The Python side already implements Contract A. The JavaScript side implements
nothing — so the two disagree today **regardless of which contract wins**. Note
`8÷2(2+2)` is not merely an error on the browser: it returns a **wrong number**,
16 instead of 1, which is the more dangerous failure mode.

## Options and consequences

**Option 1 — Contract A everywhere.** Make group adjacency legal and
tighter-binding in JS to match Python; separately make `_transform_percent`
emit a parser-rejected shape.
- Fixes 7 failing battery rows (8, 9, 24, 33, 37, 38, 44) and the wrong value
  on row 24.
- Requires touching `_transform_percent`, the JS parser, and flipping 3 tests
  deliberately.
- Risk: the `%` fix could mask legitimate input. `10%` and `10%10%` must be
  distinguished without new syntax.

**Option 2 — Contract B everywhere.** Discard the uncommitted parser change.
- Zero code change; all current tests except `test_parity_div_zero` go green.
- The calculator knowingly miscomputes 8 of its own 46 expected rows and
  disagrees with the physical device.
- Row 24 still returns a wrong number on the browser.

**Option 3 — split by shape** (allow `digit(group)`, reject `(group)(group)`).
- Not viable: cases 9, 37 and 44 are all group-group.

**Option 4 — leave it, document it.**
- Rows 8, 9, 24, 33, 37, 38, 44 stay permanently failing in the matrix and the
  matrix becomes a permanent FAIL column.
- Only honest if the teacher never enters a parenthesised expression, which is
  not something the audit can establish.

## Recommendation (advisory — the owner decides)

**Option 1.** It is the only option consistent with the project's own 46-case
expectations, with the physical device, and with owner decision 2. It is also
the only option that makes the JS and Python grammars agree.

## Why Phase D did not act

Stage 3 permits a fix only when the intended behaviour is established. Here the
repository holds two contradictory live assertions and no ratified decision.
Choosing either would be inventing a product decision, and Option 1 in
particular changes error behaviour for `10%10%` — a contract the owner has
already flagged as needing its own decision.

## To close this gate

1. Owner selects Option 1, 2 or 4.
2. Record the choice, the date and the reasoning in this file.
3. Update `audit/data/cases.json` → `_meta.adjacency_decision`
   (`status`, `decided_on`, `decided_by`, `rationale`).
4. Flip or keep `test_constant_implicit_mult.py`,
   `test_file_mode.py::test_parity_calculate` and
   `test_percent_contextual.py` **deliberately, in their own commit**.
5. Re-run `audit/tools/run_comparator.py`. Rows 8, 9, 24, 33, 37, 38, 44
   should move from FAIL to PASS on the browser and bridge paths. If they do
   not, the fix is wrong.