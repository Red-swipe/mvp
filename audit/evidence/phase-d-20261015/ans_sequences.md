# Stateful Ans sequences

Each step records the expression, getExpr(), LCD, appState and Ans.
`contract` states whether the expectation is settled; sequences whose
contract is blocked are reported as observations, NOT scored.

## ans_basic - harmless known sequence: 5, then Ans+2

contract: `approved_by_source`

| # | step | getExpr | LCD | result | error | Ans |
|---|---|---|---|---|---|---|
| 1 | compute 5 | `5` | D Math □ 5 5 5 | 5 | None | 5 |
| 2 | Ans+2 -- 7 if Ans is still 5 | `Ans+2` | D Math □ Ans+2 7 7 | 7 | None | 7 |

expected_final=7  observed_final=7  observed_ans=7

## ans_chain - Ans chaining as battery case 35 intends

contract: `contested_by_raw_context_239`

> EXPECTATION UNRESOLVED. The arithmetic is unambiguous (10*2=20) but no keypad sequence in this repository is documented to produce it, and the battery row is contested. Observed behaviour is recorded without being scored.

| # | step | getExpr | LCD | result | error | Ans |
|---|---|---|---|---|---|---|
| 1 | compute 10 | `5+5` | D Math □ 5+5 10 10 | 10 | None | 10 |
| 2 | Ans should be 10, so 20 | `Ans*2` | D Math □ Ans × 2 20 20 | 20 | None | 20 |

expected_final=None  observed_final=20  observed_ans=20

## divzero_then_ans - divide by zero, then use Ans

contract: `BLOCKED_BY_GATE_B`

> EXPECTATION UNRESOLVED by Gate B. Recorded as an observation.

| # | step | getExpr | LCD | result | error | Ans |
|---|---|---|---|---|---|---|
| 1 | compute 10 | `10` | D Math □ 10 10 10 | 10 | None | 10 |
| 2 | divide by zero | `1/0` | D Math □ 1 ÷ 0 𝑀 𝑎 𝑡 ℎ 𝐸 𝑅 𝑅 𝑂 𝑅 MathERROR | Math ERROR | None | 10 |
| 3 | observe Ans | `1/0` | D Math □ 1 ÷ 0 𝑀 𝑎 𝑡 ℎ 𝐸 𝑅 𝑅 𝑂 𝑅 MathERROR | Math ERROR | None | 10 |
| 4 | Ans+1 -- 11 if Ans was preserved, something else if not | `Ans+1` | D Math □ Ans+1 11 11 | 11 | None | 11 |

expected_final=None  observed_final=11  observed_ans=11

## usable_after_divzero - is the calculator still usable after a divide by zero

contract: `BLOCKED_BY_GATE_B`

> EXPECTATION UNRESOLVED by Gate B, even though the arithmetic (2+2=4) is uncontroversial. The unresolved part is whether the next calculation SHOULD start clean after an error, which is precisely what the divzero_then_ans sequence shows the server failing to do. Recording the observation without scoring it.

| # | step | getExpr | LCD | result | error | Ans |
|---|---|---|---|---|---|---|
| 1 | divide by zero | `1/0` | D Math □ 1 ÷ 0 𝑀 𝑎 𝑡 ℎ 𝐸 𝑅 𝑅 𝑂 𝑅 MathERROR | Math ERROR | None | 0 |
| 2 | 2+2 must work if the calculator recovered | `2+2` | D Math □ 2+2 4 4 | 4 | None | 4 |

expected_final=None  observed_final=4  observed_ans=4

## Cross-path comparison

Tests the Phase C claim that Ans handling diverges between paths.

| sequence | contract | browser final | server final | agree | browser Ans | server Ans | Ans agree |
|---|---|---|---|---|---|---|---|
| ans_basic | approved_by_source | 7 | 7 | True | 7 | 7 | True |
| ans_chain | contested_by_raw_context_239 | 20 | 20 | True | 20 | 20 | True |
| divzero_then_ans | BLOCKED_BY_GATE_B | 11 | 11 | True | 11 | 11 | True |
| usable_after_divzero | BLOCKED_BY_GATE_B | 4 | 4 | True | 4 | 4 | True |

