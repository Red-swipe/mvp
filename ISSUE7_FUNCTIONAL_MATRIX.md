# Issue 7 functional matrix audit

The audit used the served calculator at `127.0.0.1` and clicked the actual
`button[data-key]` elements. Each case reloaded the page, applied only a
declared modifier, captured the rendered LCD and browser diagnostics, and
continued after failures.

## Coverage

| Surface | Count |
|---|---:|
| Physical keys discovered | 51 |
| Normal mappings tested | 51 |
| Shift mappings tested | 37 |
| Alpha mappings tested | 20 |
| Menu modes tested | 12 |
| Setup options tested | 32 declared entries |
| Setup digit variants | 4 additional Fix/Sci/Norm prompt cases |
| Context-sensitive functions | 12 representative paths |

The 108 modifier-aware physical-key rows are 51 normal + 37 Shift + 20
Alpha. Unsupported modifier combinations were not generated.

## Initial discovery

| Status | Rows |
|---|---:|
| PASS | 170 |
| FAIL | 2 |
| INTENTIONAL-NO-OP | 14 |
| CONTEXT-DEPENDENT | 12 |
| HARNESS ERRORS | 2, resolved |

The two failures were independent application defects. The two harness errors
were an over-generated unsupported Alpha+OPTN case and a QR-panel timing issue;
the QR panel rendered correctly when checked after the interaction.

## Bugs fixed

### ISSUE 7.1 — frontend statistics settings sync

- Function: initial `/api/settings` synchronization.
- Reproduction: load the served frontend; it sent `statistics_frequency` and
  received HTTP 400 `Invalid input_output` from the backend validation path.
- Root cause: the validator accepted `statisticsFrequency` and
  `stat_frequency`, but not the frontend's exact `statistics_frequency` key.
- Fix: accept the snake-case key used by the frontend.
- Regression test: `test_frontend_settings_sync_accepts_statistics_frequency`.
- Commit: `45828b8`.
- Push: `origin/frontend_fixes_october`.

### ISSUE 7.2 — Alpha Base-N base switching

- Function: Alpha+DEC/HEX/BIN/OCT.
- Reproduction: enter Base-N, press Alpha, then the square/power/log/ln key;
  the ordinary calculation template was inserted instead of switching base.
- Root cause: the Base-N switch branch was gated on Shift only.
- Fix: route both Shift and Alpha through the existing base-switch table.
- Regression test: `test_alpha_base_switch_branches` plus live browser verification.
- Commit: `4a35ce9`.
- Push: `origin/frontend_fixes_october`.

## Final matrix

| Status | Rows |
|---|---:|
| PASS | 194 |
| FAIL | 0 |
| INTENTIONAL-NO-OP | 14 |
| CONTEXT-DEPENDENT | 12 |
| HARNESS ERRORS | 0 |

All mapped physical functions, all 12 menu modes, and all 14 Setup registry
entries were exercised; no uncaught browser exception or unexpected calculator
error remained after the two fixes.
