"""Local browser MVP server for the ClassWiz HTML frontend."""

from __future__ import annotations

import argparse
import json
import cmath
import math
import mimetypes
import os
import random
import re
import sys
import threading
import webbrowser
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent

from engine.engine import Engine
from engine.calculus.calculus_engine import CalculusEngine
from engine.spreadsheet.spreadsheet_engine import SpreadsheetEngine
from engine.evaluator import evaluate
from engine.parser import parse
from engine.tokenizer import tokenize

MODE_MAP = {
    "Calculate": "CALC",
    "Complex": "COMPLEX",
    "Base-N": "BASE_N",
    "Matrix": "MATRIX",
    "Vector": "VECTOR",
    "Statistics": "STATISTICS",
    "Distribution": "DISTRIBUTION",
    "Spreadsheet": "SPREADSHEET",
    "Table": "TABLE",
    "Equation/Func": "EQUATION",
    "Inequality": "INEQUALITY",
    "Ratio": "CALC",
}

MENU_PAGES = [
    [
        ("1", "Calculate"), ("2", "Complex"), ("3", "Base-N"), ("4", "Matrix"),
        ("5", "Vector"), ("6", "Statistics"), ("7", "Distribution"), ("8", "Spreadsheet"),
    ],
    [("9", "Table"), ("10", "Equation/Func"), ("11", "Inequality"), ("12", "Ratio")],
]

CALC_ENGINE = CalculusEngine()

_SPECIAL_FUNCS = ('integral', 'sigma', 'diff', 'log_base', 'xroot', 'cbrt', 'sqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh', 'Abs', 'abs', 'round', 'Rnd', 'FACT', 'RanInt', 'Pol', 'Rec', 'nCr', 'nPr')

DIV_ZERO_MSG = "To infinity and beyonddd"


def _group_integer_part(ip: str) -> str:
    """Group an integer digit-run in threes (ClassWiz digit separator)."""
    if len(ip) <= 3:
        return ip
    out = []
    while len(ip) > 3:
        out.append(ip[-3:])
        ip = ip[:-3]
    out.append(ip)
    return ' '.join(reversed(out))


def format_display(value_str, decimal_mark="Dot", digit_separator=False) -> str:
    """Display layer only (fx-991EX Decimal Mark / Digit Separator).

    Never touches internal values: callers keep canonical results (dots, no
    separators) for Ans/storage/evaluation and format only for the LCD.
    With Comma mark, multi-value ',' separators become ';' (per the manual).
    """
    s = str(value_str)
    if s in ("", "Math ERROR", "Dimension ERROR", DIV_ZERO_MSG):
        return s
    approx = s.startswith("≈")
    core = s[1:] if approx else s
    if digit_separator:
        def grp(m):
            num = m.group(0)
            sign = ''
            if num[:1] in ('+', '-'):
                sign, num = num[0], num[1:]
            if '.' in num:
                ip, fp = num.split('.', 1)
                return sign + _group_integer_part(ip) + '.' + fp
            return sign + _group_integer_part(num)
        core = re.sub(r'[+-]?\d+(?:\.\d+)?', grp, core)
    if decimal_mark == "Comma":
        core = core.replace(',', ';').replace('.', ',')
    return ('≈' if approx else '') + core


def _rnd_value(v, setting) -> float:
    """Rnd() per fx-991EX User's Guide: round in accordance with the current
    Number Format setting. Fix n -> n decimal places; Sci n -> n significant
    digits; Norm 1/2 -> rounded off at the 11th digit of the mantissa
    (10 significant digits). Half-up, and the rounded value is internal too.
    """
    from decimal import Decimal, ROUND_HALF_UP
    if isinstance(v, complex):
        if abs(v.imag) > 1e-14:
            raise ValueError("Math ERROR")
        v = v.real
    d = Decimal(str(v))
    if d.is_nan() or d.is_infinite():
        raise ValueError("Math ERROR")
    kind = (setting or ("Norm",))[0]
    if kind == "Fix":
        places = int((setting or ("Fix", 2))[1]) if len(setting or ()) > 1 else 2
        places = max(0, min(9, places))
        q = Decimal(1).scaleb(-places)
        return float(d.quantize(q, rounding=ROUND_HALF_UP))
    if kind == "Sci":
        sig = int((setting or ("Sci", 10))[1]) if len(setting or ()) > 1 else 10
        if sig <= 0:
            sig = 10
        sig = max(1, min(10, sig))
        if d.is_zero():
            return 0.0
        exp = d.adjusted()
        q = Decimal(1).scaleb(exp - sig + 1)
        return float(d.quantize(q, rounding=ROUND_HALF_UP))
    # Norm 1 / Norm 2: 10 significant digits
    if d.is_zero():
        return 0.0
    exp = d.adjusted()
    q = Decimal(1).scaleb(exp - 10 + 1)
    return float(d.quantize(q, rounding=ROUND_HALF_UP))

def _lit(v) -> str:
    """Format a float so the engine tokenizer can always parse it (no 1e-06)."""
    try:
        f = float(v)
    except Exception:
        # Non-floats (e.g. complex) splice verbatim; the safe complex
        # sub-parser handles the trailing 'j'.
        return f'({v!r})'
    r = repr(f)
    if 'e' not in r and 'E' not in r and 'inf' not in r and 'nan' not in r:
        return f'({r})'
    s = format(f, '.15f')
    s = s.rstrip('0').rstrip('.')
    if s in ('', '-0', '-'):
        s = '0'
    if s.startswith('-.'):
        s = '-0.' + s[2:]
    if s.startswith('.'):
        s = '0' + s
    return f'({s})'



def _casin(z: complex) -> complex:
    """Principal asin via an explicit formula (deterministic across
    platforms; matches the FILE_MODE bridge exactly)."""
    return -1j * cmath.log(1j * z + cmath.sqrt(1 - z * z))


def _cacos(z: complex) -> complex:
    return math.pi / 2 - _casin(z)


def _catan(z: complex) -> complex:
    return _casin(z / cmath.sqrt(1 + z * z))


def _prime_factorization_str(n: int) -> str:
    """Prime factorization display for FACT (fx-991EX FACT shows prime factors)."""
    if n < 0:
        raise ValueError("Math ERROR")
    if n in (0, 1):
        return str(n)
    orig = n
    factors: dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    if len(factors) == 1 and list(factors.values())[0] == 1 and orig in factors:
        return str(orig)  # prime stays as-is
    parts = []
    for p in sorted(factors):
        e = factors[p]
        parts.append(str(p) if e == 1 else f"{p}^{e}")
    return "×".join(parts)


def _transform_percent(s: str) -> str:
    """Casio % = postfix percent (/100). 50% -> (50/100). Handles )% and digit% and Ans%)."""
    # Apply repeatedly for cases like 50%%.
    for _ in range(20):
        m = re.search(r'(\(\s*[^()]*\s*\)|(?:Ans|ans|pi|\u03c0|e)|\d+(?:\.\d+)?)\s*%', s)
        if not m:
            return s
        operand = m.group(1)
        s = s[:m.start()] + f'(({operand})/100)' + s[m.end():]
    return s


DEFAULT_SETTINGS = {
    "inputOutput": "MathI/MathO",
    "angleUnit": "Degree",
    "numberFormat": "Norm",
    "numberFormatPrecision": 1,
    "engineeringSymbols": False,
    "fractionResult": "ab/c",
    "statisticsFrequency": False,
    "autoCalc": True,
    "showCell": "Value",
}

DEFAULT_SETUP_SETTINGS = {
    "input_output":          "MathI/MathO",
    "angle_unit":            "Degree",
    "number_format":         "Norm",
    "number_format_digits":  2,
    "engineering_symbols":   False,
    "fraction_result":       "ab/c",
    "stat_frequency":        True,
    "spreadsheet_auto_calc": True,
    "spreadsheet_show":      "value",
    "equation_complex":      False,
    "table_mode":            "f(x)",
    "decimal_mark":          "Dot",
    "digit_separator":       False,
    "multiline_font":        "Normal",
    "contrast":              5,
}


def _find_matching_paren(s: str, open_idx: int) -> int:
    """Return the index of the ')' matching the '(' at open_idx, or -1 if unbalanced."""
    depth = 0
    for i in range(open_idx, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_top_level_args(inner: str) -> list:
    """Split inner on commas that sit outside any parentheses."""
    parts = []
    depth = 0
    current = []
    for ch in inner:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append(''.join(current).strip())
    return parts


def _find_special_call(s: str):
    """Locate the leftmost supported special-function call.

    Returns (name, start_index) or None. A match requires a word boundary on
    the left and '(' immediately after the function name.
    """
    best = None
    for name in _SPECIAL_FUNCS:
        pos = 0
        while True:
            idx = s.find(name, pos)
            if idx < 0:
                break
            end = idx + len(name)
            boundary_ok = idx == 0 or not (s[idx - 1].isalnum() or s[idx - 1] == '_')
            if boundary_ok and end < len(s) and s[end] == '(':
                if best is None or idx < best[1]:
                    best = (name, idx)
            pos = end
    return best


def _transform_special_functions(s: str, ans_val: float, angle_unit: str = "Degree", variables=None, complex_mode: bool = False, rnd_setting=None) -> str:
    """Replace supported special-function calls with plain Python expressions.

    Uses a balanced-parentheses scan so nested parentheses inside arguments and
    nested special functions are handled correctly. Division by zero surfaces
    naturally from evaluation (e.g. xroot(0, 5)).
    """
    while True:
        found = _find_special_call(s)
        if found is None:
            return s
        name, start = found
        open_idx = start + len(name)
        close_idx = _find_matching_paren(s, open_idx)
        if close_idx < 0:
            raise ValueError("Math ERROR: unbalanced parentheses")
        args = _split_top_level_args(s[open_idx + 1:close_idx])

        if name == 'integral':
            if len(args) != 3 or not all(args):
                raise ValueError("Math ERROR: integral expects 3 arguments")
            integrand_str = args[0]
            a_val = safe_evaluate_expression(args[1], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            b_val = safe_evaluate_expression(args[2], ans_val, angle_unit, variables, complex_mode, rnd_setting)

            def integrand_func(x):
                sub_expr = re.sub(r'\bx\b', _lit(x), integrand_str)
                return safe_evaluate_expression(sub_expr, ans_val, angle_unit, variables, complex_mode, rnd_setting)

            res = CALC_ENGINE.integrate(integrand_func, a_val, b_val)
            replacement = _lit(float(res))
        elif name == 'log_base':
            if len(args) != 2 or not all(args):
                raise ValueError("Math ERROR: log_base expects 2 arguments")
            base = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            value = safe_evaluate_expression(args[1], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            replacement = _lit(math.log(value) / math.log(base))
        elif name == 'xroot':
            if len(args) != 2 or not all(args):
                raise ValueError("Math ERROR: xroot expects 2 arguments")
            n_val = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            radicand = safe_evaluate_expression(args[1], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if (not isinstance(radicand, complex) and not isinstance(n_val, complex)
                    and float(n_val).is_integer() and int(n_val) % 2 == 1 and radicand < 0):
                # Real odd root of a negative (fx-991EX gives a real result).
                replacement = _lit(-((-radicand) ** (1 / n_val)))
            else:
                replacement = _lit(radicand ** (1 / n_val))
        elif name == 'cbrt':
            if len(args) != 1 or not args[0]:
                raise ValueError("Math ERROR: cbrt expects 1 argument")
            _cbrt_v = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if not isinstance(_cbrt_v, complex) and _cbrt_v < 0:
                # Real cube root of a negative (fx-991EX gives a real result).
                replacement = _lit(-((-_cbrt_v) ** (1 / 3)))
            else:
                replacement = _lit(_cbrt_v ** (1 / 3))
        elif name in {'sin', 'cos', 'tan'}:
            if len(args) != 1 or not args[0]:
                raise ValueError(f"Math ERROR: {name} expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(value, complex) and abs(value.imag) <= 1e-14:
                value = value.real
            if isinstance(value, complex):
                if not complex_mode:
                    raise ValueError("Math ERROR")
                if angle_unit == "Radian":
                    radians = value
                elif angle_unit == "Gradian":
                    radians = value * (math.pi / 200.0)
                else:
                    radians = value * (math.pi / 180.0)
                if name == 'sin':
                    result = cmath.sin(radians)
                elif name == 'cos':
                    result = cmath.cos(radians)
                else:
                    cosine = cmath.cos(radians)
                    if abs(cosine) < 1e-12:
                        raise ValueError("Math ERROR")
                    result = cmath.tan(radians)
                replacement = _lit(result)
                s = s[:start] + replacement + s[close_idx + 1:]
                continue
            if angle_unit == "Radian":
                radians = value
            elif angle_unit == "Gradian":
                radians = value * (math.pi / 200.0)
            else:
                radians = value * (math.pi / 180.0)
            if name == 'sin':
                result = math.sin(radians)
            elif name == 'cos':
                result = math.cos(radians)
            else:
                cosine = math.cos(radians)
                if abs(cosine) < 1e-12:
                    raise ValueError("Math ERROR")
                result = math.tan(radians)
            replacement = _lit(result)
        elif name in {'asin', 'acos', 'atan'}:
            if len(args) != 1 or not args[0]:
                raise ValueError(f"Math ERROR: {name} expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(value, complex) and abs(value.imag) <= 1e-14:
                value = value.real
            if isinstance(value, complex) or (
                    name in ('asin', 'acos') and not abs(value) <= 1):
                if not complex_mode:
                    raise ValueError("Math ERROR")
                cv = value if isinstance(value, complex) else complex(float(value))
                if name == 'asin':
                    radians = _casin(cv)
                elif name == 'acos':
                    radians = _cacos(cv)
                else:
                    radians = _catan(cv)
                if angle_unit == "Radian":
                    result = radians
                elif angle_unit == "Gradian":
                    result = radians * (200.0 / math.pi)
                else:
                    result = radians * (180.0 / math.pi)
                replacement = _lit(result)
                s = s[:start] + replacement + s[close_idx + 1:]
                continue
            if name == 'asin':
                if not abs(value) <= 1:
                    raise ValueError("Math ERROR")
                radians = math.asin(value)
            elif name == 'acos':
                if not abs(value) <= 1:
                    raise ValueError("Math ERROR")
                radians = math.acos(value)
            else:
                radians = math.atan(value)
            if angle_unit == "Radian":
                result = radians
            elif angle_unit == "Gradian":
                result = radians * (200.0 / math.pi)
            else:
                result = radians * (180.0 / math.pi)
            replacement = _lit(result)
        elif name == 'ln':
            if len(args) != 1 or not args[0]:
                raise ValueError("Math ERROR: ln expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(value, complex) and abs(value.imag) <= 1e-14:
                value = value.real
            if isinstance(value, complex):
                if not complex_mode or value == 0:
                    raise ValueError("Math ERROR")
                replacement = _lit(cmath.log(value))
                s = s[:start] + replacement + s[close_idx + 1:]
                continue
            if not value > 0:
                if complex_mode and value < 0:
                    replacement = _lit(cmath.log(value))
                    s = s[:start] + replacement + s[close_idx + 1:]
                    continue
                raise ValueError("Math ERROR")
            replacement = _lit(math.log(value))
        elif name == 'log':
            if len(args) != 1 or not args[0]:
                raise ValueError("Math ERROR: log expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(value, complex) and abs(value.imag) <= 1e-14:
                value = value.real
            if isinstance(value, complex):
                if not complex_mode or value == 0:
                    raise ValueError("Math ERROR")
                replacement = _lit(cmath.log10(value))
                s = s[:start] + replacement + s[close_idx + 1:]
                continue
            if not value > 0:
                if complex_mode and value < 0:
                    replacement = _lit(cmath.log10(value))
                    s = s[:start] + replacement + s[close_idx + 1:]
                    continue
                raise ValueError("Math ERROR")
            replacement = _lit(math.log10(value))
        elif name in {'sinh', 'cosh', 'tanh'}:
            if len(args) != 1 or not args[0]:
                raise ValueError(f"Math ERROR: {name} expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(value, complex) and abs(value.imag) <= 1e-14:
                value = value.real
            if isinstance(value, complex):
                if not complex_mode:
                    raise ValueError("Math ERROR")
                if name == 'sinh':
                    result = cmath.sinh(value)
                elif name == 'cosh':
                    result = cmath.cosh(value)
                else:
                    result = cmath.tanh(value)
                replacement = _lit(result)
                s = s[:start] + replacement + s[close_idx + 1:]
                continue
            if name == 'sinh':
                result = math.sinh(value)
            elif name == 'cosh':
                result = math.cosh(value)
            else:
                result = math.tanh(value)
            replacement = _lit(result)
        elif name in {'Abs', 'abs'}:
            if len(args) != 1 or not args[0]:
                raise ValueError(f"Math ERROR: {name} expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            replacement = _lit(abs(value))
        elif name in {'round', 'Rnd'}:
            if len(args) != 1 or not args[0]:
                raise ValueError("Math ERROR: round expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            # fx-991EX Rnd: round per the current Number Format setting
            # (Fix decimals / Sci significant digits / Norm 10-digit mantissa).
            replacement = _lit(_rnd_value(value, rnd_setting or ("Norm",)))
        elif name == 'RanInt':
            if len(args) not in (1, 2) or not all(args):
                raise ValueError("Math ERROR: RanInt expects 1 or 2 arguments")
            vals = [safe_evaluate_expression(a, ans_val, angle_unit, variables, complex_mode, rnd_setting) for a in args]
            for v in vals:
                if isinstance(v, complex) or not float(v).is_integer():
                    raise ValueError("Math ERROR")
            ints = [int(v) for v in vals]
            if len(ints) == 1:
                lo, hi = 1, ints[0]
            else:
                lo, hi = ints
            if lo > hi:
                lo, hi = hi, lo
            if hi < 1 and len(ints) == 1:
                raise ValueError("Math ERROR")
            replacement = _lit(random.randint(lo, hi))
        elif name == 'Pol':
            if len(args) != 2 or not all(args):
                raise ValueError("Math ERROR: Pol expects 2 arguments")
            x = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            y = safe_evaluate_expression(args[1], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(x, complex) or isinstance(y, complex):
                raise ValueError("Math ERROR")
            r_val = math.hypot(x, y)
            if angle_unit == "Radian":
                theta_val = math.atan2(y, x)
            elif angle_unit == "Gradian":
                theta_val = math.atan2(y, x) * (200.0 / math.pi)
            else:
                theta_val = math.atan2(y, x) * (180.0 / math.pi)
            if isinstance(variables, dict):
                variables['X'] = float(r_val)
                variables['Y'] = float(theta_val)
            replacement = _lit(r_val)
        elif name == 'Rec':
            if len(args) != 2 or not all(args):
                raise ValueError("Math ERROR: Rec expects 2 arguments")
            r = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            theta = safe_evaluate_expression(args[1], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(r, complex) or isinstance(theta, complex):
                raise ValueError("Math ERROR")
            if angle_unit == "Radian":
                radians = theta
            elif angle_unit == "Gradian":
                radians = theta * (math.pi / 200.0)
            else:
                radians = theta * (math.pi / 180.0)
            x_val = r * math.cos(radians)
            y_val = r * math.sin(radians)
            if isinstance(variables, dict):
                variables['X'] = float(x_val)
                variables['Y'] = float(y_val)
            replacement = _lit(x_val)
        elif name == 'sigma':
            if len(args) != 3 or not all(args):
                raise ValueError("Math ERROR: sigma expects 3 arguments")
            body_str = args[0]
            a_val = safe_evaluate_expression(args[1], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            b_val = safe_evaluate_expression(args[2], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            for v in (a_val, b_val):
                if isinstance(v, complex) or not float(v).is_integer():
                    raise ValueError("Math ERROR")
            a_int, b_int = int(a_val), int(b_val)

            def sigma_func(x):
                sub_expr = re.sub(r'\bx\b', _lit(x), body_str)
                return safe_evaluate_expression(sub_expr, ans_val, angle_unit, variables, complex_mode, rnd_setting)

            res = CALC_ENGINE.sigma(sigma_func, a_int, b_int)
            replacement = _lit(float(res))
        elif name == 'diff':
            if len(args) != 2 or not all(args):
                raise ValueError("Math ERROR: diff expects 2 arguments")
            body_str = args[0]
            x0 = safe_evaluate_expression(args[1], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(x0, complex):
                raise ValueError("Math ERROR")

            def diff_func(x):
                sub_expr = re.sub(r'\bx\b', _lit(x), body_str)
                return safe_evaluate_expression(sub_expr, ans_val, angle_unit, variables, complex_mode, rnd_setting)

            res = CALC_ENGINE.differentiate(diff_func, float(x0))
            replacement = _lit(float(res))
        elif name in {'nCr', 'nPr'}:
            if len(args) != 2 or not all(args):
                raise ValueError(f"Math ERROR: {name} expects 2 arguments")
            n_val = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            r_val = safe_evaluate_expression(args[1], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if not float(n_val).is_integer() or not float(r_val).is_integer():
                raise ValueError("Math ERROR")
            n_int, r_int = int(n_val), int(r_val)
            if n_int < 0 or r_int < 0 or r_int > n_int:
                raise ValueError("Math ERROR")
            result = math.comb(n_int, r_int) if name == 'nCr' else math.factorial(n_int) // math.factorial(n_int - r_int)
            replacement = _lit(result)
        elif name in {'asinh', 'acosh', 'atanh'}:
            if len(args) != 1 or not args[0]:
                raise ValueError(f"Math ERROR: {name} expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(value, complex) and abs(value.imag) <= 1e-14:
                value = value.real
            if isinstance(value, complex):
                if not complex_mode:
                    raise ValueError("Math ERROR")
                if name == 'asinh':
                    result = cmath.asinh(value)
                elif name == 'acosh':
                    result = cmath.acosh(value)
                else:
                    result = cmath.atanh(value)
                replacement = _lit(result)
                s = s[:start] + replacement + s[close_idx + 1:]
                continue
            try:
                if name == 'asinh':
                    result = math.asinh(value)
                elif name == 'acosh':
                    result = math.acosh(value)
                else:
                    result = math.atanh(value)
            except ValueError:
                raise ValueError("Math ERROR")
            replacement = _lit(result)
        elif name == 'FACT':
            if len(args) != 1 or not args[0]:
                raise ValueError("Math ERROR: FACT expects 1 argument")
            value = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(value, complex):
                if abs(value.imag) > 1e-14:
                    raise ValueError("Math ERROR")
                value = value.real
            if not float(value).is_integer() or value < 0:
                raise ValueError("Math ERROR")
            n = int(value)
            if n > 999999:
                raise ValueError("Math ERROR")
            # Signal factorization display via sentinel string the caller detects.
            replacement = f'__FACT__{n}__'
        else:  # sqrt
            if len(args) != 1 or not args[0]:
                raise ValueError("Math ERROR: sqrt expects 1 argument")
            _sq = safe_evaluate_expression(args[0], ans_val, angle_unit, variables, complex_mode, rnd_setting)
            if isinstance(_sq, complex):
                if abs(_sq.imag) > 1e-14:
                    raise ValueError("Math ERROR")
                _sq = _sq.real
            try:
                replacement = _lit(math.sqrt(_sq))
            except ValueError:
                if complex_mode and _sq < 0:
                    _cv = cmath.sqrt(_sq)
                    _im = ('+' if _cv.imag >= 0 else '') + repr(_cv.imag)
                    replacement = f'({repr(_cv.real)}{_im}j)'
                else:
                    raise ValueError("Math ERROR")

        s = s[:start] + replacement + s[close_idx + 1:]


def _transform_factorials(s: str, ans_val: float, angle_unit: str = "Degree", variables=None, complex_mode: bool = False, rnd_setting=None) -> str:
    """Resolve postfix '!' for arbitrary operands (not just bare digits).

    Supports 5!, (5)!, (3+2)!, (Ans)!, (pi)! and other valid calculator
    operands by evaluating the operand through the existing
    safe_evaluate_expression pipeline and splicing the integer result.
    Uses no eval(); invalid cases raise Math ERROR. Caps at 170 to match
    the FILE_MODE bridge overflow behavior.
    """
    while True:
        idx = s.find('!')
        if idx < 0:
            return s
        # '!=' is not part of the calculator grammar.
        if idx + 1 < len(s) and s[idx + 1] == '=':
            raise ValueError("Math ERROR")
        j = idx - 1
        while j >= 0 and s[j] == ' ':
            j -= 1
        if j < 0:
            raise ValueError("Math ERROR")
        if s[j] == ')':
            depth = 1
            k = j - 1
            while k >= 0:
                if s[k] == ')':
                    depth += 1
                elif s[k] == '(':
                    depth -= 1
                    if depth == 0:
                        break
                k -= 1
            if k < 0:
                raise ValueError("Math ERROR: unbalanced parentheses")
            operand = s[k:j + 1]
            start = k
        else:
            k = j
            while k >= 0 and (s[k].isalnum() or s[k] in '._'):
                k -= 1
            k += 1
            operand = s[k:j + 1]
            if not operand:
                raise ValueError("Math ERROR")
            start = k
        value = safe_evaluate_expression(operand, ans_val, angle_unit, variables, complex_mode, rnd_setting)
        if isinstance(value, complex):
            if abs(value.imag) > 1e-14:
                raise ValueError("Math ERROR")
            value = value.real
        if not float(value).is_integer() or value < 0:
            raise ValueError("Math ERROR")
        n = int(value)
        if n > 170:
            raise ValueError("Math ERROR")
        replacement = _lit(math.factorial(n))
        s = s[:start] + replacement + s[idx + 1:]


def _transform_random(s: str) -> str:
    """Splice keypad random tokens to concrete values (no eval()).

    'Ran#' / 'rand()' -> uniform [0, 1). 'RanInt(' is a real function call
    handled by _transform_special_functions.
    """
    s = re.sub(r'Ran#', lambda _m: _lit(random.random()), s)
    s = re.sub(r'(?<![A-Za-z0-9_])rand\(\)', lambda _m: _lit(random.random()), s)
    return s


def _transform_dms(s: str, angle_unit: str = "Degree") -> str:
    """Convert DMS / angle-unit suffixes to plain numbers in the current unit.

    30°15′20″ -> decimal degrees; 30°15′ -> degrees; 30° -> 30.
    Digit+r/g suffixes (OPTN angle menu) convert radian/gradian values
    into the active angle unit. A lone 'x' variable is left untouched.
    """
    def _dms3(m):
        d = float(m.group(1))
        mag = abs(d) + float(m.group(2)) / 60.0 + float(m.group(3)) / 3600.0
        return _lit(-mag if d < 0 else mag)

    s = re.sub(
        r'(-?\d+(?:\.\d+)?)\s*°\s*(\d+(?:\.\d+)?)\s*′\s*(\d+(?:\.\d+)?)\s*″',
        _dms3, s)

    def _dms2(m):
        d = float(m.group(1))
        mag = abs(d) + float(m.group(2)) / 60.0
        return _lit(-mag if d < 0 else mag)

    s = re.sub(r'(-?\d+(?:\.\d+)?)\s*°\s*(\d+(?:\.\d+)?)\s*′', _dms2, s)
    s = re.sub(r'(-?\d+(?:\.\d+)?)\s*°', lambda m: _lit(float(m.group(1))), s)

    def _r_suffix(m):
        v = float(m.group(1))
        if angle_unit == "Degree":
            return _lit(v * 180.0 / math.pi)
        if angle_unit == "Gradian":
            return _lit(v * 200.0 / math.pi)
        return _lit(v)

    def _g_suffix(m):
        v = float(m.group(1))
        if angle_unit == "Degree":
            return _lit(v * 0.9)
        if angle_unit == "Radian":
            return _lit(v * math.pi / 200.0)
        return _lit(v)

    s = re.sub(r'(-?\d+(?:\.\d+)?)\s*r(?![A-Za-z0-9_])', _r_suffix, s)
    s = re.sub(r'(-?\d+(?:\.\d+)?)\s*g(?![A-Za-z0-9_])', _g_suffix, s)
    return s


def _find_infix_pc(s: str, start: int = 0):
    """Locate the next keypad infix P/C operator with parseable operands.

    Returns (op, l_start, l_end, r_start, r_end, op_index) or None.
    Skips letters that belong to identifiers (Pol, Rec, nPr, ...).
    """
    def match_paren_fwd(text: str, open_idx: int) -> int:
        depth = 0
        for k in range(open_idx, len(text)):
            if text[k] == '(':
                depth += 1
            elif text[k] == ')':
                depth -= 1
                if depth == 0:
                    return k
        return -1

    i = start
    while i < len(s):
        ch = s[i]
        if ch in ('P', 'C'):
            j = i - 1
            while j >= 0 and s[j] == ' ':
                j -= 1
            if j >= 0 and (s[j].isdigit() or s[j] in ').'):
                # Parse left operand (extend over a function-call name).
                if s[j] == ')':
                    depth = 1
                    k = j - 1
                    while k >= 0:
                        if s[k] == ')':
                            depth += 1
                        elif s[k] == '(':
                            depth -= 1
                            if depth == 0:
                                break
                        k -= 1
                    if k >= 0:
                        kk = k - 1
                        if kk >= 0 and (s[kk].isalnum() or s[kk] == '_'):
                            while kk >= 0 and (s[kk].isalnum() or s[kk] == '_'):
                                kk -= 1
                            k = kk + 1
                        l_start, l_end = k, j + 1
                        # Parse right operand.
                        m = i + 1
                        while m < len(s) and s[m] == ' ':
                            m += 1
                        if m < len(s) and (s[m].isdigit() or s[m] in '.(' or s[m].isalpha()):
                            if s[m] == '(':
                                close = match_paren_fwd(s, m)
                                if close >= 0:
                                    return (ch, l_start, l_end, m, close + 1, i)
                            else:
                                n = m
                                while n < len(s) and (s[n].isalnum() or s[n] in '._'):
                                    n += 1
                                if n < len(s) and s[n] == '(':
                                    close = match_paren_fwd(s, n)
                                    if close >= 0:
                                        return (ch, l_start, l_end, m, close + 1, i)
                                elif n > m:
                                    return (ch, l_start, l_end, m, n, i)
                else:
                    k = j
                    while k >= 0 and (s[k].isalnum() or s[k] in '._'):
                        k -= 1
                    k += 1
                    l_start, l_end = k, j + 1
                    m = i + 1
                    while m < len(s) and s[m] == ' ':
                        m += 1
                    if m < len(s) and (s[m].isdigit() or s[m] in '.(' or s[m].isalpha()):
                        if s[m] == '(':
                            close = match_paren_fwd(s, m)
                            if close >= 0:
                                return (ch, l_start, l_end, m, close + 1, i)
                        else:
                            n = m
                            while n < len(s) and (s[n].isalnum() or s[n] in '._'):
                                n += 1
                            if n < len(s) and s[n] == '(':
                                close = match_paren_fwd(s, n)
                                if close >= 0:
                                    return (ch, l_start, l_end, m, close + 1, i)
                            elif n > m:
                                return (ch, l_start, l_end, m, n, i)
        i += 1
    return None


def _transform_combinatorics_infix(s: str, ans_val: float, angle_unit: str = "Degree") -> str:
    """Rewrite keypad infix `n P r` / `n C r` to nPr()/nCr() calls.

    Handles bare digits as well as parenthesized / symbolic operands
    ((5)P(3+1), Ans P 2). Operands are validated through the existing
    safe pipeline; unparseable candidates are left for the tokenizer to
    reject as Math ERROR. Uses no eval().
    """
    pos = 0
    for _ in range(100):
        found = _find_infix_pc(s, pos)
        if found is None:
            return s
        op, l_start, l_end, r_start, r_end, op_idx = found
        left, right = s[l_start:l_end], s[r_start:r_end]
        try:
            safe_evaluate_expression(left, ans_val, angle_unit)
            safe_evaluate_expression(right, ans_val, angle_unit)
        except Exception:
            pos = op_idx + 1
            continue
        fn = 'nPr' if op == 'P' else 'nCr'
        s = s[:l_start] + f'{fn}({left},{right})' + s[r_end:]
        pos = 0
    return s


def _tokenize_complex(s: str):
    """Tokenize numbers (incl. Nj imaginary literals and bare j), ops, parens."""
    toks = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c == '*' and i + 1 < n and s[i + 1] == '*':
            toks.append('**')
            i += 2
            continue
        if c in '+-*/(),':
            toks.append(c)
            i += 1
            continue
        if c.isdigit() or c == '.':
            j = i
            while j < n and (s[j].isdigit() or s[j] == '.'):
                j += 1
            num = float(s[i:j])
            if j < n and s[j] == 'j':
                toks.append(complex(0, num))
                j += 1
            else:
                toks.append(num)
            i = j
            continue
        if c == 'j':
            toks.append(complex(0, 1))
            i += 1
            continue
        raise ValueError("Math ERROR")
    return toks


def _parse_complex(toks):
    """Recursive descent over +,-,*,/,**,parens,unary (complex-safe)."""
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def atom():
        tk = peek()
        if tk is None:
            raise ValueError("Math ERROR")
        if isinstance(tk, (int, float, complex)):
            pos[0] += 1
            return tk
        if tk == '(':
            pos[0] += 1
            v = addsub()
            if peek() != ')':
                raise ValueError("Math ERROR")
            pos[0] += 1
            return v
        raise ValueError("Math ERROR")

    def power():
        b = atom()
        if peek() == '**':
            pos[0] += 1
            ex = unary()
            try:
                return b ** ex
            except ZeroDivisionError:
                raise
            except Exception:
                raise ValueError("Math ERROR")
        return b

    def unary():
        if peek() == '-':
            pos[0] += 1
            return -unary()
        if peek() == '+':
            pos[0] += 1
            return unary()
        return power()

    def muldiv():
        l = unary()
        while peek() in ('*', '/'):
            op = peek()
            pos[0] += 1
            r = unary()
            if r == 0:
                raise ZeroDivisionError("division by zero")
            l = l * r if op == '*' else l / r
        return l

    def addsub():
        l = muldiv()
        while peek() in ('+', '-'):
            op = peek()
            pos[0] += 1
            r = muldiv()
            l = l + r if op == '+' else l - r
        return l

    v = addsub()
    if pos[0] != len(toks):
        raise ValueError("Math ERROR")
    return v


def safe_evaluate_expression(expr_str: str, ans_val: float = 0.0, angle_unit: str = "Degree", variables=None, complex_mode: bool = False, rnd_setting=None):
    """Evaluate mathematical expressions with scientific functions, roots, powers, and integrals."""
    s = expr_str.strip()
    if not s:
        return 0.0

    # Multi-statement separator (ALPHA+integral ':'): evaluate each part, return last.
    if ':' in s and '__BASE_SWITCH__' not in s:
        parts = [p for p in s.split(':') if p.strip() != '']
        if len(parts) > 1:
            result = 0.0
            for p in parts:
                result = safe_evaluate_expression(p, ans_val, angle_unit, variables)
                try:
                    ans_val = float(result) if not isinstance(result, complex) else ans_val
                except Exception:
                    pass
            return result

    # Replace display / shorthand symbols
    s = s.replace('π', f'({math.pi})').replace('pi', f'({math.pi})')
    s = s.replace('×', '*').replace('÷', '/').replace('−', '-')
    s = s.replace('Ans', f'({ans_val})').replace('ans', f'({ans_val})')
    # Standalone constant e (Euler). Word boundaries guard scientific
    # notation (1e10), function names and identifiers.
    s = re.sub(r'(?<![A-Za-z0-9_.])e(?![A-Za-z0-9_(])', f'({math.e})', s)
    # Standalone imaginary unit i (Complex mode ALPHA+ENG). Map to 1j for engine.
    s = re.sub(r'(?<![A-Za-z0-9_.])i(?![A-Za-z0-9_(])', '(1j)', s)

    # Calculator variables A-F, M, X, Y (STO/RECALL/ALPHA). Substitute values.
    if variables:
        for _vname in ('A', 'B', 'C', 'D', 'E', 'F', 'M', 'X', 'Y'):
            if _vname in variables:
                try:
                    _vval = float(variables[_vname])
                except Exception:
                    continue
                s = re.sub(rf'\b{_vname}\b', _lit(_vval), s)

    # Keypad aliases: frontend display tokens -> backend function names.
    s = s.replace('Σ(', 'sigma(').replace('d/dx(', 'diff(')
    s = re.sub(r'(?<![A-Za-z0-9_])Rnd\(', 'round(', s)
    # Random tokens with no argument list.
    s = _transform_random(s)
    # DMS / angle-unit suffixes -> plain numbers in the active unit.
    s = _transform_dms(s, angle_unit)
    # Casio postfix % -> /100.
    s = _transform_percent(s)
    # Keypad infix combinatorics: 5P2, (5)P(3+1), Ans P 2, ...
    s = _transform_combinatorics_infix(s, ans_val, angle_unit)

    # Powers ^ -> ** (must run BEFORE special functions so recursive
    # calls inside _transform_special_functions see '**', not '^')
    s = s.replace('^', '**')

    # Handle supported special functions (integral, log_base, xroot, cbrt, sqrt)
    s = _transform_special_functions(s, ans_val, angle_unit, variables, complex_mode, rnd_setting)
    if '__FACT__' in s:
        m = re.search(r'__FACT__(\d+)__', s)
        if m:
            return _prime_factorization_str(int(m.group(1)))  # type: ignore[return-value]
        raise ValueError("Math ERROR")

    # Factorials: postfix '!' over arbitrary operands (5!, (5)!, (3+2)!,
    # (Ans)!, (pi)!). Precomputed via the safe pipeline; no eval().
    s = _transform_factorials(s, ans_val, angle_unit, variables, complex_mode, rnd_setting)

    # Angle conversion functions
    if angle_unit == "Radian":
        to_rad = lambda x: x
        from_rad = lambda x: x
    elif angle_unit == "Gradian":
        to_rad = lambda x: x * (math.pi / 200.0)
        from_rad = lambda x: x * (200.0 / math.pi)
    else:  # Degree (default)
        to_rad = lambda x: x * (math.pi / 180.0)
        from_rad = lambda x: x * (180.0 / math.pi)

    def _safe_sin(x):
        if isinstance(x, (int, float)):
            if angle_unit == "Degree" and x % 180 == 0:
                return 0.0
            if angle_unit == "Gradian" and x % 200 == 0:
                return 0.0
            res = cmath.sin(to_rad(x))
            if abs(res.imag) < 1e-14:
                return float(res.real)
            return res
        return cmath.sin(to_rad(x))

    def _safe_cos(x):
        if isinstance(x, (int, float)):
            if angle_unit == "Degree" and (x - 90) % 180 == 0:
                return 0.0
            if angle_unit == "Gradian" and (x - 100) % 200 == 0:
                return 0.0
            res = cmath.cos(to_rad(x))
            if abs(res.imag) < 1e-14:
                return float(res.real)
            return res
        return cmath.cos(to_rad(x))

    def _safe_tan(x):
        rad = to_rad(x)
        c = cmath.cos(rad)
        if abs(c) < 1e-12:
            raise ValueError("Math ERROR")
        if isinstance(x, (int, float)):
            if angle_unit == "Degree" and x % 180 == 0:
                return 0.0
            if angle_unit == "Gradian" and x % 200 == 0:
                return 0.0
            res = cmath.tan(rad)
            if abs(res.imag) < 1e-14:
                return float(res.real)
            return res
        return cmath.tan(rad)

    def _safe_asin(x):
        res = cmath.asin(x)
        converted = from_rad(res)
        if isinstance(x, (int, float)) and abs(x) <= 1:
            return float(converted.real)
        return converted

    def _safe_acos(x):
        res = cmath.acos(x)
        converted = from_rad(res)
        if isinstance(x, (int, float)) and abs(x) <= 1:
            return float(converted.real)
        return converted

    def _safe_atan(x):
        res = cmath.atan(x)
        converted = from_rad(res)
        if isinstance(x, (int, float)):
            return float(converted.real)
        return converted

    # Second pass: catch any trig calls revealed by earlier substitutions
    # (e.g. after Ans/pi substitution exposes a new sin(...) call) so trig
    # always routes through the angle-aware path.
    s = _transform_special_functions(s, ans_val, angle_unit, variables, complex_mode, rnd_setting)

    if 'j' in s:
        try:
            cval = _parse_complex(_tokenize_complex(s))
            if isinstance(cval, complex) and abs(cval.imag) < 1e-14:
                return float(cval.real)
            return cval
        except ZeroDivisionError:
            raise
        except Exception as exc:
            raise ValueError(f"Math ERROR: {exc}") from exc
    try:
        val = evaluate(parse(tokenize(s)))
        if isinstance(val, complex):
            if abs(val.imag) < 1e-14:
                return float(val.real)
            return val
        return float(val)
    except ZeroDivisionError:
        raise
    except Exception as exc:
        raise ValueError(f"Math ERROR: {exc}") from exc


def evaluate_base_n(expr_str: str, base: int) -> str:
    """Evaluate expression in a given base (2, 8, 10, 16) and return result in that base."""
    # Replace display symbols
    s = expr_str.replace('×', '*').replace('÷', '/').replace('−', '-')

    # Convert digit sequences from the given base to decimal
    def _base_to_dec(m):
        return str(int(m.group(), base))

    s = re.sub(r'[0-9A-Fa-f]+', _base_to_dec, s)

    # Evaluate in decimal
    result = safe_evaluate_expression(s, 0.0)

    # Convert result back to target base
    if isinstance(result, complex):
        if result.imag != 0:
            raise ValueError("Math ERROR")
        result = result.real

    int_result = int(result)

    # Preserve the sign: bin()/oct()/hex() render negatives as '-0b101',
    # so slicing [2:] would strip '-0' and corrupt the output. Format the
    # magnitude and re-attach the sign instead.
    sign = "-" if int_result < 0 else ""
    magnitude = abs(int_result)

    if base == 2:
        return f"{sign}{bin(magnitude)[2:]}"
    elif base == 8:
        return f"{sign}{oct(magnitude)[2:]}"
    elif base == 16:
        return f"{sign}{hex(magnitude)[2:].upper()}"
    else:
        return str(int_result)


# ── DISTRIBUTION MATH HELPERS ───────────────────────────────────────────────

def _dist_normal_pdf(x: float, mu: float, sigma: float) -> float:
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))


def _dist_normal_cdf(x: float, mu: float, sigma: float) -> float:
    z = (x - mu) / (sigma * math.sqrt(2))
    return 0.5 * math.erfc(-z)


def _dist_inverse_normal(area: float, mu: float, sigma: float) -> float:
    """Rational approximation for the inverse normal CDF (percent-point function)."""
    if area <= 0 or area >= 1:
        raise ValueError("Area must be strictly between 0 and 1")
    p = area
    p_low = 0.02425
    p_high = 1 - p_low
    a = [0, -3.969683028665376e+01,  2.209460984245205e+02,
            -2.759285104469687e+02,  1.383577518672690e+02,
            -3.066479806614716e+01,  2.506628277459239e+00]
    b = [0, -5.447609879822406e+01,  1.615858368580409e+02,
            -1.556989798598866e+02,  6.680131188771972e+01,
            -1.328068155288572e+01]
    c = [0, -7.784894002430293e-03, -3.223964580411365e-01,
            -2.400758277161838e+00, -2.549732539343734e+00,
             4.374664141464968e+00,  2.938163982698783e+00]
    d = [0,  7.784695709041462e-03,  3.224671290700398e-01,
             2.445134137142996e+00,  3.754408661907416e+00]
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        z = (((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) / \
            ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        z = (((((a[1]*r+a[2])*r+a[3])*r+a[4])*r+a[5])*r+a[6])*q / \
            (((((b[1]*r+b[2])*r+b[3])*r+b[4])*r+b[5])*r+1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        z = -(((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) / \
              ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)
    return mu + sigma * z


def _dist_binomial_pd(x: int, n: int, p: float) -> float:
    x, n = int(x), int(n)
    if x < 0 or x > n or n < 0 or not (0 <= p <= 1):
        raise ValueError("Invalid Binomial PD parameters")
    from math import comb
    return comb(n, x) * (p ** x) * ((1 - p) ** (n - x))


def _dist_binomial_cd(x: int, n: int, p: float) -> float:
    return sum(_dist_binomial_pd(k, n, p) for k in range(int(x) + 1))


def _dist_poisson_pd(x: int, lam: float) -> float:
    x = int(x)
    if x < 0 or lam < 0:
        raise ValueError("Invalid Poisson parameters")
    if lam == 0:
        return 1.0 if x == 0 else 0.0
    return (lam ** x) * math.exp(-lam) / math.factorial(x)


def _dist_poisson_cd(x: int, lam: float) -> float:
    return sum(_dist_poisson_pd(k, lam) for k in range(int(x) + 1))


# ── SCIENTIFIC CONSTANTS DATA (47 CODATA Constants) ─────────────────────────

SCIENTIFIC_CONSTANTS = [
    # Universal (7)
    {"key": "c0", "name": "c0", "symbol": "c₀", "unit": "m/s", "category": "Universal", "value": 299792458.0},
    {"key": "mu0", "name": "mu0", "symbol": "μ₀", "unit": "N/A²", "category": "Universal", "value": 1.25663706212e-6},
    {"key": "eps0", "name": "eps0", "symbol": "ε₀", "unit": "F/m", "category": "Universal", "value": 8.8541878128e-12},
    {"key": "Z0", "name": "Z0", "symbol": "Z₀", "unit": "Ω", "category": "Universal", "value": 376.730313668},
    {"key": "h", "name": "h", "symbol": "h", "unit": "J·s", "category": "Universal", "value": 6.62607015e-34},
    {"key": "hbar", "name": "hbar", "symbol": "ℏ", "unit": "J·s", "category": "Universal", "value": 1.054571817e-34},
    {"key": "G", "name": "G", "symbol": "G", "unit": "m³/(kg·s²)", "category": "Universal", "value": 6.67430e-11},

    # Electromagnetic (7)
    {"key": "e", "name": "e", "symbol": "e", "unit": "C", "category": "Electromagnetic", "value": 1.602176634e-19},
    {"key": "Phi0", "name": "Phi0", "symbol": "Φ₀", "unit": "Wb", "category": "Electromagnetic", "value": 2.067833848e-15},
    {"key": "G0", "name": "G0", "symbol": "G₀", "unit": "S", "category": "Electromagnetic", "value": 7.748091729e-5},
    {"key": "KJ", "name": "K_J", "symbol": "K_J", "unit": "Hz/V", "category": "Electromagnetic", "value": 483597.8484e9},
    {"key": "RK", "name": "R_K", "symbol": "R_K", "unit": "Ω", "category": "Electromagnetic", "value": 25812.80745},
    {"key": "muB", "name": "mu_B", "symbol": "μ_B", "unit": "J/T", "category": "Electromagnetic", "value": 9.2740100783e-24},
    {"key": "muN", "name": "mu_N", "symbol": "μ_N", "unit": "J/T", "category": "Electromagnetic", "value": 5.0507837461e-27},

    # Atomic & Nuclear (11)
    {"key": "mp", "name": "m_p", "symbol": "m_p", "unit": "kg", "category": "Atomic & Nuclear", "value": 1.67262192369e-27},
    {"key": "mn", "name": "m_n", "symbol": "m_n", "unit": "kg", "category": "Atomic & Nuclear", "value": 1.67492749804e-27},
    {"key": "me", "name": "m_e", "symbol": "m_e", "unit": "kg", "category": "Atomic & Nuclear", "value": 9.1093837015e-31},
    {"key": "mmu", "name": "m_mu", "symbol": "m_μ", "unit": "kg", "category": "Atomic & Nuclear", "value": 1.883531627e-28},
    {"key": "a0", "name": "a0", "symbol": "a₀", "unit": "m", "category": "Atomic & Nuclear", "value": 5.29177210903e-11},
    {"key": "alpha", "name": "alpha", "symbol": "α", "unit": "", "category": "Atomic & Nuclear", "value": 7.2973525693e-3},
    {"key": "re", "name": "r_e", "symbol": "r_e", "unit": "m", "category": "Atomic & Nuclear", "value": 2.8179403262e-15},
    {"key": "lambdaC", "name": "lambda_C", "symbol": "λ_C", "unit": "m", "category": "Atomic & Nuclear", "value": 2.42631023867e-12},
    {"key": "gammap", "name": "gamma_p", "symbol": "γ_p", "unit": "rad/(s·T)", "category": "Atomic & Nuclear", "value": 2.6752218744e8},
    {"key": "lambdaCn", "name": "lambda_Cn", "symbol": "λ_Cn", "unit": "m", "category": "Atomic & Nuclear", "value": 1.31959090581e-15},
    {"key": "lambdaCp", "name": "lambda_Cp", "symbol": "λ_Cp", "unit": "m", "category": "Atomic & Nuclear", "value": 1.32140985539e-15},

    # Physico-Chem (9)
    {"key": "u", "name": "u", "symbol": "u", "unit": "kg", "category": "Physico-Chem", "value": 1.66053906660e-27},
    {"key": "F", "name": "F", "symbol": "F", "unit": "C/mol", "category": "Physico-Chem", "value": 96485.33212},
    {"key": "NA", "name": "N_A", "symbol": "N_A", "unit": "mol⁻¹", "category": "Physico-Chem", "value": 6.02214076e23},
    {"key": "k", "name": "k", "symbol": "k", "unit": "J/K", "category": "Physico-Chem", "value": 1.380649e-23},
    {"key": "R", "name": "R", "symbol": "R", "unit": "J/(mol·K)", "category": "Physico-Chem", "value": 8.314462618},
    {"key": "sigma", "name": "sigma", "symbol": "σ", "unit": "W/(m²·K⁴)", "category": "Physico-Chem", "value": 5.670374419e-8},
    {"key": "C1", "name": "c1", "symbol": "c₁", "unit": "W·m²", "category": "Physico-Chem", "value": 3.741771852e-16},
    {"key": "C2", "name": "c2", "symbol": "c₂", "unit": "m·K", "category": "Physico-Chem", "value": 1.438776877e-2},
    {"key": "b", "name": "b", "symbol": "b", "unit": "m·K", "category": "Physico-Chem", "value": 2.897771955e-3},

    # Adopted Values (6)
    {"key": "g_n", "name": "g", "symbol": "g", "unit": "m/s²", "category": "Adopted Values", "value": 9.80665},
    {"key": "atm", "name": "atm", "symbol": "atm", "unit": "Pa", "category": "Adopted Values", "value": 101325.0},
    {"key": "RK90", "name": "R_K90", "symbol": "R_K-90", "unit": "Ω", "category": "Adopted Values", "value": 25812.807},
    {"key": "KJ90", "name": "K_J90", "symbol": "K_J-90", "unit": "Hz/V", "category": "Adopted Values", "value": 483597.9e9},
    {"key": "t", "name": "t", "symbol": "t", "unit": "K", "category": "Adopted Values", "value": 273.15},
    {"key": "cal15", "name": "cal15", "symbol": "cal₁₅", "unit": "J", "category": "Adopted Values", "value": 4.18580},

    # Other (7)
    {"key": "Rinf", "name": "R_inf", "symbol": "R_∞", "unit": "m⁻¹", "category": "Other", "value": 10973731.568160},
    {"key": "mu_e", "name": "mu_e", "symbol": "μ_e", "unit": "J/T", "category": "Other", "value": -9.2847647043e-24},
    {"key": "mu_p", "name": "mu_p", "symbol": "μ_p", "unit": "J/T", "category": "Other", "value": 1.41060679736e-26},
    {"key": "mu_n", "name": "mu_n", "symbol": "μ_n", "unit": "J/T", "category": "Other", "value": -9.6623651e-27},
    {"key": "mu_mu", "name": "mu_mu", "symbol": "μ_μ", "unit": "J/T", "category": "Other", "value": -4.49044830e-26},
    {"key": "Vm", "name": "V_m", "symbol": "V_m", "unit": "m³/mol", "category": "Other", "value": 22.41396954e-3},
    {"key": "u_chem", "name": "u_chem", "symbol": "u_chem", "unit": "kg", "category": "Other", "value": 1.66053906660e-27},
]


# ── UNIT CONVERSIONS DATA ───────────────────────────────────────────────────

UNIT_CONVERSIONS = {
    "Length": {
        "m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001,
        "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mile": 1609.344, "nmile": 1852.0
    },
    "Area": {
        "m2": 1.0, "km2": 1e6, "cm2": 1e-4, "mm2": 1e-6,
        "in2": 0.00064516, "ft2": 0.09290304, "yd2": 0.83612736,
        "acre": 4046.8564224, "ha": 10000.0,
        "m²": 1.0, "km²": 1e6, "cm²": 1e-4, "mm²": 1e-6,
        "in²": 0.00064516, "ft²": 0.09290304, "yd²": 0.83612736,
    },
    "Volume": {
        "m3": 1.0, "cm3": 1e-6, "L": 0.001, "mL": 1e-6,
        "in3": 1.6387064e-5, "ft3": 0.028316846592,
        "galUS": 0.003785411784, "galUK": 0.00454609,
        "gal(US)": 0.003785411784, "gal(UK)": 0.00454609,
        "m³": 1.0, "cm³": 1e-6, "in³": 1.6387064e-5, "ft³": 0.028316846592,
    },
    "Mass": {
        "kg": 1.0, "g": 0.001, "mg": 1e-6,
        "lb": 0.45359237, "oz": 0.028349523125
    },
    "Velocity": {
        "ms": 1.0, "m/s": 1.0, "kmh": 1.0 / 3.6, "km/h": 1.0 / 3.6,
        "mph": 0.44704, "kn": 1852.0 / 3600.0
    },
    "Pressure": {
        "Pa": 1.0, "kPa": 1000.0, "MPa": 1e6, "bar": 1e5,
        "atm": 101325.0, "mmHg": 133.322387415, "psi": 6894.757293168
    },
    "Power": {
        "W": 1.0, "kW": 1000.0, "MW": 1e6, "hp": 745.699872
    },
}


def _convert_units(category: str, from_u: str, to_u: str, value: float) -> float:
    if category == "Temperature":
        f = from_u.replace("°", "").strip()
        t = to_u.replace("°", "").strip()
        # to Celsius
        if f == "C":
            c = value
        elif f == "F":
            c = (value - 32.0) * 5.0 / 9.0
        elif f == "K":
            c = value - 273.15
        else:
            raise ValueError(f"Unknown temperature unit: {from_u}")
        # from Celsius
        if t == "C":
            return c
        elif t == "F":
            return c * 9.0 / 5.0 + 32.0
        elif t == "K":
            return c + 273.15
        else:
            raise ValueError(f"Unknown temperature unit: {to_u}")

    cat = UNIT_CONVERSIONS.get(category)
    if not cat:
        raise ValueError(f"Unknown conversion category: {category}")
    if from_u not in cat:
        raise ValueError(f"Unknown source unit: {from_u}")
    if to_u not in cat:
        raise ValueError(f"Unknown target unit: {to_u}")
    base_val = value * cat[from_u]
    return base_val / cat[to_u]


def _solve_ratio(ratio_type: int, a: float, b: float, c_or_d: float) -> float:
    if ratio_type == 1:  # A : B = X : D -> X = (A * D) / B
        if b == 0:
            raise ZeroDivisionError("Math ERROR")
        return (a * c_or_d) / b
    elif ratio_type == 2:  # A : B = C : X -> X = (B * C) / A
        if a == 0:
            raise ZeroDivisionError("Math ERROR")
        return (b * c_or_d) / a
    else:
        raise ValueError("Invalid ratio type. Must be 1 or 2.")



# ── MATRIX / VECTOR EXPRESSION SUPPORT (fx-991EX Matrix & Vector modes) ──────
# Official ops: MatA-D (<=4x4): + - * scalar* Det( Trn( Identity( inverse(^-1)
# powers(^2 ^3) Abs(elementwise). VctA-D: + - scalar* Dot(,) Angle(,) UnitV(
# Abs(magnitude) cross via *. Dimension mismatches -> "Dimension ERROR",
# singular/undefined -> "Math ERROR". Dedicated typed parser (NOT scalar hack).

_MAT_REF_RE = r'Mat[ABCD]'
_VCT_REF_RE = r'Vct[ABCD]'
_MAT_FUNCS = ('Det', 'Trn', 'Identity', 'Dot', 'Angle', 'UnitV', 'Abs')


def _contains_matvec(s: str) -> bool:
    return bool(re.search(r'\b(?:Mat[ABCD]|Vct[ABCD]|Det|Trn|Identity|Dot|Angle|UnitV)\b', s))


def _format_matrix_canonical(mat, fmt) -> str:
    return '[' + ','.join(
        '[' + ','.join(fmt(v) for v in row) + ']' for row in mat) + ']'


def _format_vector_canonical(vec, fmt) -> str:
    return '[' + ','.join(fmt(v) for v in vec) + ']'


def _parse_matrix_literal(s: str, pos: int):
    """Parse canonical [[a,b],[c,d]] at pos. Returns (matrix, new_pos)."""
    assert s[pos:pos + 2] == '[['
    rows = []
    i = pos + 1
    n = len(s)
    while True:
        assert s[i] == '['
        j = s.find(']', i)
        if j < 0:
            raise ValueError("Math ERROR")
        row = [float(x) for x in s[i + 1:j].split(',') if x.strip() != '']
        rows.append(row)
        i = j + 1
        if i < n and s[i] == ',':
            i += 1
            continue
        if i < n and s[i] == ']':
            return rows, i + 1
        raise ValueError("Math ERROR")


def _parse_vector_literal(s: str, pos: int):
    """Parse canonical [a,b,c] (single brackets) at pos."""
    j = s.find(']', pos)
    if j < 0:
        raise ValueError("Math ERROR")
    return [float(x) for x in s[pos + 1:j].split(',') if x.strip() != ''], j + 1


class _MVParser:
    """Typed recursive-descent parser for matrix/vector expressions."""

    def __init__(self, s, matrices, vectors, angle_unit, eval_scalar):
        self.s = s
        self.n = len(s)
        self.pos = 0
        self.matrices = matrices
        self.vectors = vectors
        self.angle_unit = angle_unit
        self.eval_scalar = eval_scalar

    def _dim_error(self):
        raise ValueError("Dimension ERROR")

    def peek(self):
        return self.s[self.pos] if self.pos < self.n else None

    def eat(self, ch):
        assert self.peek() == ch
        self.pos += 1

    def parse(self):
        kind, val = self.parse_expr()
        if self.pos != self.n:
            raise ValueError("Math ERROR")
        return kind, val

    def parse_expr(self):
        kind, val = self.parse_term()
        while self.peek() in ('+', '-'):
            op = self.peek()
            self.pos += 1
            k2, v2 = self.parse_term()
            kind, val = self.apply_add(kind, val, op, k2, v2)
        return kind, val

    def parse_term(self):
        kind, val = self.parse_factor()
        while self.peek() in ('*', '/', '×', '÷'):
            op = self.peek()
            self.pos += 1
            k2, v2 = self.parse_factor()
            kind, val = self.apply_mul(kind, val, op, k2, v2)
        return kind, val

    def parse_factor(self):
        kind, val = self.parse_unary()
        if self.peek() == '^':
            self.pos += 1
            if self.peek() == '*':
                self.pos += 1
            k2, v2 = self.parse_unary()
            kind, val = self.apply_pow(kind, val, k2, v2)
        return kind, val

    def parse_unary(self):
        if self.peek() == '-':
            self.pos += 1
            kind, val = self.parse_unary()
            if kind == 's':
                return 's', -val
            if kind == 'm':
                return 'm', [[-x for x in row] for row in val]
            return 'v', [-x for x in val]
        if self.peek() == '+':
            self.pos += 1
            return self.parse_unary()
        return self.parse_primary()

    def parse_primary(self):
        c = self.peek()
        if c is None:
            raise ValueError("Math ERROR")
        if c == '(':
            self.pos += 1
            kind, val = self.parse_expr()
            if self.peek() != ')':
                raise ValueError("Math ERROR")
            self.pos += 1
            return kind, val
        if c == '[':
            if self.s[self.pos:self.pos + 2] == '[[':
                mat, npos = _parse_matrix_literal(self.s, self.pos)
                self.pos = npos
                return 'm', mat
            vec, npos = _parse_vector_literal(self.s, self.pos)
            self.pos = npos
            return 'v', vec
        if c.isdigit() or c == '.':
            return self.parse_number()
        if c.isalpha() or c == '_':
            return self.parse_named()
        raise ValueError("Math ERROR")

    def parse_number(self):
        j = self.pos
        while j < self.n and (self.s[j].isdigit() or self.s[j] == '.'):
            j += 1
        try:
            v = float(self.s[self.pos:j])
        except ValueError:
            raise ValueError("Math ERROR")
        self.pos = j
        return 's', v

    def parse_named(self):
        j = self.pos
        while j < self.n and (self.s[j].isalnum() or self.s[j] == '_'):
            j += 1
        name = self.s[self.pos:j]
        self.pos = j
        if re.fullmatch(r'Mat[ABCD]', name):
            return 'm', self.get_matrix(name[-1])
        if re.fullmatch(r'Vct[ABCD]', name):
            return 'v', self.get_vector(name[-1])
        if self.peek() == '(':
            self.pos += 1
            args = self.parse_arg_list()
            if self.peek() != ')':
                raise ValueError("Math ERROR")
            self.pos += 1
            return self.apply_func(name, args)
        raise ValueError("Math ERROR")

    def parse_arg_list(self):
        args = []
        if self.peek() == ')':
            return args
        while True:
            args.append(self.parse_expr())
            if self.peek() == ',':
                self.pos += 1
                continue
            return args

    def get_matrix(self, letter):
        m = self.matrices.get(letter)
        if not m or not m.get("data") or m.get("rows", 0) <= 0:
            raise ValueError("Math ERROR")
        return [[float(x) for x in row] for row in m["data"]]

    def get_vector(self, letter):
        v = self.vectors.get(letter)
        if not v or not v.get("data") or v.get("dim", 0) <= 0:
            raise ValueError("Math ERROR")
        return [float(x) for x in v["data"]]

    def to_angle(self, radians):
        if self.angle_unit == "Radian":
            return radians
        if self.angle_unit == "Gradian":
            return radians * (200.0 / math.pi)
        return radians * (180.0 / math.pi)

    def apply_func(self, name, args):
        from engine.matrix.matrix_engine import MatrixEngine
        if name == 'Det':
            if len(args) != 1 or args[0][0] != 'm':
                raise ValueError("Math ERROR")
            mat = args[0][1]
            if len(mat) != len(mat[0]):
                self._dim_error()
            from engine.matrix.matrix_engine import MatrixEngineError
            try:
                eng = MatrixEngine()
                eng.define_matrix("MatA", mat)
                return 's', float(eng.determinant("MatA"))
            except MatrixEngineError as exc:
                if "Dimension" in str(exc):
                    self._dim_error()
                raise ValueError("Math ERROR")
        if name == 'Trn':
            if len(args) != 1 or args[0][0] != 'm':
                raise ValueError("Math ERROR")
            mat = args[0][1]
            return 'm', [[mat[i][j] for i in range(len(mat))] for j in range(len(mat[0]))]
        if name == 'Identity':
            if len(args) != 1 or args[0][0] != 's':
                raise ValueError("Math ERROR")
            nv = args[0][1]
            if not float(nv).is_integer() or not 1 <= int(nv) <= 4:
                raise ValueError("Math ERROR")
            n = int(nv)
            return 'm', [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        if name == 'Abs':
            if len(args) != 1:
                raise ValueError("Math ERROR")
            k, v = args[0]
            if k == 's':
                return 's', abs(v)
            if k == 'm':
                return 'm', [[abs(x) for x in row] for row in v]
            return 's', math.sqrt(sum(x * x for x in v))
        if name == 'Dot':
            if len(args) != 2 or args[0][0] != 'v' or args[1][0] != 'v':
                raise ValueError("Math ERROR")
            a, b = args[0][1], args[1][1]
            if len(a) != len(b):
                self._dim_error()
            return 's', float(sum(x * y for x, y in zip(a, b)))
        if name == 'Angle':
            if len(args) != 2 or args[0][0] != 'v' or args[1][0] != 'v':
                raise ValueError("Math ERROR")
            a, b = args[0][1], args[1][1]
            if len(a) != len(b):
                self._dim_error()
            ma = math.sqrt(sum(x * x for x in a))
            mb = math.sqrt(sum(x * x for x in b))
            if ma == 0 or mb == 0:
                raise ValueError("Math ERROR")
            ratio = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (ma * mb)))
            return 's', self.to_angle(math.acos(ratio))
        if name == 'UnitV':
            if len(args) != 1 or args[0][0] != 'v':
                raise ValueError("Math ERROR")
            v = args[0][1]
            m = math.sqrt(sum(x * x for x in v))
            if m == 0:
                raise ValueError("Math ERROR")
            return 'v', [x / m for x in v]
        raise ValueError("Math ERROR")

    def apply_add(self, k1, v1, op, k2, v2):
        if k1 == 's' and k2 == 's':
            return 's', v1 + v2 if op == '+' else v1 - v2
        if k1 == 'm' and k2 == 'm':
            if len(v1) != len(v2) or len(v1[0]) != len(v2[0]):
                self._dim_error()
            if op == '+':
                return 'm', [[a + b for a, b in zip(r1, r2)] for r1, r2 in zip(v1, v2)]
            return 'm', [[a - b for a, b in zip(r1, r2)] for r1, r2 in zip(v1, v2)]
        if k1 == 'v' and k2 == 'v':
            if len(v1) != len(v2):
                self._dim_error()
            if op == '+':
                return 'v', [a + b for a, b in zip(v1, v2)]
            return 'v', [a - b for a, b in zip(v1, v2)]
        self._dim_error()

    def apply_mul(self, k1, v1, op, k2, v2):
        if op in ('/', '÷'):
            if k1 == 's' and k2 == 's':
                if v2 == 0:
                    raise ZeroDivisionError("division by zero")
                return 's', v1 / v2
            raise ValueError("Math ERROR")
        if k1 == 's' and k2 == 's':
            return 's', v1 * v2
        if k1 == 's' and k2 == 'm':
            return 'm', [[v1 * x for x in row] for row in v2]
        if k1 == 'm' and k2 == 's':
            return 'm', [[x * v2 for x in row] for row in v1]
        if k1 == 's' and k2 == 'v':
            return 'v', [v1 * x for x in v2]
        if k1 == 'v' and k2 == 's':
            return 'v', [x * v2 for x in v1]
        if k1 == 'm' and k2 == 'm':
            if len(v1[0]) != len(v2):
                self._dim_error()
            inner = len(v1[0])
            return 'm', [[sum(v1[i][k] * v2[k][j] for k in range(inner))
                          for j in range(len(v2[0]))] for i in range(len(v1))]
        if k1 == 'v' and k2 == 'v':
            if len(v1) != 3 or len(v2) != 3:
                self._dim_error()
            ax, ay, az = v1
            bx, by, bz = v2
            return 'v', [ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx]
        self._dim_error()

    def apply_pow(self, k1, v1, k2, v2):
        if k2 != 's' or not float(v2).is_integer():
            raise ValueError("Math ERROR")
        e = int(v2)
        if k1 == 's':
            if v1 < 0 and e != v2:
                raise ValueError("Math ERROR")
            try:
                return 's', v1 ** e
            except ZeroDivisionError:
                raise
            except Exception:
                raise ValueError("Math ERROR")
        if k1 == 'm':
            n = len(v1)
            if len(v1[0]) != n:
                self._dim_error()
            if e == -1:
                from engine.matrix.matrix_engine import MatrixEngine, MatrixEngineError
                try:
                    eng = MatrixEngine()
                    eng.define_matrix("MatA", v1)
                    return 'm', eng.inverse("MatA")
                except MatrixEngineError as exc:
                    if "Dimension" in str(exc):
                        self._dim_error()
                    raise ValueError("Math ERROR")
            if e < 0:
                raise ValueError("Math ERROR")
            from engine.matrix.matrix_engine import MatrixEngine
            eng = MatrixEngine()
            eng.define_matrix("MatA", v1)
            eng.define_matrix("MatB", [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)])
            res = eng.get_matrix("MatB")
            base = v1
            exp = e
            while exp > 0:
                if exp % 2 == 1:
                    eng.define_matrix("MatA", res)
                    eng.define_matrix("MatB", base)
                    res = eng.multiply("MatA", "MatB")
                exp //= 2
                if exp:
                    eng.define_matrix("MatA", base)
                    eng.define_matrix("MatB", base)
                    base = eng.multiply("MatA", "MatB")
            return 'm', res
        raise ValueError("Math ERROR")


def _resolve_matvec_funcs(s, matrices, vectors, angle_unit, eval_scalar):
    """Innermost-first resolution of Det/Trn/Identity/Dot/Angle/UnitV/Abs-with-
    matrix-or-vector-arg calls, splicing canonical literals. Pure-scalar Abs()
    is left for the scalar evaluator."""
    out = s
    for _ in range(50):
        found = None
        for name in ('Det', 'Trn', 'Identity', 'Dot', 'Angle', 'UnitV', 'Abs'):
            pos = 0
            while True:
                idx = out.find(name, pos)
                if idx < 0:
                    break
                end = idx + len(name)
                ok = (idx == 0 or not (out[idx - 1].isalnum() or out[idx - 1] == '_'))
                if ok and end < len(out) and out[end] == '(':
                    if found is None or idx < found[1]:
                        found = (name, idx)
                pos = end
        if found is None:
            return out
        name, start = found
        open_idx = start + len(name)
        close_idx = _find_matching_paren(out, open_idx)
        if close_idx < 0:
            raise ValueError("Math ERROR: unbalanced parentheses")
        inner = out[open_idx + 1:close_idx]
        args = _split_top_level_args(inner)
        parser = _MVParser('', matrices, vectors, angle_unit, eval_scalar)
        kind, val = parser.apply_func(name, [parser_arg_eval(a, matrices, vectors, angle_unit, eval_scalar) for a in args])
        if kind == 's':
            if isinstance(val, complex):
                raise ValueError("Math ERROR")
            replacement = _lit(val)
        elif kind == 'm':
            replacement = _format_matrix_canonical(val, lambda v: repr(float(v)))
        else:
            replacement = _format_vector_canonical(val, lambda v: repr(float(v)))
        out = out[:start] + replacement + out[close_idx + 1:]
    return out


def _split_matvec_atoms(s):
    """Split into (is_atom, text) runs. Atoms are Mat/Vct refs or balanced
    [...] literals (matrix [[..]] or vector [..]); everything else is a
    scalar chunk. Unbalanced brackets -> Math ERROR."""
    parts = []
    buf = []

    def flush():
        if buf:
            parts.append((False, ''.join(buf)))
            buf.clear()

    i, n = 0, len(s)
    while i < n:
        m = re.match(r'Mat[ABCD]\b|Vct[ABCD]\b', s[i:])
        if m and (i == 0 or not (s[i - 1].isalnum() or s[i - 1] == '_')):
            flush()
            parts.append((True, m.group()))
            i += len(m.group())
            continue
        if s[i] == '[':
            depth = 0
            j = i
            while j < n:
                if s[j] == '[':
                    depth += 1
                elif s[j] == ']':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if depth != 0:
                raise ValueError("Math ERROR")
            flush()
            parts.append((True, s[i:j + 1]))
            i = j + 1
            continue
        buf.append(s[i])
        i += 1
    flush()
    return parts


def parser_arg_eval(arg, matrices, vectors, angle_unit, eval_scalar):
    arg = arg.strip()
    if not arg:
        raise ValueError("Math ERROR")
    if not _contains_matvec(arg):
        v = eval_scalar(arg)
        if isinstance(v, complex):
            raise ValueError("Math ERROR")
        return 's', float(v)
    sub = _MVParser(arg, matrices, vectors, angle_unit, eval_scalar)
    return sub.parse()


def evaluate_matvec_expression(expr_str, matrices, vectors, angle_unit="Degree", variables=None, ans_val=0.0):
    """Evaluate a Matrix/Vector-mode expression. Returns (kind, value) with
    kind in {'s','m','v'}. Raises ValueError("Dimension ERROR") or
    ValueError("Math ERROR") / ZeroDivisionError."""
    s = expr_str.strip()
    if not s:
        raise ValueError("Math ERROR")

    def eval_scalar(chunk):
        return safe_evaluate_expression(chunk, ans_val, angle_unit, variables)

    # Phase 1: resolve matrix/vector function calls to canonical literals.
    s = _resolve_matvec_funcs(s, matrices, vectors, angle_unit, eval_scalar)
    # Phase 2: split on matrix/vector atoms; evaluate pure-scalar chunks.
    split_parts = _split_matvec_atoms(s)
    rebuilt = []
    for is_atom, part in split_parts:
        if is_atom:
            rebuilt.append(part)
            continue
        if part == '' or not re.search(r'[0-9A-Za-z(.]', part):
            # Pure operators/whitespace between atoms: keep verbatim.
            rebuilt.append(part)
            continue
        if part.lstrip()[:1] in ('*', '/', '^'):
            # Leading connector (e.g. '^2', '*MatA' fragments): the typed
            # parser owns it; scalar evaluation would choke on '^2'.
            rebuilt.append(part)
            continue
        m = re.match(r'^(.*?)([+\-*/^]+)$', part, re.DOTALL)
        trail = ''
        core = part
        if m and re.search(r'[0-9A-Za-z)]', m.group(1)):
            core, trail = m.group(1), m.group(2)
        if core.strip() == '':
            rebuilt.append(part)
            continue
        try:
            v = eval_scalar(core)
        except ZeroDivisionError:
            raise
        except Exception:
            raise ValueError("Math ERROR")
        if isinstance(v, complex):
            raise ValueError("Math ERROR")
        rebuilt.append(_lit(v) + trail)
    s = ''.join(rebuilt)
    # Phase 3: typed structural parse.
    parser = _MVParser(s, matrices, vectors, angle_unit, eval_scalar)
    return parser.parse()



class CalculatorController:
    def __init__(self) -> None:
        self.engine = Engine()
        self.expression = ""
        self.cursor_position = 0
        self.last_result = None
        self.result_displayed = False
        self.expression_viewport = 0
        self.shift = False
        self.alpha = False
        self.insert_mode = False
        self.undo_stack = []
        self.powered_on = True
        self.state = "INPUT"
        self.mode_name = "Calculate"
        self.mode_number = "1"
        self.menu_page = 1
        self.menu_index = 0
        self.base_n_base = 10
        self.spreadsheet_engine = SpreadsheetEngine()
        self._init_state()

    def _init_state(self) -> None:
        self.ans = "0"
        self.settings = dict(DEFAULT_SETTINGS)
        self.setup_settings = dict(DEFAULT_SETUP_SETTINGS)
        self.matrices = {
            "A": {"rows": 0, "cols": 0, "data": []},
            "B": {"rows": 0, "cols": 0, "data": []},
            "C": {"rows": 0, "cols": 0, "data": []},
            "D": {"rows": 0, "cols": 0, "data": []},
        }
        self.vectors = {
            "A": {"dim": 0, "data": []},
            "B": {"dim": 0, "data": []},
            "C": {"dim": 0, "data": []},
            "D": {"dim": 0, "data": []},
        }
        self.statistics = {
            "type": 0,   # 0 = not selected, 1-8 = regression type
            "data": []   # list of {"x": float, "y": float} or {"x": float} for 1-var
        }
        self.distribution = {"type": 0, "params": {}, "result": None}
        self.spreadsheet = {}  # { "A1": {"value": "123", "formula": ""}, ... }
        self.ratio = {"type": 1, "a": None, "b": None, "c_or_d": None, "x": None}
        self.variables = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0, "F": 0.0, "x": 0.0, "y": 0.0, "M": 0.0}
        self.ans_matrix = None
        self.ans_vector = None

    def get_settings(self) -> dict:
        return dict(self.settings)

    def _validate_setting(self, key, value):
        aliases = {
            "angle_unit": {"Deg": "Degree", "Rad": "Radian", "Gra": "Gradian"},
            "input_output": {"MthIO": "MathI/MathO", "MthO": "MathI/DecimalO", "LineIO": "LineI/LineO", "LineO": "LineI/DecimalO"},
        }
        if key in {"angleUnit", "angle_unit"}:
            normalized = aliases["angle_unit"].get(str(value).strip(), str(value).strip())
            if normalized not in {"Degree", "Radian", "Gradian"}:
                raise ValueError
            return normalized
        if key in {"inputOutput", "input_output"}:
            normalized = aliases["input_output"].get(str(value).strip(), str(value).strip())
            if normalized not in {"MathI/MathO", "MathI/DecimalO", "LineI/LineO", "LineI/DecimalO"}:
                raise ValueError
            return normalized
        if key in {"numberFormat", "number_format"}:
            normalized = str(value).strip()
            if normalized not in {"Fix", "Sci", "Norm"}:
                raise ValueError
            return normalized
        if key in {"numberFormatPrecision", "number_format_precision", "number_format_digits"}:
            if isinstance(value, bool):
                raise ValueError
            normalized = int(value)
            if not 0 <= normalized <= 9:
                raise ValueError
            return normalized
        if key in {"fractionResult", "fraction_result"}:
            normalized = str(value).strip()
            if normalized not in {"ab/c", "d/c"}:
                raise ValueError
            return normalized
        if key in {"showCell", "spreadsheet_show"}:
            normalized = str(value).strip()
            if normalized in {"formula", "Formula"}:
                return "Formula" if key == "showCell" else "formula"
            if normalized in {"value", "Value"}:
                return "Value" if key == "showCell" else "value"
            raise ValueError
        if key in {"engineeringSymbols", "engineering_symbols", "statisticsFrequency", "stat_frequency", "autoCalc", "spreadsheet_auto_calc"}:
            if not isinstance(value, bool):
                raise ValueError
            return value
        if key in {"contrast"}:
            normalized = int(value)
            if not 0 <= normalized <= 10:
                raise ValueError
            return normalized
        if key in self.setup_settings:
            return value
        raise ValueError

    def set_settings(self, new_settings: dict) -> dict:
        if not isinstance(new_settings, dict):
            return {"ok": False, "error": "Settings must be a JSON object"}
        updated = dict(self.settings)
        pairs = {
            "inputOutput": "inputOutput", "input_output": "inputOutput",
            "angleUnit": "angleUnit", "angle_unit": "angleUnit",
            "numberFormat": "numberFormat", "number_format": "numberFormat",
            "numberFormatPrecision": "numberFormatPrecision", "number_format_precision": "numberFormatPrecision",
            "engineeringSymbols": "engineeringSymbols", "engineering_symbols": "engineeringSymbols",
            "fractionResult": "fractionResult", "fraction_result": "fractionResult",
            "statisticsFrequency": "statisticsFrequency", "statistics_frequency": "statisticsFrequency",
            "autoCalc": "autoCalc", "auto_calc": "autoCalc",
            "showCell": "showCell", "show_cell": "showCell",
        }
        try:
            for key, target in pairs.items():
                if key in new_settings:
                    updated[target] = self._validate_setting(key, new_settings[key])
        except (ValueError, TypeError):
            bad = [k for k in new_settings if k in pairs]
            bad_name = bad[0] if bad else "setting"
            return {"ok": False, "error": f"Invalid {bad_name}"}
        self.settings = updated
        self.setup_settings["angle_unit"] = self.settings["angleUnit"]
        return {"ok": True, "success": True, "settings": dict(self.settings)}

    def update_setup_setting(self, key, value) -> dict:
        if key not in self.setup_settings:
            return {"ok": False, "error": "unknown key"}
        try:
            normalized = self._validate_setting(key, value)
        except (ValueError, TypeError):
            return {"ok": False, "error": f"Invalid value for setting: {key}"}
        self.setup_settings[key] = normalized
        mapping = {
            "angle_unit": "angleUnit", "input_output": "inputOutput", "number_format": "numberFormat",
            "number_format_digits": "numberFormatPrecision", "engineering_symbols": "engineeringSymbols",
            "fraction_result": "fractionResult", "stat_frequency": "statisticsFrequency",
            "spreadsheet_auto_calc": "autoCalc", "spreadsheet_show": "showCell",
        }
        if key in mapping:
            self.settings[mapping[key]] = normalized
        return {"ok": True, "settings": dict(self.setup_settings)}

    def set_matrix(self, matrix_name: str, rows: int, cols: int, data: list) -> dict:
        name = str(matrix_name).strip().upper()
        if name not in {"A", "B", "C", "D"}:
            return {"ok": False, "error": f"Invalid matrix name '{matrix_name}'. Must be A, B, C, or D."}
        try:
            rows_int = int(rows)
            cols_int = int(cols)
        except (ValueError, TypeError):
            return {"ok": False, "error": "Rows and cols must be integers."}
        if not (1 <= rows_int <= 4 and 1 <= cols_int <= 4):
            return {"ok": False, "error": "Matrix dimensions must be between 1x1 and 4x4."}
        if not isinstance(data, list) or len(data) != rows_int:
            return {"ok": False, "error": f"Data row count ({len(data) if isinstance(data, list) else 0}) does not match rows ({rows_int})."}
        cleaned_data = []
        for r_idx, row in enumerate(data):
            if not isinstance(row, list) or len(row) != cols_int:
                return {"ok": False, "error": f"Data col count at row {r_idx} does not match cols ({cols_int})."}
            cleaned_row = []
            for val in row:
                try:
                    f_val = float(val) if val not in ("", None) else 0.0
                    cleaned_row.append(int(f_val) if f_val.is_integer() else f_val)
                except (ValueError, TypeError):
                    return {"ok": False, "error": f"Invalid numeric value in matrix data: {val!r}"}
            cleaned_data.append(cleaned_row)

        self.matrices[name] = {
            "rows": rows_int,
            "cols": cols_int,
            "data": cleaned_data,
        }
        return {"ok": True, "success": True}

    def set_vector(self, vector_name: str, dim: int, data: list) -> dict:
        name = str(vector_name).strip().upper()
        if name not in {"A", "B", "C", "D"}:
            return {"ok": False, "error": f"Invalid vector name '{vector_name}'. Must be A, B, C, or D."}
        try:
            dim_int = int(dim)
        except (ValueError, TypeError):
            return {"ok": False, "error": "Dim must be an integer."}
        if not (1 <= dim_int <= 4):
            return {"ok": False, "error": "Vector dimension must be between 1 and 4."}
        if not isinstance(data, list) or len(data) != dim_int:
            return {"ok": False, "error": f"Data length ({len(data) if isinstance(data, list) else 0}) does not match dim ({dim_int})."}
        cleaned = []
        for val in data:
            try:
                f_val = float(val) if val not in ("", None) else 0.0
                cleaned.append(int(f_val) if isinstance(f_val, float) and f_val.is_integer() else f_val)
            except (ValueError, TypeError):
                return {"ok": False, "error": f"Invalid numeric value: {val!r}"}
        self.vectors[name] = {"dim": dim_int, "data": cleaned}
        return {"ok": True, "success": True}

    def set_statistics(self, stat_type: int, data: list) -> dict:
        try:
            t = int(stat_type)
        except (ValueError, TypeError):
            return {"ok": False, "error": "Type must be an integer 1-8."}
        if not (1 <= t <= 8):
            return {"ok": False, "error": "Statistics type must be 1-8."}
        if not isinstance(data, list):
            return {"ok": False, "error": "Data must be a list."}
        is_one_var = (t == 1)
        cleaned = []
        for i, row in enumerate(data):
            if not isinstance(row, dict):
                return {"ok": False, "error": f"Row {i} must be a dict."}
            try:
                x_val = float(row.get("x", 0))
            except (ValueError, TypeError):
                return {"ok": False, "error": f"Invalid x at row {i}."}
            if is_one_var:
                cleaned.append({"x": x_val})
            else:
                try:
                    y_val = float(row.get("y", 0))
                except (ValueError, TypeError):
                    return {"ok": False, "error": f"Invalid y at row {i}."}
                cleaned.append({"x": x_val, "y": y_val})
        self.statistics = {"type": t, "data": cleaned}
        return {"ok": True, "success": True}

    def calculate_statistics(self, stat_type: int, data: list) -> dict:
        stored = self.set_statistics(stat_type, data)
        if not stored.get("ok"):
            return stored
        t = int(stat_type)
        try:
            self.engine.set_mode("STATISTICS")
            xs = [row["x"] for row in self.statistics["data"]]
            freqs = [row.get("freq", 1) for row in self.statistics["data"]]
            if t == 1:
                self.engine.stats_set_1var(xs, freqs)
                result = {"n": self.engine.stats_n(), "mean": self.engine.stats_mean(),
                          "populationStd": self.engine.stats_population_std(),
                          "min": self.engine.stats_min(), "max": self.engine.stats_max()}
            else:
                ys = [row["y"] for row in self.statistics["data"]]
                self.engine.stats_set_2var(xs, ys, freqs)
                result = {2: self.engine.stats_linear_regression,
                          3: self.engine.stats_quadratic_regression,
                          4: self.engine.stats_log_regression,
                          5: self.engine.stats_exp_e_regression,
                          6: self.engine.stats_exp_ab_regression,
                          7: self.engine.stats_power_regression,
                          8: self.engine.stats_inverse_regression}[t]()
            return {"ok": True, "success": True, "type": t, "result": result}
        except Exception as exc:
            return {"ok": False, "error": f"Math ERROR: {exc}"}

    def calculate_table(self, expr: str, x_start: float, x_end: float, x_step: float) -> dict:
        try:
            self.engine.set_mode("TABLE")
            # The calculator editor emits ^ notation; TableEngine evaluates
            # Python expressions and therefore needs exponentiation as **.
            self.engine.table_set_f(str(expr).replace("^", "**"))
            return {"ok": True, "success": True, "rows": self.engine.table_generate(float(x_start), float(x_end), float(x_step))}
        except Exception as exc:
            return {"ok": False, "error": f"Math ERROR: {exc}"}

    def solve_equation(self, kind: str, coefficients, count_or_degree: int) -> dict:
        try:
            print(f"[EQUATION] request kind={kind!r} count_or_degree={count_or_degree!r} coefficients={coefficients!r}", flush=True)
            self.engine.set_mode("EQUATION")
            if kind == "simultaneous":
                n = int(count_or_degree)
                vals = [[float(v) for v in row] for row in coefficients]
                result = {2: self.engine.equation_solve_simultaneous_2,
                          3: self.engine.equation_solve_simultaneous_3,
                          4: self.engine.equation_solve_simultaneous_4}[n](vals)
            else:
                n = int(count_or_degree)
                vals = [float(v) for v in coefficients]
                if n == 2: result = self.engine.equation_solve_quadratic(*vals)
                elif n == 3: result = self.engine.equation_solve_cubic(*vals)
                elif n == 4: result = self.engine.equation_solve_quartic(*vals)
                else: raise ValueError("degree must be 2-4")
            def json_safe(value):
                if isinstance(value, complex):
                    return {"real": value.real, "imag": value.imag}
                if isinstance(value, list):
                    return [json_safe(item) for item in value]
                if isinstance(value, tuple):
                    return [json_safe(item) for item in value]
                if isinstance(value, dict):
                    return {key: json_safe(item) for key, item in value.items()}
                return value
            response = {"ok": True, "success": True, "result": json_safe(result)}
            print(f"[EQUATION] parsed={vals!r} result={response['result']!r}", flush=True)
            return response
        except Exception as exc:
            print(f"[EQUATION] error={exc!r}", flush=True)
            return {"ok": False, "error": f"Math ERROR: {exc}"}

    def solve_inequality(self, degree: int, operator: str, coefficients: list) -> dict:
        try:
            self.engine.set_mode("INEQUALITY")
            vals = [float(v) for v in coefficients]
            op = str(operator).replace(" 0", "").strip()
            op = op.replace("\u2265", ">=").replace("\u2264", "<=")
            if int(degree) == 2: self.engine.inequality_set_quadratic(*vals, operator=op)
            elif int(degree) == 3: self.engine.inequality_set_cubic(*vals, operator=op)
            elif int(degree) == 4: self.engine.inequality_set_quartic(*vals, operator=op)
            else: raise ValueError("degree must be 2-4")
            return {"ok": True, "success": True, "result": self.engine.inequality_solve(), "solution": self.engine.inequality_solution_as_string()}
        except Exception as exc:
            return {"ok": False, "error": f"Math ERROR: {exc}"}

    def calculate_distribution(self, dist_type: int, params: dict) -> dict:
        try:
            t = int(dist_type)
            if t == 1:   # Normal PD
                result = _dist_normal_pdf(
                    float(params['x']),
                    float(params.get('mu', 0)),
                    float(params.get('sigma', 1))
                )
            elif t == 2:  # Normal CD
                result = _dist_normal_cdf(
                    float(params['upper']),
                    float(params.get('mu', 0)),
                    float(params.get('sigma', 1))
                ) - _dist_normal_cdf(
                    float(params['lower']),
                    float(params.get('mu', 0)),
                    float(params.get('sigma', 1))
                )
            elif t == 3:  # Inverse Normal
                result = _dist_inverse_normal(
                    float(params['area']),
                    float(params.get('mu', 0)),
                    float(params.get('sigma', 1))
                )
            elif t == 4:  # Binomial PD
                result = _dist_binomial_pd(
                    float(params['x']), float(params['n']), float(params['p'])
                )
            elif t == 5:  # Binomial CD
                result = _dist_binomial_cd(
                    float(params['x']), float(params['n']), float(params['p'])
                )
            elif t == 6:  # Poisson PD
                result = _dist_poisson_pd(
                    float(params['x']), float(params['lambda'])
                )
            elif t == 7:  # Poisson CD
                result = _dist_poisson_cd(
                    float(params['x']), float(params['lambda'])
                )
            else:
                return {"ok": False, "error": f"Invalid distribution type {t}"}
            formatted = self._format_result(result)
            self.distribution = {"type": t, "params": params, "result": formatted}
            return {"ok": True, "success": True, "result": formatted}
        except KeyError as exc:
            return {"ok": False, "error": f"Missing parameter: {exc}"}
        except Exception as exc:
            return {"ok": False, "error": f"Math ERROR: {exc}"}

    def set_spreadsheet_cell(self, cell_ref: str, value: str) -> dict:
        ref = str(cell_ref).strip().upper()
        if not re.fullmatch(r"[A-Z][1-9][0-9]{0,3}", ref):
            return {"ok": False, "error": "Invalid cell reference"}
        val_str = str(value).strip()
        if not val_str:
            try:
                self.spreadsheet_engine.clear_cell(ref)
            except Exception:
                pass
            self.spreadsheet.pop(ref, None)
            if self.settings.get("autoCalc", True):
                self.eval_spreadsheet()
            return {"ok": True, "success": True, "cell": ref, "data": None, "cells": self.spreadsheet}

        try:
            self.spreadsheet_engine.set_cell(ref, val_str)
            computed = self.spreadsheet_engine.get_cell_value(ref)
            formatted_computed = self._format_result(computed) if computed is not None else ""
        except Exception:
            return {"ok": False, "error": "Formula error"}

        self.spreadsheet[ref] = {
            "raw": val_str,
            "value": formatted_computed if val_str.startswith("=") else val_str,
            "formula": val_str if val_str.startswith("=") else ""
        }
        if self.settings.get("autoCalc", True):
            evaluated = self.eval_spreadsheet()
            if not evaluated.get("ok"):
                return evaluated

        return {"ok": True, "success": True, "cell": ref, "data": self.spreadsheet.get(ref), "cells": self.spreadsheet}

    def get_spreadsheet(self) -> dict:
        return {"ok": True, "success": True, "cells": self.spreadsheet}

    def clear_spreadsheet(self) -> dict:
        self.spreadsheet.clear()
        self.spreadsheet_engine.clear_all()
        return {"ok": True, "success": True, "cells": {}}

    def eval_spreadsheet(self) -> dict:
        results = {}
        for ref, item in list(self.spreadsheet.items()):
            raw = item.get("raw", item.get("value", ""))
            try:
                self.spreadsheet_engine.set_cell(ref, raw)
            except Exception:
                return {"ok": False, "error": "Formula error"}
        for ref, item in list(self.spreadsheet.items()):
            raw = item.get("raw", item.get("value", ""))
            try:
                computed = self.spreadsheet_engine.get_cell_value(ref)
                res_fmt = self._format_result(computed) if computed is not None else ""
            except Exception:
                return {"ok": False, "error": "Formula error"}
            self.spreadsheet[ref]["value"] = res_fmt if raw.startswith("=") else raw
            results[ref] = self.spreadsheet[ref]["value"]
        return {"ok": True, "success": True, "results": results, "cells": self.spreadsheet}

    def calculate_ratio(self, ratio_type: int, a: float, b: float, c_or_d: float) -> dict:
        try:
            t = int(ratio_type)
            fa, fb, fcd = float(a), float(b), float(c_or_d)
            x_val = _solve_ratio(t, fa, fb, fcd)
            formatted = self._format_result(x_val)
            self.ratio = {"type": t, "a": fa, "b": fb, "c_or_d": fcd, "x": formatted}
            return {"ok": True, "success": True, "result": formatted, "x": formatted}
        except ZeroDivisionError:
            return {"ok": False, "error": "Math ERROR"}
        except Exception as exc:
            return {"ok": False, "error": f"Math ERROR: {exc}"}

    def convert_units_calc(self, category: str, from_unit: str, to_unit: str, value: float) -> dict:
        try:
            val = float(value)
            res = _convert_units(category, from_unit, to_unit, val)
            formatted = self._format_result(res)
            return {"ok": True, "success": True, "result": formatted, "numericResult": res}
        except Exception as exc:
            return {"ok": False, "error": f"Conversion ERROR: {exc}"}

    def get_constants(self) -> dict:
        return {"ok": True, "success": True, "constants": SCIENTIFIC_CONSTANTS}

    def reset_calculator(self, target: str) -> dict:
        t = str(target).strip().lower()
        if t in ("setup", "setup_data"):
            self.settings = dict(DEFAULT_SETTINGS)
            self.setup_settings = dict(DEFAULT_SETUP_SETTINGS)
            return {"ok": True, "success": True, "settings": dict(self.settings)}
        elif t == "memory":
            self.ans = "0"
            self.variables = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0, "F": 0.0, "x": 0.0, "y": 0.0, "M": 0.0}
            self.matrices = {k: {"rows": 0, "cols": 0, "data": []} for k in ("A", "B", "C", "D")}
            self.vectors = {k: {"dim": 0, "data": []} for k in ("A", "B", "C", "D")}
            self.statistics = {"type": 0, "data": []}
            self.distribution = {"type": 0, "params": {}, "result": None}
            return {"ok": True, "success": True}
        elif t in ("all", "initialize_all"):
            self._init_state()
            self.spreadsheet_engine.clear_all()
            self.expression = ""
            self.cursor_position = 0
            self.last_result = None
            self.result_displayed = False
            self.mode_name = "Calculate"
            self.mode_number = "1"
            self.engine.reset()
            self.state = "INPUT"
            return {"ok": True, "success": True, "state": self._state()}
        else:
            return {"ok": False, "error": f"Unknown reset target: {target}"}

    def _convert_base(self, value_str, from_base, to_base):
        try:
            decimal_val = int(str(value_str).strip(), from_base)
            if to_base == 10:
                return str(decimal_val)
            sign = "-" if decimal_val < 0 else ""
            magnitude = abs(decimal_val)
            if to_base == 2:
                return f"{sign}{bin(magnitude)[2:]}"
            elif to_base == 8:
                return f"{sign}{oct(magnitude)[2:]}"
            elif to_base == 16:
                return f"{sign}{hex(magnitude)[2:].upper()}"
            return str(decimal_val)
        except Exception:
            return str(value_str)

    def _format_single_number(self, val):
        if not isinstance(val, (int, float)):
            return str(val)
        if math.isnan(val) or math.isinf(val):
            return str(val)

        num_fmt = self.settings.get("numberFormat", self.settings.get("number_format", "Norm"))
        precision = self.settings.get("numberFormatPrecision", self.settings.get("number_format_precision", 1))
        eng_sym = self.settings.get("engineeringSymbols", self.settings.get("engineering_symbols", False))

        # Handle Engineering Symbols if enabled
        if eng_sym and val != 0:
            exp = int(math.floor(math.log10(abs(val)) / 3.0) * 3)
            mant = val / (10.0 ** exp)
            si_prefixes = {
                -15: " f", -12: " p", -9: " n", -6: " µ", -3: " m",
                0: "", 3: " k", 6: " M", 9: " G", 12: " T", 15: " P"
            }
            if exp in si_prefixes and si_prefixes[exp] != "":
                mant_str = f"{mant:.10g}"
                return f"{mant_str}{si_prefixes[exp]}"
            elif exp != 0:
                mant_str = f"{mant:.10g}"
                return f"{mant_str}×10^{exp}"

        if num_fmt == "Fix":
            p = int(precision) if precision is not None else 2
            p = max(0, min(9, p))
            return f"{val:.{p}f}"
        elif num_fmt == "Sci":
            p = int(precision) if precision is not None else 3
            if p == 0:
                p = 10
            p = max(1, min(10, p))
            s = f"{val:.{p-1}e}"
            parts = s.split("e")
            mant = parts[0]
            ex = int(parts[1])
            return f"{mant}×10^{ex}"
        else:  # Norm
            norm_type = int(precision) if precision in (1, 2, "1", "2") else 1
            ax = abs(val)
            if ax != 0:
                lower_lim = 1e-2 if norm_type == 1 else 1e-9
                if ax < lower_lim or ax >= 1e10:
                    s = f"{val:.9e}"
                    parts = s.split("e")
                    mant = parts[0].rstrip("0").rstrip(".")
                    ex = int(parts[1])
                    return f"{mant}×10^{ex}"
            if isinstance(val, float) and val.is_integer():
                return str(int(val))
            return f"{val:.10g}"

    def _format_result(self, result):
        if isinstance(result, complex):
            r, i = result.real, result.imag
            if abs(i) < 1e-14:
                return self._format_single_number(r)
            if abs(r) < 1e-14:
                return f"{self._format_single_number(i)}i"
            sign = "+" if i >= 0 else "-"
            r_str = self._format_single_number(r)
            i_str = self._format_single_number(abs(i))
            return f"{r_str}{sign}{i_str}i"
        if isinstance(result, (int, float)):
            return self._format_single_number(result)
        return str(result)

    def set_variable(self, name: str, value) -> dict:
        key = str(name).strip().upper()
        if key not in {"A", "B", "C", "D", "E", "F", "M", "X", "Y"}:
            return {"ok": False, "error": f"Invalid variable '{name}'"}
        try:
            fval = float(value)
        except (ValueError, TypeError):
            return {"ok": False, "error": "Variable value must be numeric"}
        self.variables[key] = fval
        return {"ok": True, "success": True, "variable": key, "value": fval, "variables": dict(self.variables)}

    def get_variables(self) -> dict:
        return {"ok": True, "success": True, "variables": dict(self.variables)}

    def calc_evaluate(self, expression: str, values: dict | None = None):
        """CALC: substitute provided variable values, evaluate, keep stored vars."""
        try:
            merged = dict(self.variables)
            if isinstance(values, dict):
                for k, v in values.items():
                    ku = str(k).strip().upper()
                    if ku in merged:
                        merged[ku] = float(v)
            try:
                ans_float = float(self.ans)
            except (ValueError, TypeError):
                ans_float = 0.0
            angle_u = self.setup_settings["angle_unit"]
            res = safe_evaluate_expression(str(expression), ans_float, angle_u, merged, self.mode_name == "Complex", self._rnd_setting())
            if isinstance(res, complex):
                if abs(res.imag) < 1e-14:
                    res = float(res.real)
                elif self.mode_name != "Complex":
                    return {"ok": False, "error": "Math ERROR"}
            # Persist any caller-supplied values like the real CALC prompt does.
            if isinstance(values, dict):
                for k, v in values.items():
                    ku = str(k).strip().upper()
                    if ku in self.variables:
                        try:
                            self.variables[ku] = float(v)
                        except Exception:
                            pass
            formatted = self._format_result(res)
            self.last_result = formatted
            self.ans = formatted
            self.result_displayed = True
            self.state = "RESULT"
            return {"ok": True, "success": True, "result": formatted, "variables": dict(self.variables)}
        except ZeroDivisionError:
            return {"ok": False, "error": DIV_ZERO_MSG}
        except Exception as exc:
            msg = str(exc) if str(exc).startswith("Math ERROR") else f"Math ERROR: {exc}"
            return {"ok": False, "error": msg}

    def solve_equation_newton(self, expression: str, variable: str = "X", guess: float = 0.0):
        """SOLVE (Newton's method, fx-991EX style): solve expr==0 or lhs==rhs for variable."""
        try:
            var = str(variable).strip().upper() or "X"
            if var not in {"A", "B", "C", "D", "E", "F", "M", "X", "Y"}:
                var = "X"
            try:
                x0 = float(guess)
            except (ValueError, TypeError):
                x0 = 0.0
            try:
                ans_float = float(self.ans)
            except (ValueError, TypeError):
                ans_float = 0.0
            angle_u = self.setup_settings["angle_unit"]
            expr = str(expression)
            if "=" in expr and "__BASE_SWITCH__" not in expr:
                lhs, rhs = expr.split("=", 1)
                def f(x):
                    merged = dict(self.variables)
                    merged[var] = float(x)
                    l = safe_evaluate_expression(lhs, ans_float, angle_u, merged)
                    r = safe_evaluate_expression(rhs, ans_val=ans_float, angle_unit=angle_u, variables=merged)
                    return float(l) - float(r)
            else:
                def f(x):
                    merged = dict(self.variables)
                    merged[var] = float(x)
                    return float(safe_evaluate_expression(expr, ans_float, angle_u, merged))
            h = 1e-6
            x = x0
            for _ in range(100):
                try:
                    fx = f(x)
                except Exception:
                    return {"ok": False, "error": "Math ERROR"}
                if abs(fx) < 1e-10:
                    break
                try:
                    dfx = (f(x + h) - f(x - h)) / (2 * h)
                except Exception:
                    return {"ok": False, "error": "Math ERROR"}
                if abs(dfx) < 1e-12:
                    # nudge and retry (Newton needs nonzero derivative)
                    x = x + 0.5 if x >= 0 else x - 0.5
                    continue
                x_new = x - fx / dfx
                if abs(x_new - x) < 1e-9:
                    x = x_new
                    break
                x = x_new
                if abs(x) > 1e12:
                    return {"ok": False, "error": "Math ERROR"}
            else:
                return {"ok": False, "error": "Math ERROR"}
            try:
                if abs(f(x)) > 1e-6:
                    return {"ok": False, "error": "Math ERROR"}
            except Exception:
                return {"ok": False, "error": "Math ERROR"}
            self.variables[var] = float(x)
            formatted = self._format_result(float(x))
            self.last_result = formatted
            self.ans = formatted
            self.result_displayed = True
            self.state = "RESULT"
            return {"ok": True, "success": True, "result": formatted, "variable": var, "value": float(x)}
        except ZeroDivisionError:
            return {"ok": False, "error": DIV_ZERO_MSG}
        except Exception as exc:
            msg = str(exc) if str(exc).startswith("Math ERROR") else f"Math ERROR: {exc}"
            return {"ok": False, "error": msg}

    def _matvec_result(self, kind, val):
        if kind == 's':
            return self._format_result(val)
        if kind == 'm':
            return _format_matrix_canonical(val, self._format_single_number)
        return _format_vector_canonical(val, self._format_single_number)

    def _run_matvec(self, expr):
        try:
            ans_float = float(self.ans) if self.ans is not None else 0.0
        except (ValueError, TypeError):
            ans_float = 0.0
        angle_u = self.setup_settings["angle_unit"]
        return evaluate_matvec_expression(expr, self.matrices, self.vectors,
                                          angle_u, self.variables, ans_float)

    def _store_matvec_answer(self, kind, val, formatted):
        # Like the physical unit (separate MatAns/VctAns memories), matrix and
        # vector answers must not clobber the scalar Ans register.
        if kind == 's':
            self.last_result = formatted
            self.ans = formatted
        elif kind == 'm':
            self.ans_matrix = formatted
            self.last_result = formatted
        else:
            self.ans_vector = formatted
            self.last_result = formatted
        self.result_displayed = True
        self.shift = False
        self.alpha = False
        self.state = "RESULT"
        return self._state(display=self._display(formatted))

    def calculate_matrix(self, op, a=None, b=None, scalar=None, n=None):
        """Explicit Matrix-mode operation (mirrors OPTN menu items)."""
        try:
            o = str(op).strip().lower()
            A = (str(a or "").strip().upper())[-1:] if a else ""
            B = (str(b or "").strip().upper())[-1:] if b else ""
            if o == "add":
                expr = f"Mat{A}+Mat{B}"
            elif o == "subtract":
                expr = f"Mat{A}-Mat{B}"
            elif o == "multiply":
                expr = f"Mat{A}*Mat{B}"
            elif o == "scalar_multiply":
                expr = f"({float(scalar)})*Mat{A}"
            elif o == "transpose":
                expr = f"Trn(Mat{A})"
            elif o == "determinant":
                expr = f"Det(Mat{A})"
            elif o == "inverse":
                expr = f"Mat{A}^(-1)"
            elif o == "power":
                expr = f"Mat{A}^({int(scalar if scalar is not None else 2)})"
            elif o == "identity":
                expr = f"Identity({int(n if n is not None else scalar or 0)})"
            elif o == "abs":
                expr = f"Abs(Mat{A})"
            else:
                return {"ok": False, "error": "Math ERROR"}
            kind, val = self._run_matvec(expr)
            return {"ok": True, "success": True, "result": self._matvec_result(kind, val)}
        except ZeroDivisionError:
            return {"ok": False, "error": DIV_ZERO_MSG}
        except ValueError as exc:
            return {"ok": False, "error": "Dimension ERROR" if "Dimension" in str(exc) else "Math ERROR"}
        except Exception:
            return {"ok": False, "error": "Math ERROR"}

    def calculate_vector(self, op, a=None, b=None, scalar=None):
        """Explicit Vector-mode operation (mirrors OPTN menu items)."""
        try:
            o = str(op).strip().lower()
            A = (str(a or "").strip().upper())[-1:] if a else ""
            B = (str(b or "").strip().upper())[-1:] if b else ""
            if o == "add":
                expr = f"Vct{A}+Vct{B}"
            elif o == "subtract":
                expr = f"Vct{A}-Vct{B}"
            elif o == "scalar_multiply":
                expr = f"({float(scalar)})*Vct{A}"
            elif o in ("multiply", "cross"):
                expr = f"Vct{A}*Vct{B}"
            elif o in ("dot", "dot_product"):
                expr = f"Dot(Vct{A},Vct{B})"
            elif o == "angle":
                expr = f"Angle(Vct{A},Vct{B})"
            elif o in ("unit", "unit_vector"):
                expr = f"UnitV(Vct{A})"
            elif o in ("abs", "magnitude"):
                expr = f"Abs(Vct{A})"
            else:
                return {"ok": False, "error": "Math ERROR"}
            kind, val = self._run_matvec(expr)
            return {"ok": True, "success": True, "result": self._matvec_result(kind, val)}
        except ZeroDivisionError:
            return {"ok": False, "error": DIV_ZERO_MSG}
        except ValueError as exc:
            return {"ok": False, "error": "Dimension ERROR" if "Dimension" in str(exc) else "Math ERROR"}
        except Exception:
            return {"ok": False, "error": "Math ERROR"}

    def _display(self, canonical):
        return format_display(
            canonical,
            self.setup_settings.get("decimal_mark", "Dot"),
            bool(self.setup_settings.get("digit_separator", False)))

    def _rnd_setting(self):
        fmt = self.settings.get("numberFormat", "Norm")
        prec = self.settings.get("numberFormatPrecision", 1)
        try:
            prec_int = int(prec)
        except (ValueError, TypeError):
            prec_int = 1
        if fmt == "Fix":
            return ("Fix", max(0, min(9, prec_int)))
        if fmt == "Sci":
            return ("Sci", prec_int)
        return ("Norm", 2 if prec_int == 2 else 1)

    def _state(self, ok=True, error=None, display=None):
        if not self.powered_on:
            display = ""
        elif error:
            display = error
        if display is None:
            display = self.expression if self.last_result is None else self.last_result
        return {
            "ok": ok,
            "state": "OFF" if not self.powered_on else self.state,
            "poweredOn": self.powered_on,
            "display": str(display),
            "expression": self.expression,
            "result": self.last_result,
            "resultDisplayed": self.result_displayed,
            "cursorPosition": self.cursor_position,
            "expressionViewport": self.expression_viewport,
            "ans": self.ans,
            "error": error,
            "mode": self.engine.get_mode(),
            "modeName": self.mode_name,
            "modeNumber": self.mode_number,
            "shift": self.shift,
            "alpha": self.alpha,
            "insertMode": self.insert_mode,
            "settings": self.settings,
            "menuPage": self.menu_page,
            "menuIndex": self.menu_index,
            "base": self.base_n_base,
            "selectedMode": self._selected_menu()[1],
            "matrices": self.matrices,
            "vectors": self.vectors,
            "statistics": self.statistics,
            "distribution": self.distribution,
            "spreadsheet": self.spreadsheet,
            "ratio": self.ratio,
            "variables": self.variables,
        }

    def get_state(self):
        with CONTROLLER_LOCK:
            return self._state()

    def _selected_menu(self):
        page_idx = max(0, min(self.menu_page - 1, len(MENU_PAGES) - 1))
        item_idx = max(0, min(self.menu_index, len(MENU_PAGES[page_idx]) - 1))
        return MENU_PAGES[page_idx][item_idx]

    def _sync_menu_from_payload(self, payload) -> bool:
        """Adopt the frontend's canonical menu cursor (single source of truth).

        The frontend sends menuPage (1/2) + menuIndex (0-based within page)
        with every /api/key request. When present and valid, the backend
        adopts it so digit selection, D-pad navigation and equals-confirm
        all resolve against the same cursor instead of competing cursors.
        """
        try:
            mp = payload.get("menuPage")
            mi = payload.get("menuIndex")
            if mp is None or mi is None:
                return False
            page = int(mp)
            idx = int(mi)
            if page not in (1, 2):
                return False
            if not (0 <= idx < len(MENU_PAGES[page - 1])):
                return False
            self.menu_page = page
            self.menu_index = idx
            return True
        except (ValueError, TypeError):
            return False

    def _move_menu(self, key):
        page_items = MENU_PAGES[self.menu_page - 1]
        if key == "dpad_right":
            if self.menu_index < len(page_items) - 1:
                self.menu_index += 1
            elif self.menu_page == 1:
                self.menu_page = 2
                self.menu_index = 0
            else:
                self.menu_page = 1
                self.menu_index = 0
        elif key == "dpad_left":
            if self.menu_index > 0:
                self.menu_index -= 1
            elif self.menu_page == 2:
                self.menu_page = 1
                self.menu_index = len(MENU_PAGES[0]) - 1
            else:
                self.menu_page = 2
                self.menu_index = len(MENU_PAGES[1]) - 1
        elif key == "dpad_up":
            if self.menu_index >= 4:
                self.menu_index -= 4
        elif key == "dpad_down":
            if self.menu_index + 4 < len(page_items):
                self.menu_index += 4

    def _enter_selected_mode(self):
        number, mode_name = self._selected_menu()
        return self.set_mode(mode_name, number)

    def _token_for(self, key):
        if self.mode_name == "Complex" and key == "eng":
            return "i"
        if self.mode_name == "Base-N" and self.shift:
            base_switch = {
                "square": "DEC",
                "power": "HEX",
                "log": "BIN",
                "ln": "OCT",
            }.get(key)
            if base_switch:
                return f"__BASE_SWITCH__{base_switch}__"
        if self.shift:
            return {
                "sin": "asin(", "cos": "acos(", "tan": "atan(",
                "log": "10^(", "ln": "e^(", "sqrt": "cbrt(",
                "square": "^3", "power": "xroot(", "scientific": "π",
                "0": "round(", "decimal": "rand()", "fraction": "mixed_frac(",
                "integral": "diff(", "variable": "sigma(",
                "ellipsis": "FACT(", "right_paren": ",",
                "ans": "%",
                "eng": "<",
            }.get(key, "")
        if self.alpha:
            return {
                "negate": "A", "ellipsis": "B", "inverse": "C",
                "sin": "D", "cos": "E", "tan": "F",
                "right_paren": "x", "s_to_d": "y", "m_plus": "M",
                "scientific": "e", "decimal": "RanInt(",
                "integral": ":", "calc": "=", "eng": "i",
            }.get(key, "")
        return {
            **{str(number): str(number) for number in range(10)},
            "decimal": ".", "plus": "+", "minus": "-",
            "multiply": "*", "divide": "/", "left_paren": "(",
            "right_paren": ")", "negate": "(-", "sin": "sin(",
            "cos": "cos(", "tan": "tan(", "log": "log(",
            "ln": "ln(", "sqrt": "sqrt(", "square": "^2",
            "power": "^", "inverse": "^(-1)", "scientific": "*10^",
            "ans": str(self.ans) if self.ans is not None else "0",
            "fraction": "/", "variable": "x", "integral": "integral(",
        }.get(key, "")

    def set_mode(self, mode_name, number=""):
        engine_mode = MODE_MAP.get(mode_name)
        if engine_mode is None:
            self.mode_name = mode_name
            self.mode_number = str(number or self.mode_number)
            self.state = "ERROR"
            return self._state(False, f"{mode_name} unavailable")
        try:
            for page_number, page_items in enumerate(MENU_PAGES, start=1):
                for item_index, (_, item_name) in enumerate(page_items):
                    if item_name == mode_name:
                        self.menu_page = page_number
                        self.menu_index = item_index
                        break
            self.engine.set_mode(engine_mode)
            self.mode_name = mode_name
            self.mode_number = str(number or self.mode_number)
            self.state = "INPUT"
            self.expression = ""
            self.cursor_position = 0
            self.expression_viewport = 0
            self.last_result = None
            self.result_displayed = False
            return self._state()
        except Exception as exc:
            return self._state(False, str(exc))

    def press_key(self, payload):
        key = str(payload.get("key", ""))
        action = str(payload.get("action", key))
        expr_override = payload.get("expression")

        try:
            if key == "on":
                self.powered_on = True
                self.state = "INPUT"
                self.engine.set_mode("CALC")
                self.mode_name = "Calculate"
                self.mode_number = "1"
                self.expression = ""
                self.cursor_position = 0
                self.expression_viewport = 0
                self.last_result = None
                self.result_displayed = False
                self.shift = False
                self.alpha = False
                self.insert_mode = False
                self.undo_stack.clear()
                return self._state()

            if not self.powered_on:
                return self._state()

            if (key == "ac" and action.upper() == "OFF") or (key == "ac" and self.shift):
                self.powered_on = False
                self.shift = False
                self.alpha = False
                self.state = "OFF"
                return self._state()

            if key == "shift":
                self.shift = not self.shift
                self.alpha = False
                return self._state()
            if key == "alpha":
                self.alpha = not self.alpha
                self.shift = False
                return self._state()

            if key == "ac":
                self.expression = ""
                self.cursor_position = 0
                self.expression_viewport = 0
                self.last_result = None
                self.result_displayed = False
                self.shift = False
                self.alpha = False
                self.undo_stack.clear()
                self.state = "INPUT"
                return self._state()

            if key == "del" and self.shift:
                self.insert_mode = not self.insert_mode
                self.shift = False
                self.alpha = False
                return self._state()

            if key == "del" and self.alpha:
                if self.undo_stack:
                    previous = self.undo_stack.pop()
                    self.expression = previous["expression"]
                    self.cursor_position = previous["cursor_position"]
                    self.result_displayed = previous["result_displayed"]
                    self.last_result = previous["last_result"]
                self.shift = False
                self.alpha = False
                return self._state()

            if key == "del":
                self._return_to_editing()
                self.undo_stack.append({
                    "expression": self.expression,
                    "cursor_position": self.cursor_position,
                    "result_displayed": self.result_displayed,
                    "last_result": self.last_result,
                })
                if expr_override is not None:
                    self.expression = str(expr_override)
                    self.cursor_position = int(payload.get("cursorPosition", len(self.expression)))
                else:
                    if self.cursor_position < len(self.expression):
                        self.expression = (self.expression[:self.cursor_position] +
                                           self.expression[self.cursor_position + 1:])
                    elif self.cursor_position > 0:
                        self.expression = self.expression[:self.cursor_position - 1]
                        self.cursor_position -= 1
                self.shift = False
                self.alpha = False
                self.state = "INPUT"
                return self._state()

            if key in {"dpad_up", "dpad_down", "dpad_left", "dpad_right"} and self.state == "RESULT":
                self._return_to_editing()
                return self._state()

            if key == "dpad_left" and self.state != "MENU":
                if payload.get("cursorPosition") is not None:
                    self.cursor_position = int(payload.get("cursorPosition"))
                else:
                    self.cursor_position = max(0, self.cursor_position - 1)
                self._update_viewport()
                return self._state()

            if key == "dpad_right" and self.state != "MENU":
                if payload.get("cursorPosition") is not None:
                    self.cursor_position = int(payload.get("cursorPosition"))
                else:
                    self.cursor_position = min(len(self.expression), self.cursor_position + 1)
                self._update_viewport()
                return self._state()

            if key == "equals" or (key == "dpad_center" and self.state == "MENU"):
                if self.state == "MENU":
                    # Canonical cursor comes from the frontend payload; adopt it
                    # so MENU + D-pad + equals/center confirms the visible selection.
                    # (The physical unit has no center key; center is confirm-only.)
                    self._sync_menu_from_payload(payload)
                    return self._enter_selected_mode()

                eval_expr = str(expr_override if expr_override is not None else self.expression)
                # Complex mode: replace standalone i with j for Python's complex literal
                if self.mode_name == "Complex":
                    eval_expr = re.sub(r'(?<![a-zA-Z])i(?![a-zA-Z0-9])', 'j', eval_expr)
                # Base-N mode: evaluate in the selected base
                if self.mode_name == "Base-N":
                    try:
                        result_str = evaluate_base_n(eval_expr, self.base_n_base)
                        self.last_result = result_str
                        self.ans = result_str
                        self.result_displayed = True
                        self.shift = False
                        self.alpha = False
                        self.state = "RESULT"
                        return self._state(display=self._display(result_str))
                    except ZeroDivisionError:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        return self._state(False, DIV_ZERO_MSG, DIV_ZERO_MSG)
                    except Exception:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        return self._state(False, "Math ERROR", "Math ERROR")
                self.expression = eval_expr

                try:
                    ans_float = float(self.ans) if self.ans is not None else 0.0
                except (ValueError, TypeError):
                    ans_float = 0.0

                # Matrix/Vector-mode expressions use the dedicated typed parser.
                mv_probe = eval_expr.replace('×', '*').replace('÷', '/').replace('−', '-')
                mv_probe = re.sub(r'(\d|\))(?=Mat[ABCD]|Vct[ABCD])', r'\1*', mv_probe)
                if _contains_matvec(mv_probe):
                    try:
                        angle_u = self.setup_settings["angle_unit"]
                        kind, mval = evaluate_matvec_expression(
                            mv_probe, self.matrices, self.vectors,
                            angle_u, self.variables, ans_float)
                        formatted = self._matvec_result(kind, mval)
                        return self._store_matvec_answer(kind, mval, formatted)
                    except ZeroDivisionError:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        return self._state(False, DIV_ZERO_MSG, DIV_ZERO_MSG)
                    except ValueError as exc:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        msg = "Dimension ERROR" if "Dimension" in str(exc) else "Math ERROR"
                        return self._state(False, msg, msg)
                    except Exception:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        return self._state(False, "Math ERROR", "Math ERROR")

                try:
                    # Evaluate with safe mathematical evaluator
                    angle_u = self.setup_settings["angle_unit"]
                    res_val = safe_evaluate_expression(eval_expr, ans_float, angle_u, self.variables, self.mode_name == "Complex", self._rnd_setting())
                    if isinstance(res_val, complex):
                        if abs(res_val.imag) < 1e-14:
                            res_val = float(res_val.real)
                        elif self.mode_name != "Complex":
                            # Physical unit: non-Complex modes reject complex
                            # results with Math ERROR.
                            raise ValueError("Math ERROR")
                    self.last_result = self._format_result(res_val)
                    self.ans = self.last_result
                    self.result_displayed = True
                    self.shift = False
                    self.alpha = False
                    self.state = "RESULT"
                    return self._state(display=self._display(self.last_result))
                except ZeroDivisionError:
                    self.shift = False
                    self.alpha = False
                    self.state = "ERROR"
                    return self._state(False, DIV_ZERO_MSG, DIV_ZERO_MSG)
                except Exception:
                    # Fallback to engine.evaluate
                    try:
                        res_val = self.engine.evaluate(eval_expr)
                        self.last_result = self._format_result(res_val)
                        self.ans = self.last_result
                        self.result_displayed = True
                        self.shift = False
                        self.alpha = False
                        self.state = "RESULT"
                        return self._state(display=self._display(self.last_result))
                    except ZeroDivisionError:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        return self._state(False, DIV_ZERO_MSG, DIV_ZERO_MSG)
                    except Exception:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        return self._state(False, "Math ERROR", "Math ERROR")

            if key in {"menu", "setup"} and action.upper() != "SETUP":
                if self.state == "MENU":
                    return self._state()
                self.state = "MENU"
                return self._state()

            if self.state == "MENU" and key.isdigit():
                # Canonical resolution: the frontend sends its menuPage with
                # every request. Physical keys "1"-"4" on page 2 collide with
                # page-1 digits, so disambiguate via the payload first.
                try:
                    frontend_page = int(payload.get("menuPage", 0))
                except (ValueError, TypeError):
                    frontend_page = 0
                if frontend_page == 2 and key in {"1", "2", "3", "4"}:
                    self.menu_page = 2
                    self.menu_index = int(key) - 1
                    return self._enter_selected_mode()
                for page_number, page_items in enumerate(MENU_PAGES, start=1):
                    for item_index, (number, _) in enumerate(page_items):
                        if number == key:
                            self.menu_page = page_number
                            self.menu_index = item_index
                            return self._enter_selected_mode()

            if key in {"dpad_up", "dpad_down", "dpad_left", "dpad_right"} and self.state == "MENU":
                # Single canonical cursor: the frontend already moved its
                # cursor locally and sends the new position in the payload.
                # Adopt it directly instead of moving a second competing
                # cursor (which caused off-by-one/stale confirms).
                if self._sync_menu_from_payload(payload):
                    self.state = "MENU"
                    return self._state()
                self._move_menu(key)
                self.state = "MENU"
                return self._state()

            if key in {"dpad_center", "dpad_up", "dpad_down"}:
                return self._state()

            if expr_override is not None:
                self.expression = str(expr_override)
                self.cursor_position = int(payload.get("cursorPosition", len(self.expression)))
                self._update_viewport()
                self.state = "INPUT"
                self.result_displayed = False
                self.last_result = None
                self.shift = False
                self.alpha = False
                return self._state()

            # FIX 1/3: explicit base_switch key sent from frontend SHIFT-path handlers
            if key == "base_switch" and self.mode_name == "Base-N":
                new_base = int(payload.get("base", 10))
                if self.result_displayed and self.last_result is not None:
                    converted = self._convert_base(self.last_result, self.base_n_base, new_base)
                    self.last_result = converted
                    self.ans = converted
                self.base_n_base = new_base
                self.shift = False
                self.alpha = False
                return self._state()

            if self.mode_name == "Base-N":
                token = self._token_for(key)
                if token and token.startswith("__BASE_SWITCH__"):
                    base_name = token.split("__")[2]
                    base_map = {"DEC": 10, "HEX": 16, "BIN": 2, "OCT": 8}
                    new_base = base_map.get(base_name, 10)
                    # FIX 3: Convert displayed result to new base before switching
                    if self.result_displayed and self.last_result is not None:
                        converted = self._convert_base(self.last_result, self.base_n_base, new_base)
                        self.last_result = converted
                        self.ans = converted
                    self.base_n_base = new_base
                    self.shift = False
                    self.alpha = False
                    return self._state()
                # fall through to normal token handling below

            token = self._token_for(key)
            if token:
                self.undo_stack.append({
                    "expression": self.expression,
                    "cursor_position": self.cursor_position,
                    "result_displayed": self.result_displayed,
                    "last_result": self.last_result,
                })
                if self.result_displayed:
                    self.expression = ""
                    self.cursor_position = 0
                    self.last_result = None
                    self.result_displayed = False
                if self.insert_mode:
                    self.expression = (self.expression[:self.cursor_position] + token +
                                       self.expression[self.cursor_position:])
                elif self.cursor_position < len(self.expression):
                    self.expression = (self.expression[:self.cursor_position] + token +
                                       self.expression[self.cursor_position + 1:])
                else:
                    self.expression = (self.expression[:self.cursor_position] + token +
                                       self.expression[self.cursor_position:])
                self.cursor_position += len(token)
                self._update_viewport()
                self.state = "INPUT"

            self.shift = False
            self.alpha = False
            return self._state()
        except ZeroDivisionError:
            self.shift = False
            self.alpha = False
            self.state = "ERROR"
            return self._state(False, "Math ERROR", "Math ERROR")
        except Exception as exc:
            print(f"calculator key error for {key!r}: {exc}", file=sys.stderr)
            self.shift = False
            self.alpha = False
            self.state = "ERROR"
            return self._state(False, "Math ERROR", "Math ERROR")

    def _return_to_editing(self):
        if self.result_displayed:
            self.result_displayed = False
            self.last_result = None
            self.state = "INPUT"
            self.cursor_position = len(self.expression)
            self._update_viewport()

    def _update_viewport(self):
        visible_width = 22
        self.expression_viewport = max(0, min(self.expression_viewport,
                                              max(0, len(self.expression) - visible_width)))
        if self.cursor_position < self.expression_viewport:
            self.expression_viewport = self.cursor_position
        elif self.cursor_position > self.expression_viewport + visible_width:
            self.expression_viewport = self.cursor_position - visible_width


CONTROLLER = CalculatorController()
CONTROLLER_LOCK = threading.Lock()


class MvpHandler(BaseHTTPRequestHandler):
    server_version = "ClassWizMVP/1.0"

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid JSON") from exc
        if length > 64 * 1024:
            raise ValueError("request too large")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")
        return payload

    def _validate_required_fields(self, path, payload):
        required = {
            "/api/evaluate": {"expression": str},
            "/api/equation": {"coefficients": list, "degree": int},
            "/api/spreadsheet": {"cell": str, "value": str},
            "/api/distribution": {"type": str, "params": dict},
            "/api/matrix": {"operation": str},
            "/api/statistics": {"data": list},
            # Concrete route names currently used by frontend.html.
            "/api/equation/solve": {"coefficients": list},
            "/api/spreadsheet/set": {"cell": str, "value": str},
            "/api/distribution/calculate": {"type": (int, str), "params": dict},
            "/api/statistics/set": {"data": list},
            "/api/statistics/calculate": {"data": list},
        }
        if path == "/api/equation/solve":
            required[ path ]["degree"] = int
            if "degree" not in payload and "count" in payload:
                required[path].pop("degree")
                required[path]["count"] = int
        checks = required.get(path)
        if checks is None:
            return None
        for name, expected_type in checks.items():
            value = payload.get(name)
            valid = name in payload and isinstance(value, expected_type)
            if expected_type is int and isinstance(value, bool):
                valid = False
            if not valid:
                return f"Missing field: {name}"
        return None

    def do_GET(self):
        path = unquote(urlparse(self.path).path)

        if path in {"/", "/frontend.html"}:
            body = (PROJECT_ROOT / "frontend.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Static font files
        if path.startswith("/fonts/") or path.startswith("/ClassWizFontSet/") or path.startswith("/raw_assets/ClassWizFontSet/"):
            font_filename = Path(path).name
            candidates = [
                PROJECT_ROOT / "ClassWizFontSet" / font_filename,
                PROJECT_ROOT / font_filename,
            ]
            for candidate in candidates:
                if candidate.exists() and candidate.is_file():
                    body = candidate.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "font/ttf")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(body)
                    return
            self._send_json({"ok": False, "error": f"Font file '{font_filename}' not found"}, 404)
            return

        if path == "/health":
            self._send_json({"ok": True})
            return

        if path == "/api/settings":
            self._send_json({"ok": True, "settings": CONTROLLER.get_settings()})
            return

        if path == "/setup_get":
            self._send_json({"settings": dict(CONTROLLER.setup_settings)})
            return

        if path in {"/api/spreadsheet", "/api/spreadsheet/get"}:
            self._send_json(CONTROLLER.get_spreadsheet())
            return

        if path in {"/api/variables", "/api/variables/get"}:
            self._send_json(CONTROLLER.get_variables())
            return

        self._send_json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._send_json({"ok": False, "error": "Content-Type must be application/json"}, 400)
            return
        try:
            payload = self._read_json()
            validation_error = self._validate_required_fields(path, payload)
            if validation_error:
                self._send_json({"ok": False, "error": validation_error}, 422)
                return
            with CONTROLLER_LOCK:
                if path == "/api/key":
                    response = CONTROLLER.press_key(payload)
                elif path == "/api/evaluate":
                    payload["key"] = "equals"
                    response = CONTROLLER.press_key(payload)
                elif path == "/api/fraction":
                    if "value" not in payload:
                        response = {"ok": False, "error": "missing value"}
                    else:
                        value = float(payload["value"])
                        mixed = bool(payload.get("mixed", False))
                        frac = Fraction(value).limit_denominator(10000)
                        if frac.denominator == 1:
                            result = str(frac.numerator)
                        elif mixed and abs(frac.numerator) > frac.denominator:
                            whole = int(frac.numerator / frac.denominator)
                            remainder = abs(frac.numerator) % frac.denominator
                            result = f"{whole} {remainder}/{frac.denominator}" if remainder else str(whole)
                        else:
                            result = f"{frac.numerator}/{frac.denominator}"
                        response = {"result": result, "success": True, "ok": True}
                elif path == "/api/settings":
                    response = CONTROLLER.set_settings(payload)
                elif path == "/setup_update":
                    response = CONTROLLER.update_setup_setting(payload.get("key"), payload.get("value"))
                elif path == "/api/matrix/set":
                    matrix_name = payload.get("matrix", "")
                    rows = payload.get("rows", 0)
                    cols = payload.get("cols", 0)
                    data = payload.get("data", [])
                    response = CONTROLLER.set_matrix(matrix_name, rows, cols, data)
                elif path == "/api/vector/set":
                    vector_name = payload.get("vector", "")
                    dim = payload.get("dim", 0)
                    data = payload.get("data", [])
                    response = CONTROLLER.set_vector(vector_name, dim, data)
                elif path == "/api/statistics/set":
                    stat_type = payload.get("type", 0)
                    data = payload.get("data", [])
                    response = CONTROLLER.set_statistics(stat_type, data)
                elif path == "/api/statistics/calculate":
                    response = CONTROLLER.calculate_statistics(payload.get("type", 0), payload.get("data", []))
                elif path == "/api/distribution/calculate":
                    dist_type = payload.get("type", 0)
                    params = payload.get("params", {})
                    response = CONTROLLER.calculate_distribution(dist_type, params)
                elif path == "/api/table/calculate":
                    response = CONTROLLER.calculate_table(payload.get("expression", ""), payload.get("start"), payload.get("end"), payload.get("step"))
                elif path == "/api/equation/solve":
                    response = CONTROLLER.solve_equation(payload.get("kind", "polynomial"), payload.get("coefficients", []), payload.get("count", payload.get("degree", 2)))
                elif path == "/api/inequality/solve":
                    response = CONTROLLER.solve_inequality(payload.get("degree", 2), payload.get("operator", ">"), payload.get("coefficients", []))
                elif path in {"/api/spreadsheet", "/api/spreadsheet/get"}:
                    response = CONTROLLER.get_spreadsheet()
                elif path == "/api/spreadsheet/set":
                    ref = payload.get("cell", payload.get("cell_ref", ""))
                    val = payload.get("value", payload.get("formula", payload.get("val", "")))
                    response = CONTROLLER.set_spreadsheet_cell(ref, val)
                elif path == "/api/spreadsheet/clear":
                    response = CONTROLLER.clear_spreadsheet()
                elif path == "/api/matrix/calculate":
                    response = CONTROLLER.calculate_matrix(
                        payload.get("op", payload.get("operation", "")),
                        payload.get("a", payload.get("matrix", payload.get("A"))),
                        payload.get("b", payload.get("B")),
                        payload.get("scalar", payload.get("k")),
                        payload.get("n", payload.get("size")))
                elif path == "/api/vector/calculate":
                    response = CONTROLLER.calculate_vector(
                        payload.get("op", payload.get("operation", "")),
                        payload.get("a", payload.get("vector", payload.get("A"))),
                        payload.get("b", payload.get("B")),
                        payload.get("scalar", payload.get("k")))
                elif path == "/api/ratio/calculate":
                    t = payload.get("type", payload.get("ratio_type", 1))
                    a = payload.get("a", 0)
                    b = payload.get("b", 0)
                    c_or_d = payload.get("c", payload.get("d", payload.get("c_or_d", 0)))
                    response = CONTROLLER.calculate_ratio(t, a, b, c_or_d)
                elif path == "/api/convert":
                    cat = payload.get("category", "Length")
                    fu = payload.get("from", payload.get("from_unit", ""))
                    tu = payload.get("to", payload.get("to_unit", ""))
                    val = payload.get("value", payload.get("val", 0.0))
                    response = CONTROLLER.convert_units_calc(cat, fu, tu, val)
                elif path == "/api/reset":
                    target = payload.get("target", payload.get("reset", "all"))
                    response = CONTROLLER.reset_calculator(target)
                elif path == "/api/calc":
                    response = CONTROLLER.calc_evaluate(payload.get("expression", ""), payload.get("values", payload.get("variables")))
                elif path == "/api/solve":
                    response = CONTROLLER.solve_equation_newton(payload.get("expression", ""), payload.get("variable", "X"), payload.get("guess", payload.get("x0", 0.0)))
                elif path in {"/api/variables", "/api/variables/set"}:
                    if "name" in payload or "variable" in payload:
                        response = CONTROLLER.set_variable(payload.get("name", payload.get("variable")), payload.get("value", 0))
                    else:
                        response = CONTROLLER.get_variables()
                else:
                    self._send_json({"ok": False, "error": "not found"}, 404)
                    return
            error_text = str(response.get("error", ""))
            if error_text == "Invalid cell reference" or error_text == "Formula error" or error_text.startswith("Invalid value for setting:"):
                status = 422
            else:
                status = 200 if response.get("ok") or response.get("success") else 400
            self._send_json(response, status)
        except ValueError as exc:
            message = str(exc)
            if message not in {"Invalid JSON", "Payload must be a JSON object"}:
                message = "Invalid JSON"
            self._send_json({"ok": False, "error": message}, 400)
        except Exception as exc:
            print(f"request error: {exc}", file=sys.stderr)
            self._send_json({"ok": False, "error": "invalid request"}, 400)

    def log_message(self, format, *args):
        # Concise logging
        pass


def main():
    parser = argparse.ArgumentParser(description="Run the local ClassWiz browser MVP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MvpHandler)
    url = f"http://{args.host}:{server.server_port}/"
    print(f"ClassWiz browser MVP: {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping ClassWiz browser MVP")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
