# Divergence matrix

PASS = matches the declared expectation. FAIL = contradicts it.
UNRES = case expectation unresolved. INPUT = keypad built a different
expression than the case declares, so nothing was evaluated.
N/A = no observation. PARSE = output did not canonicalise.
COLL = the collector itself failed (infrastructure, not calculator).

| # | ascii | expected | engine | safe_eval | node_bridge | http | browser_file |
|---|---|---|---|---|---|---|---|
| 1 | `5+−1(3−1)/(9−3)` | 4.666666667 | PASS | PASS | PASS | PASS | PASS |
| 2 | `2+3×4` | 14 | PASS | PASS | PASS | PASS | PASS |
| 3 | `(2+3)×4` | 20 | PASS | PASS | PASS | PASS | PASS |
| 4 | `10−4÷2` | 8 | PASS | PASS | PASS | PASS | PASS |
| 5 | `−5+8` | 3 | PASS | PASS | PASS | PASS | PASS |
| 6 | `7−−3` | 10 | PASS | PASS | PASS | PASS | PASS |
| 7 | `2(3+4)` | 14 | PASS | PASS | PASS | PASS | PASS |
| 8 | `2(3+4)(5−1)` | 56 | PASS | PASS | PASS | PASS | PASS |
| 9 | `(1+2)(3+4)` | 21 | PASS | PASS | PASS | PASS | PASS |
| 10 | `3(−2)` | -6 | PASS | PASS | PASS | PASS | PASS |
| 11 | `12÷(2+4)` | 2 | PASS | PASS | PASS | PASS | PASS |
| 12 | `1÷3+1÷6` | 0.5 | PASS | PASS | PASS | PASS | PASS |
| 13 | `2^3` | 8 | N/A | PASS | PASS | PASS | PASS |
| 14 | `2^−2` | 0.25 | N/A | PASS | PASS | PASS | PASS |
| 15 | `−2^2` | -4 | N/A | PASS | PASS | PASS | PASS |
| 16 | `(−2)^2` | 4 | N/A | PASS | PASS | PASS | INPUT |
| 17 | `√16` | 4 | N/A | PASS | PASS | PASS | PASS |
| 18 | `√(9+16)` | 5 | N/A | PASS | PASS | PASS | PASS |
| 19 | `5!` | 120 | N/A | PASS | PASS | PASS | N/A |
| 20 | `10÷4` | 2.5 | PASS | PASS | PASS | PASS | N/A |
| 21 | `0.1+0.2` | 0.3 | PASS | PASS | PASS | PASS | N/A |
| 22 | `100×1.05²` | 110.25 | N/A | PASS | PASS | PASS | PASS |
| 23 | `(3−1)/(9−3)` | 0.333333333 | PASS | PASS | PASS | PASS | N/A |
| 24 | `8÷2(2+2)` | 1 | PASS | PASS | PASS | PASS | PASS |
| 25 | `1/2+1/3` | 0.833333333 | PASS | PASS | PASS | PASS | N/A |
| 26 | `3.5×2` | 7 | PASS | PASS | PASS | PASS | N/A |
| 27 | `9−3×2+1` | 4 | PASS | PASS | PASS | PASS | N/A |
| 28 | `sin(30)` | 0.5 | N/A | PASS | PASS | PASS | N/A |
| 29 | `log(100)` | 2 | N/A | PASS | PASS | PASS | N/A |
| 30 | `2π` | 6.283185307 | N/A | PASS | PASS | PASS | N/A |
| 31 | `(5+3)/(2−2)` | error | PASS | PASS | FAIL | PASS | PASS |
| 32 | `99999×99999` | 9999800001 | PASS | PASS | PASS | PASS | N/A |
| 33 | `7+(−3)(−2)` | 13 | PASS | PASS | PASS | PASS | N/A |
| 34 | `2×(3+(4−1)×2)` | 18 | PASS | PASS | PASS | PASS | N/A |
| 35 | `5+5 = then ×2 =` | None | UNRES | UNRES | UNRES | UNRES | UNRES |
| 36 | `1(3−1)` | 2 | PASS | PASS | PASS | PASS | PASS |
| 37 | `(2)(3)` | 6 | PASS | PASS | PASS | PASS | PASS |
| 38 | `2(3)(4)(5)` | 120 | PASS | PASS | PASS | PASS | PASS |
| 39 | `−(3+4)` | -7 | PASS | PASS | PASS | PASS | PASS |
| 40 | `3−(−2)` | 5 | PASS | PASS | PASS | PASS | PASS |
| 41 | `(((1)))` | 1 | PASS | PASS | PASS | PASS | PASS |
| 42 | `2×−3` | -6 | PASS | PASS | PASS | PASS | PASS |
| 43 | `1+(2(3+4))` | 15 | PASS | PASS | PASS | PASS | PASS |
| 44 | `(1+2)(3+4)(5+6)` | 231 | PASS | PASS | PASS | PASS | PASS |
| 45 | `2(3+4)²` | 98 | N/A | PASS | PASS | PASS | PASS |
| 46 | `1÷(1÷(1÷2))` | 0.5 | PASS | PASS | PASS | PASS | PASS |

