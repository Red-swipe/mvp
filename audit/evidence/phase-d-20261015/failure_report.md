# Non-passing results, grouped by classification

A FAIL is a measured defect. INPUT is a keypad/UI defect.
UNRES is an open question, not a defect. COLL and N/A are gaps in
the audit itself. PARSE means the output could not be canonicalised.

## FAIL (fail) - 1

a real observation contradicts the expectation

- case 31 `(5+3)/(2−2)` on `node_bridge`: expected an error, got 'Math ERROR'

## INPUT (input_construction_failure) - 1

the keypad built a different expression, so the calculator was never asked the question

- case 16 `(−2)^2` on `browser_file`: keypad built '-(((2))^(2))' but the case declares '((-(2))^(2))'; not evaluated as a calculator defect

## N/A (unexecuted) - 25

no observation was produced

- case 13 `2^3` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character '^' at position 4
- case 14 `2^−2` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character '^' at position 4
- case 15 `−2^2` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character '^' at position 5
- case 16 `(−2)^2` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character '^' at position 7
- case 17 `√16` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character 's' at position 0
- case 18 `√(9+16)` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character 's' at position 0
- case 19 `5!` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character '!' at position 1
- case 19 `5!` on `browser_file`: no keypad sequence defined for this case
- case 20 `10÷4` on `browser_file`: no keypad sequence defined for this case
- case 21 `0.1+0.2` on `browser_file`: no keypad sequence defined for this case
- case 22 `100×1.05²` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character '^' at position 11
- case 23 `(3−1)/(9−3)` on `browser_file`: no keypad sequence defined for this case
- case 25 `1/2+1/3` on `browser_file`: no keypad sequence defined for this case
- case 26 `3.5×2` on `browser_file`: no keypad sequence defined for this case
- case 27 `9−3×2+1` on `browser_file`: no keypad sequence defined for this case
- case 28 `sin(30)` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character 's' at position 0
- case 28 `sin(30)` on `browser_file`: no keypad sequence defined for this case
- case 29 `log(100)` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character 'l' at position 0
- case 29 `log(100)` on `browser_file`: no keypad sequence defined for this case
- case 30 `2π` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character 'p' at position 0
- case 30 `2π` on `browser_file`: no keypad sequence defined for this case
- case 32 `99999×99999` on `browser_file`: no keypad sequence defined for this case
- case 33 `7+(−3)(−2)` on `browser_file`: no keypad sequence defined for this case
- case 34 `2×(3+(4−1)×2)` on `browser_file`: no keypad sequence defined for this case
- case 45 `2(3+4)²` on `engine`: Engine.evaluate cannot tokenize template syntax: Unexpected character '^' at position 9

## UNRES (unresolved) - 5

the specification itself is undecided; not a defect

- case 35 `5+5 = then ×2 =` on `engine`: UNRESOLVED. Source document states 20 (Ans chaining), but raw/context.md:239 records that a previous agent's 'case 35' never tested Ans chaining at all and merely evaluated (10.0)*2, and that its PASS/FAIL flipped between reports with no root cause. The stated expectation is therefore CONTESTED, not merely hard to express, so expected is null rather than 20. This case is also structurally two-step (5+5 =, then x2 =) and cannot be expressed as a single expression string for any of the five collectors. Needs a dedicated multi-step collector plus a human decision on what is being asserted. The disputed value 20 is recorded here so it is not lost.
- case 35 `5+5 = then ×2 =` on `safe_eval`: UNRESOLVED. Source document states 20 (Ans chaining), but raw/context.md:239 records that a previous agent's 'case 35' never tested Ans chaining at all and merely evaluated (10.0)*2, and that its PASS/FAIL flipped between reports with no root cause. The stated expectation is therefore CONTESTED, not merely hard to express, so expected is null rather than 20. This case is also structurally two-step (5+5 =, then x2 =) and cannot be expressed as a single expression string for any of the five collectors. Needs a dedicated multi-step collector plus a human decision on what is being asserted. The disputed value 20 is recorded here so it is not lost.
- case 35 `5+5 = then ×2 =` on `node_bridge`: UNRESOLVED. Source document states 20 (Ans chaining), but raw/context.md:239 records that a previous agent's 'case 35' never tested Ans chaining at all and merely evaluated (10.0)*2, and that its PASS/FAIL flipped between reports with no root cause. The stated expectation is therefore CONTESTED, not merely hard to express, so expected is null rather than 20. This case is also structurally two-step (5+5 =, then x2 =) and cannot be expressed as a single expression string for any of the five collectors. Needs a dedicated multi-step collector plus a human decision on what is being asserted. The disputed value 20 is recorded here so it is not lost.
- case 35 `5+5 = then ×2 =` on `http`: UNRESOLVED. Source document states 20 (Ans chaining), but raw/context.md:239 records that a previous agent's 'case 35' never tested Ans chaining at all and merely evaluated (10.0)*2, and that its PASS/FAIL flipped between reports with no root cause. The stated expectation is therefore CONTESTED, not merely hard to express, so expected is null rather than 20. This case is also structurally two-step (5+5 =, then x2 =) and cannot be expressed as a single expression string for any of the five collectors. Needs a dedicated multi-step collector plus a human decision on what is being asserted. The disputed value 20 is recorded here so it is not lost.
- case 35 `5+5 = then ×2 =` on `browser_file`: UNRESOLVED. Source document states 20 (Ans chaining), but raw/context.md:239 records that a previous agent's 'case 35' never tested Ans chaining at all and merely evaluated (10.0)*2, and that its PASS/FAIL flipped between reports with no root cause. The stated expectation is therefore CONTESTED, not merely hard to express, so expected is null rather than 20. This case is also structurally two-step (5+5 =, then x2 =) and cannot be expressed as a single expression string for any of the five collectors. Needs a dedicated multi-step collector plus a human decision on what is being asserted. The disputed value 20 is recorded here so it is not lost.

