# Repository health audit — 2026-10-28

## Scope and source of truth

`main` is the development source of truth. The release branch `v0.12` is rebuilt from the runtime allowlist in `scripts/build_release.py`; development history and audit material are intentionally absent from that release tree. No merge from `v0.12` to `main` is part of this process.

## Baseline and final test results

Python 3.11.15, pytest 9.1.1, and pytest-timeout 2.4.0 were used. The initial bounded per-directory baseline completed with 925 passed, 2 skipped, 1 expected xfail, 306 passing subtests, and 0 failures/errors (928 collected). The two skips are PyInstaller spec checks because the repository has no matching spec files; the xfail is an existing documented expected failure.

After changes, the full suite completed in 771.03 seconds: 930 passed, 2 skipped, 1 expected xfail, 306 passing subtests, 0 failures/errors (933 collected). The five additional collected tests are the new derivative precision coverage.

Earlier runs in the original checkout did not produce a summary because that execution context could not write temporary JavaScript harness files. Running in the writable main worktree with Python 3.11 and the configured timeout completed; no application hang was reproduced. `pytest.ini` now sets a 60-second test timeout, thread timeout method, faulthandler timeout, no cache provider, and test helper paths.

The regression suite confirms cursor insertion at the caret, DEL as backspace, and AC as a full reset.

## Calculus precision

No derivative algorithm was ported from v0.12. Main already contains Richardson extrapolation (commit `53ecdc8`), which is at least as accurate as the fifth-order five-point step in v0.12 commit `37a04de`. Added `tests/unit/test_calculus_precision.py` for polynomial, sine, exponential, logarithm, and a small-step-sensitive function. The focused precision and existing calculus tests passed: 30 passed, 64 deselected, 9 subtests.

## Hygiene and implementation changes

- Removed the zero-byte `docs/audit/partial_edits.patch`.
- Added `.gitattributes` for normalized text line endings and CRLF batch files; completed ignores for virtual environments, Python caches, build output, logs, and generated JavaScript harnesses.
- Pinned runtime and development requirements.
- Added portable Playwright browser discovery for regression/server tests.
- Added a release allowlist builder that creates `dist/calculator_portable.zip` and excludes audit, documentation, tests, and developer scripts from the package.
- Replaced the launcher and Windows batch files to use the builder and support paths with spaces, visible Python errors, alternative local ports, and noninteractive smoke mode.
- Corrected README instructions for setup, running, testing, verification, and portable packaging.
- Added a Linux headless GitHub Actions workflow for push and pull request to `main`; it installs Python, Node, and the browser dependencies. The workflow was not executed on GitHub during this local audit.
- No tracked root-level test files, bytecode/cache/build outputs, or files larger than 5 MB were found.
- The tracked-source secret scan found no credential-like material; vendored JavaScript and audit data were excluded from that pattern scan to avoid minified-code and evidence false positives.

Commits: `79b562a` (precision regression tests), `7dbdd90` (test configuration and baseline hygiene), `aa80dda` (portable browser discovery), `4485e3c` (allowlist release builder and launchers), and `9e34a6a` (GitHub Actions).

## Rescued work triage

The three files on `rescue/uncommitted_20261028` were compared with `origin/main` and `origin/v0.12`. All remain preserved on the rescue branch. The integration settings test has an outdated fraction-format expectation (`ab/c` instead of the current `d/c`) and was not applied. The rescued S-to-D test edit removes existing behavior coverage and is weaker than main's test, so it was not applied. The rescued lowercase-x test removes a required `getParent()` stub from its isolated JavaScript harness and is stale, so it was not applied.

## Branch and tag state at audit writing

Pre-audit tags: `pre_audit_main_20261028` at `c240cda349f2b32861e6b3c26c9fbdd86515bcc9` and `pre_audit_v012_20261028` at `37a04ded73eea68752431d71c9c9c919b2a3c5b2`. Rescue branch `rescue/uncommitted_20261028` remains preserved at `745ae502b1eba866810f72de29e6be466cf1c0b1`. Other existing branches and tags are listed in the final audit report; no unrelated branches or tags were changed.

## Remaining verification

The Windows ZIP build and extraction/launcher smoke test, release-tree regeneration, v0.12 parity test run, pushes, sync proof, and gated old-branch deletion are recorded in the final audit report after those steps complete.
