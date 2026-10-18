# Testing guide

Everything needed to reproduce the test suite and the audit comparator.
All versions below were **observed on this machine**, not copied from a
manifest — the repository declared no test dependencies at all before this file.

## Observed environment

| component | version / path | verification command |
|---|---|---|
| CPython | **3.11.15** | `python --version` |
| python executable | `…\hermes\hermes-agent\venv\Scripts\python.exe` | `python -c "import sys; print(sys.executable)"` |
| pytest | **9.1.1** | `python -m pytest --version` |
| playwright (Python) | **1.62.0** | `python -m pip show playwright` |
| node | **v24.15.0** | `node --version`, `C:\Program Files\nodejs\node.exe` |
| Chromium build | **1228** | `%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe` |
| Chromium product version | **149.0.7827.55** | file `VersionInfo.ProductVersion` |

Firefox and WebKit are **not** installed. Every browser observation in this
repository is Chromium only, and is labelled as such.

## The runtime contract this does not violate

`requirements.txt` contains exactly one line:

```
PySide6>=6.6
```

The shipped product is a **portable, standalone** CPython 3.12.8 bundle with no
pip and no third-party packages. It therefore **cannot run pytest**, and never
has (`CLAUDE_HANDOVER.md:37,668,778`).

That is not a contradiction with this guide: the test tooling is for
development on a full machine, and lives in `audit/requirements-dev.txt`
specifically so `requirements.txt` keeps describing only what ships.

## About the dependency pins

`audit/requirements-dev.txt` uses **lower bounds, not exact pins**. Exact pins
would be false precision: these packages were already installed in this
environment and were not resolved by this repository, so claiming an exact
reproducible set would be a claim I cannot back. The versions above are what
was verified.

## Clean-environment verification checklist

**Status: NOT VERIFIED.** This repository has never been tested from a clean
virtual environment on this machine. Everything above ran against a
pre-existing interpreter with packages I did not install and did not resolve.

To actually verify reproducibility, on a fresh machine or a fresh venv:

```powershell
# 1. fresh environment
python -m venv .venv-audit
.\.venv-audit\Scripts\Activate.ps1

# 2. runtime dependencies only -- must NOT need pip at all in the shipped
#    product, but the source tree does import PySide6 in places
python -m pip install -r requirements.txt

# 3. development dependencies
python -m pip install -r audit\requirements-dev.txt
python -m playwright install chromium

# 4. node separately (not a pip package)
node --version

# 5. prove the versions match what was verified above
python --version
python -m pytest --version
python -m pip show playwright
node --version

# 6. collection must succeed before any test is trusted
python -m pytest --collect-only -q

# 7. full suite
python -m pytest -q --tb=short -rs

# 8. the audit comparator
python audit\tools\run_comparator.py --out audit\evidence\<run>
python audit\tools\build_keypad_inventory.py --out audit\evidence\<run>\keypad_inventory.json
python audit\tools\ans_sequences.py --out audit\evidence\<run>
```

If step 6 fails, or step 7 reports failures that are NOT the four known ones,
the environment is not equivalent and the results are not comparable.

### Known blockers to full reproducibility

- **Chromium is pinned by absolute path** in `audit/tools/collectors.py`
  (`CHROMIUM = …\ms-playwright\chromium-1228\…`). On a machine whose Playwright
  installed a different build, that constant must be updated or replaced with a
  Playwright-managed launch. This WILL break on a fresh environment.
- Firefox and WebKit are not installed, so the cross-browser requirement is
  unmet by owner decision (`raw/context.md`).
- The delivered release bundles CPython 3.12.8, which is **not** the interpreter
  used here. No result in this repository has been reproduced on 3.12.

## Run the existing suite

```powershell
python -m pytest -q --tb=short -rs
```

Observed characteristics, measured:

- Collection: `python -m pytest --collect-only -q` → succeeded, exit 0.
  The `test_safe_eval_regressions.py` bare-collection abort claimed in
  `button_audit.md:213` does **not** reproduce.
- Runtime ≈ 9 min, dominated by the browser suites.
- Phase C baseline: **4 failed, 677 passed, 179 subtests**, exit 1
  (`audit/evidence/phase-b-20261015/baseline_pytest_q.log`).
- Phase D baseline: **4 failed, 694 passed + audit modules, 179 subtests**.
  See `audit/evidence/phase-d-20261015/` for the current log. The four
  pre-existing failures are unchanged; Phase D adds new audit test modules and
  changes no existing test.

## Run the audit comparator

```powershell
python audit\tools\run_comparator.py --out audit\evidence\phase-c-20261015
```

Runs all 46 battery cases through all five collectors and writes:

- `comparator_results.json` — raw observations plus verdicts, nothing discarded
- `divergence_matrix.md` — 46 rows × 5 collectors
- `divergence_matrix.csv` — same, with the reason for every cell

Runtime ≈ 3 min. Needs node and chromium; a missing collector reports
`collector_error` for its cases instead of aborting the run.

Outputs per run:

- `comparator_results.json` — raw observations, verdicts and full evidence
- `divergence_matrix.md` / `.csv` — 46 rows × 5 collectors
- `failure_report.md` — every non-passing cell grouped by classification

Two further instruments, same evidence directory:

```powershell
python audit\tools\build_keypad_inventory.py   # keypad coverage, getExpr() per case
python audit\tools\ans_sequences.py            # stateful Ans sequences, both paths
```

### Audit test modules

```powershell
python -m pytest test_comparator_tools.py test_comparator_battery.py `
       test_comparator_classification.py test_keypad_inventory.py `
       test_browser_evidence.py test_ans_sequences.py -q
```

### Inputs

- `audit/data/cases.json` — the declarative battery. Traced to
  `raw/context.md` section "The 46 case battery (expected values)".
- `audit/docs/adjacency_contract.md` — **undecided**, gates rows 8, 9, 24, 33,
  37, 38, 44.
- `audit/docs/divzero_contract.md` — **partially undecided**, gates row 31.

### What the comparator does NOT do

It does not fail the build. The battery is evidence, not a gate, because two
semantic contracts are still open. When they are closed, its matrix becomes the
acceptance criterion.

## Regenerating the keypad-verified internal expressions

30 of 46 `internal_expr` values were read from the live page, not typed:

```powershell
python audit\evidence\phase-c-20261015\capture_internal_expr.py `
       frontend.html `
       audit\evidence\phase-b-20261015\probe_path_a.py
```

Re-run this if `frontend.html` changes; it is the only source of truth for what
the keypad actually builds.

## Known environment limitations

- No Firefox, no WebKit. `raw/context.md` records these as deliberately
  UNTESTED by owner decision.
- No CPython 3.12 available here; the bundled interpreter in the delivered
  release was never executed.
- The comparator pins chromium by absolute path in `audit/tools/collectors.py`.
  On another machine that constant must be updated, or `CHROMIUM` pointed at a
  normal Playwright-managed browser instead.