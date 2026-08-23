# Mentis ClassWiz

A desktop MVP emulator inspired by the Casio fx-991EX ClassWiz calculator, built in Python. It ships with two interchangeable frontends on top of a shared calculation engine:

- **Desktop app** (`main.py`) — a PySide6/Qt replica of the ClassWiz body: LCD, SHIFT/ALPHA, D-pad, scientific and numeric keypads.
- **Browser MVP** (`mvp_server.py` + `frontend.html`) — a dependency-free local web server that renders the calculator in the browser using the authentic Casio ClassWiz fonts.

## Features

- 12 calculator modes: Calculate, Complex, Base-N, Matrix, Vector, Statistics, Distribution, Spreadsheet, Table, Equation/Func, Inequality, Ratio
- SHIFT / ALPHA secondary key functions, menu paging via the D-pad, Ans memory
- Scientific functions: trig/inverse trig, log/ln, roots, powers, factorials, definite integrals
- Division-by-zero and syntax errors surface as calculator-style errors
- Authentic Casio ClassWiz TTF fonts for the LCD rendering (browser frontend)

## Requirements

- Python 3.11+ (developed and built on 3.11)
- [PySide6](https://pypi.org/project/PySide6/) — desktop app only; the browser MVP uses only the standard library

## Installation

```bash
pip install -r requirements.txt
```

## Running from source

Desktop app:

```bash
python main.py
```

Browser MVP:

```bash
python mvp_server.py            # opens http://127.0.0.1:8000 in your browser
python mvp_server.py --no-browser   # start without opening a browser tab
```

The `ClassWizFontSet/` directory is a runtime asset for the browser frontend and must stay next to `mvp_server.py`.

## Testing

The repository uses two verification entry points instead of pytest.

Browser MVP verification suite (start the server first, then run the suite):

```bash
python mvp_server.py --no-browser
python verify.py
```

`verify.py` exercises arithmetic, scientific functions, integrals, mode switching, power on/off, font serving, and the frontend HTML, and exits non-zero on any failure.

Desktop smoke test (no window shown, exits 0 on success):

```bash
python main.py --smoke-test
```

## Building the executable

The desktop app is packaged with PyInstaller (one-folder build):

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name MentisClassWiz main.py
```

The result lands in `dist/MentisClassWiz/` (generated output, not committed).

## Project layout

```
main.py            PySide6 desktop application (entry point)
mvp_server.py      Local HTTP server for the browser MVP
frontend.html      Browser frontend UI
verify.py          Verification suite for the browser MVP
engine/            Calculation engine
  engine.py        Mode coordinator (dispatches to the tier-3 engines)
  evaluator.py     AST evaluation pipeline (tokenizer -> parser -> evaluator)
  <mode>/          One package per calculator mode (matrix, statistics, ...)
ClassWizFontSet/   Casio ClassWiz fonts (runtime assets)
```
