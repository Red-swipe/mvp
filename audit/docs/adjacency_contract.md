# Adjacency contract — DECISION GATE, NOT YET DECIDED

Status: **UNRESOLVED — requires a human product decision.**
Phase C does not change any application behaviour to make these pass.

## The three shapes

| case | expression | `raw/context.md` expects | notes |
|---|---|---|---|
| 37 | `(2)(3)` | 6 | group adjacent to group |
| 24 | `8÷2(2+2)` | 1 | group after an explicit `÷` |
| — | `10%10%` | **Math ERROR** | produced by the postfix-`%` rewrite |

Plus the wider family: `(1+2)(3+4)`→21, `2(3+4)(5−1)`→56,
`(1+2)(3+4)(5+6)`→231, `1+(2(3+4))`→15, `2(3)(4)(5)`→120,
`7+(−3)(−2)`→13, `1(3−1)`→2, `3(−2)`→−6, `2(3+4)`→14.

These are **not separable**. They are one grammar question:

> When a value is immediately followed by a parenthesised group, is that an
> implicit multiplication, and if so, how tightly does it bind against an
> explicit `×` or `÷`?

## The contradictory evidence

The repository currently asserts **two mutually exclusive contracts at once**.
Both are live tests in the current suite.

**Contract A — adjacency is LEGAL, and binds tighter than explicit × ÷.**
Evidence FOR:
- `raw/context.md` section "The 46 case battery" lists `(2)(3)`→6,
  `(1+2)(3+4)`→21, `2(3+4)(5−1)`→56, `(1+2)(3+4)(5+6)`→231,
  `8÷2(2+2)`→1. That is 8 of 46 rows that are only reachable if group-group
  juxtaposition multiplies.
- `raw/context.md:16` (owner decision 2): "`)(` juxtaposition becomes **legal**
  on every path (non-negotiable)."
- The real Casio fx-991EX does evaluate `(1+2)(3+4)` as 21.
- The **uncommitted** `engine/parser.py` change implements exactly this and was
  hand-traced correct in Phase 0: `8/2(2+2)`→1, `2+3*4`→14, `2(3+4)*5`→70,
  `1/3+1/6`→0.5, `2(3+4)^2`→98.

Evidence AGAINST (i.e. for Contract B):
- `engine/parser.py::_implicit_multiply_allowed()` existed in HEAD precisely to
  *reject* group-group adjacency, and `mvp_server.py` still honours it.
- `test_file_mode.py:CASES_ERR` lists `"(2)(3)"` with the comment
  "Group-adjacent-to-group is deliberately NOT juxtaposition: it is the shape
  the postfix-% rewrite produces for `10%10%`, which must stay an error on both
  sides".
- `test_constant_implicit_mult.py::test_group_adjacent_to_group_stays_an_error`
  asserts `(2)(3)` raises.

**Contract B — adjacency is an ERROR, so that `10%10%` can stay one.**

## Why they genuinely conflict

The `%` rewrite (`_transform_percent`) rewrites `10%10%` into the *same string
shape* as `(2)(3)`. There is no syntactic marker left to tell them apart:

- reject group-group adjacency → `(2)(3)` fails, `10%10%` correctly errors.
- allow it → `(2)(3)` gives 6, but `10%10%` **also** stops erroring.

This is not a theoretical worry. The Phase B baseline run observed exactly that
side effect: with the uncommitted parser change in place,
`test_percent_contextual.py::test_trailing_percent_expression` fails with
`ValueError not raised : 10%10%`.

So Contract A additionally requires **fixing `_transform_percent` to emit a
form the parser rejects** (owner decision 2 says exactly this, with a fallback of
documenting the `10%10%` limitation if the fix is too large).

## What each path currently does (Phase C measured, not assumed)

| path | `(2)(3)` | `8/2(2+2)` | `10%10%` |
|---|---|---|---|
| `Engine()` / `safe_eval` / HTTP server | 6 | 1 | no longer errors (parser change) |
| node bridge / Chromium `file://` | Math ERROR | 16 | not measured in Phase C |

The JS evaluator has **no** equivalent of the Python parser change. The two
grammars disagree today regardless of which contract is chosen.

## Options, with consequences

**Option 1 — Contract A everywhere (matches the hardware and owner decision 2).**
- Make group-group adjacency legal and tighter-binding on the JS path too.
- Separately make the `%` rewrite emit a parser-rejected shape so `10%10%` errors.
- Must flip 4 baseline tests: `test_group_adjacent_to_group_stays_an_error`,
  `test_parity_calculate`, and re-verify `test_parity_div_zero`.
- Cost: touching `_transform_percent`, the JS parser, and the tests.

**Option 2 — Contract B everywhere (status quo).**
- Revert/discard the uncommitted `engine/parser.py` change.
- `(1+2)(3+4)` stays Math ERROR on every path, i.e. the calculator remains wrong
  relative to the physical device and relative to 8 of its own 46 expected rows.
- Cost: zero code change, but the product knowingly miscomputes.

**Option 3 — split by shape.**
- Allow `digit(group)` and `(expr)(expr)` but reject `(group)(group)`.
- Fails immediately: `(1+2)(3+4)` and `(2)(3)` are both group-group.
- Not viable.

**Option 4 — leave it broken and document it.**
- Keeps all current tests green except the 4 already failing.
- The battery rows 9, 44, 8, 24, 37, 38 stay permanently failing on the
  browser path and the row-24 value stays wrong on the browser path.
- Only honest if the teacher never enters a parenthesised expression.

## Recommendation (advisory only — the owner decides)

**Option 1**, because the expected values in the project's own 46-case source
document require it and the physical device does it. It is also the only option
that makes the JS and Python paths agree.

However: **Phase C does not implement it.** The `%`-rewrite fix is a behaviour
change to `mvp_server.py` and `frontend.html`, which this phase is forbidden to
touch, and it needs its own reviewed commit.

## Until this is decided

The comparator marks:

- `(2)(3)`, `8÷2(2+2)` and the other adjacency rows **unresolved**, because the
  repository holds two contradictory assertions and no ratified decision.
  `run_comparator.py` reads the adjudicated value from `audit/data/cases.json`
  and flags the whole family when the gate is open.
- `10%10%` is **not** in the 46-case battery (`raw/context.md` contains no such
  row). It is covered separately by the existing
  `test_percent_contextual.py` and by this document.

## To close the gate

1. Owner picks Option 1, 2 or 4.
2. Write the choice here with a date and the reasoning.
3. Update `audit/data/cases.json` `_meta.adjacency_decision`.
4. Flip or keep the 4 contradicting tests deliberately — never silently.
5. Re-run the comparator; expect rows 9, 24, 37, 38, 43, 44 to move.