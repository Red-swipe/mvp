# Correction: the Phase E square-root finding is RETRACTED

Phase F retested Phase E section 8b and **withdraws** the claim that `√16` is
broken on the teacher-facing path.

| | |
|---|---|
| Phase E claim | "`√16` and `√(9+16)` FAIL with Math ERROR on the SERVER path in BOTH the shipped package and this branch. ... **This is the strongest candidate for the original teacher incident.**" |
| Phase F finding | **The claim is wrong.** The measurement used the wrong surface. |
| Evidence | `audit/evidence/phase-f-20261015/04_e2e_browser_to_server.txt`, `07_shipped_e2e.txt`, `03_keypad_trace.txt` |

## What went wrong

Phase E drove the server directly:

```
POST /api/key {"key":"sqrt"}   ->  expression 'sqrt(16'   ->  Math ERROR
```

That is the server's **own per-key emulation** surface. The calculator's UI
never uses it.

The real path is:

```
browser keypad  ->  getExpr()  ->  POST /api/key {"key":"equals",
                                                   "expression": ...}
```

`frontend.html` documents this explicitly. `syncBackendExpression()` is an
intentional no-op:

> "Intentionally local-only. The backend is a stateless mathematical engine;
> the frontend owns keypress interpretation... evaluation paths always send an
> explicit expression."

## Measured on the real path

| case | local branch | SHIPPED v0.1 | expected |
|---|---|---|---|
| `√16` | **4** | **4** | 4 |
| `√(9+16)` | **5** | **5** | 5 |
| `√(4+√16)` | 2.828427125 | — | (4+4)^½ |
| `2+3` | 5 | 5 | 5 |
| `(2+3)×4` | 20 | 20 | 20 |

The shipped request bodies, captured from the browser itself:

```
{"key":"equals","expression":"sqrt(16)",...}
{"key":"equals","expression":"sqrt(9+16)",...}
```

The keypad serialises a **balanced** radical. The browser evaluator is not
repairing malformed input; it receives the balanced string.

## Why the Phase C comparator also missed it

The comparator's browser collector showed cases 17 and 18 passing because it
submits the *internal* string `sqrt(16)`, which is exactly the balanced form the
keypad produces. So the earlier "these pass" evidence was correct — but for a
different reason than assumed, and it never exercised the server round trip for
those cases.

## What remains genuinely broken

Phase E sections 8a and 8b contained one real finding and one false one.

- **8a (stale buffer) — REAL, and fixed in Phase E** (`9b7084f`). The shipped
  copy still has it: `Ans+1` after `1÷0` returns 1.1, `2+2` after an error
  returns 2.5.
- **8b (sqrt) — FALSE. Withdrawn.**
- **`8÷2(2+2)` = 16 in the shipped package — REAL**, confirmed again on the
  shipped real path. That is Gate A.

## One genuine latent gap, newly found

The server's per-key template emulation is broken generally, not just for sqrt:

| per-key sequence | result |
|---|---|
| `sqrt,1,6,equals` | Math ERROR |
| `sqrt,9,plus,1,6,equals` | Math ERROR |
| `fraction,1,dpad_right,2,equals` | Math ERROR |

Template keys build an unbalanced expression server-side. This is **not
reachable from the UI** and has no user-visible effect. It is recorded in
`test_sqrt_keypad_path.py` as `unittest.expectedFailure`, so that fixing it
produces `unexpectedSuccess` and gets reported instead of being silently
absorbed. Whether to fix it is an owner call; it is not the reported defect.

## Net effect on the teacher-incident hypothesis

Withdrawing 8b removes the strongest candidate identified so far. The
incident remains **unconfirmed**. What is still confirmed broken on the shipped
teacher path is:

1. `Ans+1` after a division by zero returns **1.1** (fixed in Phase E, not in
   the shipped copy).
2. `2+2` after a division by zero returns **2.5** (same fix).
3. `8÷2(2+2)` returns **16** instead of 1 (Gate A).

None of these produces `Math ERROR` on a simple expression. The remaining
explanation for the reported incident is the swallowed-error mechanism
(context repo P6): `frontend.html` reports every failure — network, asset,
internal — as `Math ERROR`, so a *non-maths* failure is indistinguishable from a
maths failure on screen. That is the mechanism Phase A identified and it remains
the most plausible explanation. It is not fixed.