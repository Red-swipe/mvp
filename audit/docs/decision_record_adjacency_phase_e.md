# Gate A — adjacency and precedence: EVIDENCE UPDATE (Phase E)

Status: **STILL BLOCKED FOR HUMAN DECISION — but the evidence base has changed
materially.** A complete implementation of one option already exists, committed
and pushed. It has **not** been ratified by the owner, and Phase E does not
adopt it.

Supersedes nothing: `decision_record_adjacency.md` (Phase D, `95d9e56`) remains
the option analysis. This file records what Stage 1 found.

## The material discovery

Phase A–D recorded `origin/release_fix_v0_1_1-9849905938563262561` as an
unexamined remote-tracking ref. Phase E inspected it. It is **not** a stray
artefact. It is Jules's completed audit work:

```
e6a5584  fix: comprehensive bug audit and fixes ...   Author: google-labs-jules[bot]
5604549  fix: comprehensive bug audit and fixes ...   Author: google-labs-jules[bot]
         Co-authored-by: Red-swipe <129591465+red-swipe@users.noreply.github.com>
48d9286  (origin/main) Release readiness ... (#5)
```

merge-base with the local branch: `afd619e`. Divergence: **3 behind / 12 ahead**.

### What those commits claim to decide

From the `5604549` / `e6a5584` commit messages, verbatim:

- "Fixed adjacent bracket groups (1+2)(3+4) in parser and evaluator."
- "Fixed implicit multiplication precedence over explicit \* and / (e.g. 8÷2(2+2) = 1)."
- "Replaced legacy \"To infinity and beyonddd\" with \"Math ERROR\" across
  frontend, server, and test suite."

### Does it cover every contested case?

| contested case | covered by the remote work? | evidence |
|---|---|---|
| `(2)(3)` | **yes** → 6 | remote `test_expression_battery.py:37` |
| `(1+2)(3+4)` | **yes** → 21 | remote battery case 9 |
| `2(3+4)(5−1)` | **yes** → 56 | remote battery case 8 |
| `8÷2(2+2)` | **yes** → 1 | remote battery case 24 |
| `10%10%` | **yes** → raises `ValueError('Math ERROR')` | `_transform_percent` guard added in `5604549` |

The `10%10%` guard is the piece Phase D identified as **required** for Option 1
to be viable at all. Phase D wrote: "Contract A additionally requires making
`_transform_percent` emit a form the parser rejects". The remote does exactly
that, via an explicit rejection:

```python
+    if re.search(r'%\s*%', s) or re.search(r'%\s*\d+(?:\.\d+)?\s*%', s):
+        raise ValueError('Math ERROR')
```

So the remote work is a coherent, complete implementation of **Gate A Option 1**,
and it also settles **Gate B** toward `Math ERROR` — the answer
`raw/context.md` already gave.

The parser change is structurally the same idea as the pre-existing uncommitted
`engine/parser.py` edit on this branch (`_term` split so juxtaposition binds
tighter than explicit `×`/`÷`), though written as a separate `_implicit_term`
helper rather than an inline loop.

## Why Gate A remains BLOCKED anyway

**1. There is no owner decision record.** The commits are authored by
`google-labs-jules[bot]`. A `Co-authored-by: Red-swipe` trailer records
co-authorship of the *code*, not an explicit selection of a product contract.
Phase D's gate asks a product question; a bot implementing one option is not the
owner answering it. Phase E will not treat an implementation as a ratification.

**2. The local branch does not contain it, and the histories are diverged.**
Adopting it would require a merge or a rebase. Both are prohibited while
divergent, and Phase E is not authorised to reconcile them.

**3. It conflicts with four currently-failing tests on this branch.** Those
tests encode the *opposite* contract. Adopting Option 1 means flipping them
deliberately, in its own commit, with owner sign-off.

**4. It only tests the Python path.** Every assertion in the remote battery
calls `mvp_server.safe_evaluate_expression`. **No remote test exercises the
JavaScript evaluator or the browser keypad.** The defects Phase D measured as
browser-specific — `(1+2)(3+4)` → `Math ERROR`, `8÷2(2+2)` → 16 — are precisely
in the untested path. Adopting the remote work would therefore leave the
teacher-facing failure mode unverified.

**5. Its case 35 is the version `raw/context.md:239` already discredited.**
The remote test does:

```python
r1 = mvp_server.safe_evaluate_expression("5+5")
r2 = mvp_server.safe_evaluate_expression(f"({r1})*2")
```

That is `(10.0)*2`, not Ans chaining — the exact shortcut Phase D's
`ans_sequences.py` replaced with real keypad sequences. Ans chaining across the
real interface remains unverified even on the remote branch.

## Options as they now stand

**Option 1 — adopt the existing remote implementation.**
- Lowest-risk path to the intended behaviour: it is already written, tested on
  Python, and co-signed.
- Cost: reconcile the divergence; flip the 4 contradicting tests deliberately;
  **extend its coverage to the JavaScript and browser paths, which it entirely
  lacks**; verify the shipped package is rebuilt from it.
- Requires owner authorisation to merge.

**Option 2 — implement Option 1 on this branch instead.**
- The PHP-side work already exists here: the uncommitted `engine/parser.py`
  change plus Phase D's `_extractPowerBaseItems`.
- Cost: write the JS-side parity change and the `_transform_percent` guard
  here; more work, but it lands on a branch that already has the browser
  comparator, the keypad inventory and the Ans instrumentation that would prove
  it.

**Option 3 — leave Gate A blocked.** Release cannot proceed: the browser keeps
returning `Math ERROR` for `(1+2)(3+4)` and the wrong value `16` for
`8÷2(2+2)`.

## The decision the owner must still make

One question, four words of answer:

> **Should adjacent bracket groups multiply (Option 1), or stay an error?**

Everything else follows. Specifically, the owner must also say whether to:

- **ratify** the existing remote implementation (authorising a merge of the
  diverged history), or
- **re-implement** Option 1 on this branch, or
- **retain** the current error behaviour.

Phase E recommends **ratify-then-extend**: the parser work exists and is correct
in outline; the missing part is browser coverage, which this branch's
instrumentation is built to supply. But the merge itself is the owner's call.

## What Phase E did NOT do

- Did not merge, rebase or cherry-pick the remote work.
- Did not change any adjacency or precedence semantics.
- Did not modify the four failing tests.