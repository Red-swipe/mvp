# Decision record B — calculation error contract

Status: **PARTIALLY BLOCKED FOR HUMAN DECISION.** One part is settled by
evidence; the rest is not. Nothing in this phase changes error behaviour.

Date raised: 2026-10-15 · Raised by: Phase D commit `d04aad0`
Decision owner: **unassigned — requires the product owner**

## Questions to be answered

1. Is a given failure a *calculation* error or a *system* error?
2. What does the LCD show after division by zero?
3. What HTTP status and response body does the server return?
4. Is `Ans` preserved, cleared, or updated after an error?
5. Do subsequent calculations work, and do they start clean?

## SETTLED BY EVIDENCE — Q1

**A division by zero is a calculation error, never a system error.**

| path | observation |
|---|---|
| `Engine().evaluate` | raises `ZeroDivisionError` |
| `safe_evaluate_expression` | raises `ZeroDivisionError` |
| `POST /api/key` | HTTP 400, body `error = "To infinity and beyonddd"` |
| node bridge | throws `DIV_ZERO` |
| Chromium `file://` | LCD `Math ERROR` |

Every path raises or reports a division-specific condition. None falls through
to an internal-failure branch. `raw/context.md:351` also states the rule:
`System ERROR` is reserved for non-maths failures (network, missing asset,
internal bug).

**Corollary:** `System ERROR` must never be displayed for `1÷0` on any path.

## BLOCKED — Q2 and Q3: the displayed string and the HTTP status

Two incompatible requirements exist in the repository:

| source | requires |
|---|---|
| `raw/context.md` 46-case battery, row 31 | `Math ERROR` |
| `mvp_server.py:129` | `DIV_ZERO_MSG = "To infinity and beyonddd"` |
| `frontend.html:7417` | `const DIV_ZERO_MSG = 'To infinity and beyonddd'` |
| `test_file_mode.py:284,309-314` | both paths show `To infinity and beyonddd` |
| `raw/september_handover.md:1403` | deliberate fx-991EX fidelity, shown as a *result*, `Ans` preserved |

The string is not an accident. The September handover records it as an
intentional fidelity feature matching the fx-991EX, where `1÷0` displays
`To infinity and beyonddd` as a **value** and leaves `Ans` untouched.

**These cannot all hold, and the repository does not say which wins.** The
audit does not guess. The comparator currently accepts any of
`{To infinity and beyonddd, Math ERROR, System ERROR, DIV_ZERO, Division
ERROR}` for case 31 and records the observed string verbatim, so the divergence
stays visible instead of being normalised away.

**Q3 is separately unresolved.** The handover intends a *result* (implying
HTTP 200). The server implements an *error* (HTTP 400). Both exist today.

## MEASURED — Q4: `Ans` is preserved on BOTH paths

This corrects the Phase C report, which listed the question as untested and
speculated about divergence.

Observed by `audit/tools/ans_sequences.py` (commit `d04aad0`):

```
browser: 10 -> 1/0 (Math ERROR) -> Ans+1 = 11     localAns stays 10
server:  10 -> 1/0 (HTTP 400)    -> Ans   = 10     ans preserved
```

**`Ans` itself is correct on both paths.** It is preserved through a
divide-by-zero on both. No defect here.

## DEFECT FOUND — Q5: the server does not start clean after an error

While measuring Q4, a real defect surfaced. It is **not** `Ans` corruption.

After `1÷0`, the server leaves the failed expression in the input buffer:

```
key '1'      -> expression "1"
key 'divide' -> expression "1/"
key '0'      -> expression "1/0"
key 'equals' -> 400, error, state ERROR, expression STILL "1/0"
key 'ans'    -> expression "1/010"     <-- appended to the stale buffer
key 'plus'   -> expression "1/010+"
key '1'      -> expression "1/010+1"
key 'equals' -> result "1.1"          <-- not 11
```

The browser clears the buffer and starts clean: `Ans+1` → **11**.

So the divergence Phase C sensed is real, but its cause is different:

> **The server carries a failed calculation's text into the next calculation.**
> The next answer silently includes the previous failed expression. `10`, then
> `1÷0`, then `Ans+1`, yields **1.1** instead of **11** — a wrong number with no
> error shown.

This is more serious than the string disagreement: it silently returns a wrong
answer.

### Why Phase D did not fix it

Fixing it means deciding Q5: should the buffer clear after an error? The
browser says yes, which is the strong product signal, but:

- `AUDIT_PROGRESS.md:19` records owner decision 3 as "`_state()` must never
  return a stale `result` on an error branch (+ test)" — that is about the
  `result` field, **not** the expression buffer, and was never implemented.
- Q2/Q3 are still blocked, and the clearing behaviour interacts with them: if
  `1÷0` is eventually shown as a *result* (September handover), the buffer
  should perhaps be retained for display.

Fixing this before Q2/Q3 are decided risks having to undo it. **Recorded as
evidence; not fixed.**

## Test coverage added without inventing an expected answer

`test_ans_sequences.py` asserts only what is observable and uncontroversial:

- `Ans` is preserved through a divide-by-zero on both paths (measured, and it
  is what `raw/september_handover.md:1403` states is required).
- The two paths **do** diverge on the next calculation — asserting the
  divergence exists, not which side is right.
- The server's stale buffer is visible in the recorded evidence
  (`expression == "1/010+1"`), so the cause is pinned to the data.
- Blocked sequences carry **no** expected answer. A test enforces this, and it
  caught a real inconsistency in my own data (`usable_after_divzero` was marked
  blocked while still stating `4`).

## Recommended contract (advisory — the owner decides)

If the physical-device fidelity argument holds, the coherent contract is:

| question | answer |
|---|---|
| Q1 classification | always a calculation error; never `System ERROR` |
| Q2 LCD text | `To infinity and beyonddd` on every path, matching the fx-991EX |
| Q3 HTTP | **200**, treated as a displayed value, not a transport failure |
| Q4 `Ans` | preserved (already true on both paths — no change needed) |
| Q5 recovery | clear the input buffer after any error; the next input starts fresh |

Under that contract the server's stale buffer is unambiguously a bug and Q5 has
one correct answer on both paths.

If the fx-991EX string is instead judged a mistake, the alternative is a real
maths error string everywhere, and `raw/context.md` row 31 already says which:
`Math ERROR`.

Either way **Q5 must clear the buffer.** That much does not depend on how Q2
and Q3 are decided.

## To close this gate

1. Owner answers Q2 and Q3.
2. Record the answers with a date and reasoning in this file.
3. Update `audit/data/cases.json` → `_meta.divzero_decision`.
4. Fix Q5 (clear the buffer) — justified under either answer.
5. Align `mvp_server.py`, `frontend.html`, `test_file_mode.py:284` and
   `raw/september_handover.md` with the ratified strings, in one deliberate
   commit.
6. Re-run the comparator; case 31 and the Ans sequences should agree across
   paths.