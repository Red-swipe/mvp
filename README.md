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

- Python 3.11+ to run from source
- [PySide6](https://pypi.org/project/PySide6/) — **desktop app only**. The browser MVP and the portable build use only the standard library.

The shipped portable build carries its own **embeddable CPython 3.12.8** and does **not** use a system Python. The full test suite has been run green under Python 3.12.8.

## Installation

```bash
pip install -r requirements.txt   # desktop app only
```

The browser MVP and the portable build need no installation at all.

## Running from source

Browser MVP:

```bash
python mvp_server.py                   # serves http://127.0.0.1:8000
python mvp_server.py --no-browser      # start without opening a tab
```

Desktop app:

```bash
python main.py
```

`ClassWizFontSet/`, `katex/` and `qrcode/` are runtime assets for the browser frontend and must stay next to `mvp_server.py`. KaTeX and the QR generator are **vendored**, not loaded from a CDN, so the app works with no internet connection.

## Building the portable version (how users get it)

Run **once** on a Windows PC that has internet. It downloads the embeddable
Python runtime and produces the folder you copy to a USB stick:

```bat
cd portable
BUILD_ON_MY_PC.bat
```

The build writes to `calculator_portable/` at the repository root, verifies
itself by importing the real engine with the bundled interpreter, and prints a
`[SELFTEST]` report. It then exits non-zero if anything is missing.

To use it, copy the **whole** `calculator_portable/` folder to the target PC and
double-click `RUN_CALCULATOR.bat`. A console window opens, the calculator
appears in the browser, and closing the window stops it.

`calculator_portable/` is a generated artefact and is not committed (see `.gitignore`). Rebuild it on each machine you distribute from.

## Testing

The suite is **pytest**. From a Python 3.12 environment:

```bash
pip install pytest playwright opencv-python-headless pillow numpy fonttools
python -m pytest -q
```

Several tests drive a real Chrome via Playwright (`channel="chrome"`), so a local
Chrome install is required; tests needing it skip cleanly if it is unavailable.
`fonttools` and the image/decoder packages are optional — without them a small
number of tests skip.

Last recorded result on the release commit: **681 passed, 179 subtests, 0 failed, 0 skipped** under Python 3.12.8.

`verify.py` is a separate, smaller end-to-end check that expects a running server:

```bash
python mvp_server.py --no-browser
python verify.py
```

Desktop smoke test:

```bash
python main.py --smoke-test
```

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
verify.py          Small end-to-end check against a running server
engine/            Calculation engine
  engine.py        Mode coordinator (dispatches to the tier-3 engines)
  evaluator.py     AST evaluation pipeline (tokenizer -> parser -> evaluator)
  <mode>/          One package per calculator mode (matrix, statistics, ...)
ClassWizFontSet/   Casio ClassWiz fonts + OFL licence (runtime assets)
katex/             Vendored KaTeX distribution (offline math typesetting)
qrcode/            Vendored MIT QR generator (offline QR screen)
portable/          Scripts that build and launch the portable distribution
```