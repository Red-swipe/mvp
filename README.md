# Mentis ClassWiz

A desktop MVP emulator inspired by the Casio fx-991EX ClassWiz calculator, built in Python. It ships with two interchangeable frontends on top of a shared calculation engine:

- **Browser MVP** (`mvp_server.py` + `frontend.html`) — a standard-library-only local web server that renders the calculator in the browser using the authentic Casio ClassWiz fonts. This is the frontend that ships to users, as a portable folder with its own embedded Python.
- **Desktop app** (`main.py`) — a PySide6/Qt replica of the ClassWiz body: LCD, SHIFT/ALPHA, D-pad, scientific and numeric keypads.

## Features

- 12 calculator modes: Calculate, Complex, Base-N, Matrix, Vector, Statistics, Distribution, Spreadsheet, Table, Equation/Func, Inequality, Ratio
- SHIFT / ALPHA secondary key functions, menu paging via the D-pad, Ans memory
- Scientific functions: trig/inverse trig, log/ln, roots, powers, factorials, definite integrals
- MathI/MathO, LineI/LineO and DecimalO input/output modes, with exact fraction and surd output
- Simultaneous and polynomial equation solving with an editable coefficient grid
- Matrix, vector, spreadsheet and statistics screens
- Div-by-zero and syntax errors surface as calculator-style errors
- A QR screen encoding the product URL, generated locally and verified by decoding the rendered pixels
- Authentic Casio ClassWiz fonts (SIL OFL 1.1, licence shipped in `ClassWizFontSet/`)

## Requirements

- Python 3.11 or newer for source use and tests.
- PySide6 for the desktop app (`pip install -r requirements.txt`). The browser server and packaged runtime use the Python standard library.
- Tests additionally use the pinned packages in `audit/requirements-dev.txt`; browser tests need Playwright Chromium and Chrome.

## Installation and running

```bash
python -m pip install -r requirements.txt
python main.py                 # desktop app
python mvp_server.py           # browser app at http://127.0.0.1:8000
python mvp_server.py --no-browser
```

The browser runtime assets `ClassWizFontSet/`, `katex/` and `qrcode/` must remain beside `mvp_server.py`. They are vendored for offline use.

## Tests

```bash
python -m pip install -r requirements.txt -r audit/requirements-dev.txt
python -m playwright install chromium chrome
python -m pytest -vv
```

`pytest.ini` applies a 60-second per-test timeout and prints a traceback for stalled tests. Tests that require browser binaries skip with a visible reason when those binaries are absent. `scripts/verify.py` checks static frontend wiring and scroll indicators; it does not start a server.

## Building the portable ZIP

On Windows, run `portable\BUILD_ON_MY_PC.bat` from a machine with Python 3.11+ and internet access. The script downloads the CPython 3.12.8 embeddable runtime and calls `scripts/build_release.py`, which defines the runtime allowlist and writes `dist\calculator_portable.zip`. Extract the ZIP completely, then double-click `RUN_CALCULATOR.bat`. The launcher starts the server, opens the browser, selects another port if 8000 is busy, and closes cleanly with its console.

The ZIP works offline after download and extraction. The release contains only runtime files and launch instructions; it excludes tests, audit evidence, and developer scripts.

## Building the desktop executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name MentisClassWiz main.py
```

The result lands in `dist/MentisClassWiz/` (generated output, not committed).

## Known limitations

- Windows-only for the portable build: it relies on the embeddable CPython `.zip` + `._pth` layout and a `.bat` launcher.
- The portable build must be built on a machine with internet; only the resulting folder is offline-capable.
- Windows SmartScreen may warn on first launch of an unsigned `.bat`; the teacher instructions in `portable/README_FOR_TEACHER.txt` cover this.
- Opening `frontend.html` directly as a `file://` URL runs a reduced, in-browser bridge with no backend. Arithmetic and formatting work, but that mode is not the supported path — use `RUN_CALCULATOR.bat`.

## Project layout

```
main.py            PySide6 desktop application (entry point)
mvp_server.py      Local HTTP server for the browser MVP
frontend.html      Browser frontend UI (single-file app: markup, CSS, JS)
scripts/verify.py  Small end-to-end check against a running server
engine/            Calculation engine
  engine.py        Mode coordinator (dispatches to the tier-3 engines)
  evaluator.py     AST evaluation pipeline (tokenizer -> parser -> evaluator)
  <mode>/          One package per calculator mode (matrix, statistics, ...)
ClassWizFontSet/   Casio ClassWiz fonts + OFL licence (runtime assets)
katex/             Vendored KaTeX distribution (offline math typesetting)
qrcode/            Vendored MIT QR generator (offline QR screen)
portable/          Scripts that build and launch the portable distribution
```

## Mathematical Evaluation Conventions

Implicit multiplication follows the fx-991EX convention. For example, `8 / 2(2+2)` is evaluated as `8 / (2 * (2+2)) = 1`.
