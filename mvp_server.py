"""Local browser MVP server for the ClassWiz HTML frontend."""

from __future__ import annotations

import argparse
import json
import cmath
import math
import mimetypes
import os
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent

from engine.engine import Engine
from engine.calculus.calculus_engine import CalculusEngine
from engine.spreadsheet.spreadsheet_engine import SpreadsheetEngine

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

_SPECIAL_FUNCS = ('integral', 'log_base', 'xroot', 'cbrt', 'sqrt')


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


def _transform_special_functions(s: str, ans_val: float, angle_unit: str = "Degree") -> str:
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
            a_val = safe_evaluate_expression(args[1], ans_val, angle_unit)
            b_val = safe_evaluate_expression(args[2], ans_val, angle_unit)

            def integrand_func(x):
                sub_expr = re.sub(r'\bx\b', f'({x})', integrand_str)
                return safe_evaluate_expression(sub_expr, ans_val, angle_unit)

            res = CALC_ENGINE.integrate(integrand_func, a_val, b_val)
            replacement = f'({float(res)!r})'
        elif name == 'log_base':
            if len(args) != 2 or not all(args):
                raise ValueError("Math ERROR: log_base expects 2 arguments")
            base = safe_evaluate_expression(args[0], ans_val, angle_unit)
            value = safe_evaluate_expression(args[1], ans_val, angle_unit)
            replacement = f'({math.log(value) / math.log(base)!r})'
        elif name == 'xroot':
            if len(args) != 2 or not all(args):
                raise ValueError("Math ERROR: xroot expects 2 arguments")
            n_val = safe_evaluate_expression(args[0], ans_val, angle_unit)
            radicand = safe_evaluate_expression(args[1], ans_val, angle_unit)
            replacement = f'({radicand ** (1 / n_val)!r})'
        elif name == 'cbrt':
            if len(args) != 1 or not args[0]:
                raise ValueError("Math ERROR: cbrt expects 1 argument")
            replacement = f'({safe_evaluate_expression(args[0], ans_val, angle_unit) ** (1 / 3)!r})'
        else:  # sqrt
            if len(args) != 1 or not args[0]:
                raise ValueError("Math ERROR: sqrt expects 1 argument")
            replacement = f'({math.sqrt(safe_evaluate_expression(args[0], ans_val, angle_unit))!r})'

        s = s[:start] + replacement + s[close_idx + 1:]


def safe_evaluate_expression(expr_str: str, ans_val: float = 0.0, angle_unit: str = "Degree") -> float:
    """Evaluate mathematical expressions with scientific functions, roots, powers, and integrals."""
    s = expr_str.strip()
    if not s:
        return 0.0

    # Replace display / shorthand symbols
    s = s.replace('π', f'({math.pi})').replace('pi', f'({math.pi})')
    s = s.replace('×', '*').replace('÷', '/').replace('−', '-')
    s = s.replace('Ans', f'({ans_val})').replace('ans', f'({ans_val})')

    # Handle supported special functions (integral, log_base, xroot, cbrt, sqrt)
    s = _transform_special_functions(s, ans_val, angle_unit)

    # Powers ^ -> **
    s = s.replace('^', '**')

    # Factorials n! -> math.factorial(n)
    s = re.sub(r'(\d+)!', r'math.factorial(\1)', s)

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

    # Prepare safe evaluation namespace
    math_ns = {
        'math': math,
        'sin': _safe_sin,
        'cos': _safe_cos,
        'tan': _safe_tan,
        'asin': _safe_asin,
        'acos': _safe_acos,
        'atan': _safe_atan,
        'sinh': cmath.sinh,
        'cosh': cmath.cosh,
        'tanh': cmath.tanh,
        'sqrt': cmath.sqrt,
        'log': cmath.log10,
        'log10': cmath.log10,
        'ln': cmath.log,
        'exp': cmath.exp,
        'abs': abs,
        'Abs': abs,
        'e': math.e,
        'pi': math.pi,
        'round': round,
        'j': complex(0, 1),
    }

    try:
        val = eval(s, {'__builtins__': {}}, math_ns)
        if isinstance(val, complex):
            if abs(val.imag) < 1e-14:
                return float(val.real)
            return val
        return float(val)
    except ZeroDivisionError:
        raise
    except Exception as exc:
        raise ValueError(f"Math ERROR: {exc}")


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

    if base == 2:
        return bin(int_result)[2:]       # strip '0b' prefix
    elif base == 8:
        return oct(int_result)[2:]       # strip '0o' prefix
    elif base == 16:
        return hex(int_result)[2:].upper()  # strip '0x' prefix
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


class CalculatorController:
    def __init__(self) -> None:
        self.engine = Engine()
        self.expression = ""
        self.cursor_position = 0
        self.last_result = None
        self.result_displayed = False
        self.expression_viewport = 0
        self.ans = "0"
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
        self.settings = dict(DEFAULT_SETTINGS)
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
        self.spreadsheet_engine = SpreadsheetEngine()
        self.ratio = {"type": 1, "a": None, "b": None, "c_or_d": None, "x": None}
        self.variables = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0, "F": 0.0, "x": 0.0, "y": 0.0, "M": 0.0}

    def get_settings(self) -> dict:
        return dict(self.settings)

    def set_settings(self, new_settings: dict) -> dict:
        if not isinstance(new_settings, dict):
            return {"ok": False, "success": False, "error": "Settings must be a JSON object"}

        valid_io = {"MathI/MathO", "MathI/DecimalO", "LineI/LineO", "LineI/DecimalO"}
        valid_angle = {"Degree", "Radian", "Gradian"}
        valid_num_fmt = {"Fix", "Sci", "Norm"}
        valid_frac = {"ab/c", "d/c"}
        valid_show_cell = {"Value", "Formula"}

        updated = dict(self.settings)

        # inputOutput / input_output
        io_val = new_settings.get("inputOutput", new_settings.get("input_output"))
        if io_val is not None:
            io_val = str(io_val).strip()
            if io_val not in valid_io:
                return {"ok": False, "success": False, "error": f"Invalid inputOutput: {io_val}"}
            updated["inputOutput"] = io_val

        # angleUnit / angle_unit
        au_val = new_settings.get("angleUnit", new_settings.get("angle_unit"))
        if au_val is not None:
            au_val = str(au_val).strip()
            if au_val not in valid_angle:
                return {"ok": False, "success": False, "error": f"Invalid angleUnit: {au_val}"}
            updated["angleUnit"] = au_val

        # numberFormat / number_format
        nf_val = new_settings.get("numberFormat", new_settings.get("number_format"))
        if nf_val is not None:
            nf_val = str(nf_val).strip()
            if nf_val not in valid_num_fmt:
                return {"ok": False, "success": False, "error": f"Invalid numberFormat: {nf_val}"}
            updated["numberFormat"] = nf_val

        # numberFormatPrecision / number_format_precision
        nfp_val = new_settings.get("numberFormatPrecision", new_settings.get("number_format_precision"))
        if nfp_val is not None:
            try:
                p = int(nfp_val)
                if not (0 <= p <= 9):
                    return {"ok": False, "success": False, "error": f"Precision must be between 0 and 9: {p}"}
                updated["numberFormatPrecision"] = p
            except (ValueError, TypeError):
                return {"ok": False, "success": False, "error": "Invalid precision"}

        # engineeringSymbols / engineering_symbols
        es_val = new_settings.get("engineeringSymbols", new_settings.get("engineering_symbols"))
        if es_val is not None:
            updated["engineeringSymbols"] = bool(es_val)

        # fractionResult / fraction_result
        fr_val = new_settings.get("fractionResult", new_settings.get("fraction_result"))
        if fr_val is not None:
            fr_val = str(fr_val).strip()
            if fr_val not in valid_frac:
                return {"ok": False, "success": False, "error": f"Invalid fractionResult: {fr_val}"}
            updated["fractionResult"] = fr_val

        # statisticsFrequency / statistics_frequency
        sf_val = new_settings.get("statisticsFrequency", new_settings.get("statistics_frequency"))
        if sf_val is not None:
            updated["statisticsFrequency"] = bool(sf_val)

        # autoCalc / auto_calc
        ac_val = new_settings.get("autoCalc", new_settings.get("auto_calc"))
        if ac_val is not None:
            updated["autoCalc"] = bool(ac_val)

        # showCell / show_cell
        sc_val = new_settings.get("showCell", new_settings.get("show_cell"))
        if sc_val is not None:
            sc_val = str(sc_val).strip()
            if sc_val not in valid_show_cell:
                return {"ok": False, "success": False, "error": f"Invalid showCell: {sc_val}"}
            updated["showCell"] = sc_val

        self.settings = updated
        return {"ok": True, "success": True, "settings": dict(self.settings)}

    def set_matrix(self, matrix_name: str, rows: int, cols: int, data: list) -> dict:
        name = str(matrix_name).strip().upper()
        if name not in {"A", "B", "C", "D"}:
            return {"ok": False, "success": False, "error": f"Invalid matrix name '{matrix_name}'. Must be A, B, C, or D."}
        try:
            rows_int = int(rows)
            cols_int = int(cols)
        except (ValueError, TypeError):
            return {"ok": False, "success": False, "error": "Rows and cols must be integers."}
        if not (1 <= rows_int <= 4 and 1 <= cols_int <= 4):
            return {"ok": False, "success": False, "error": "Matrix dimensions must be between 1x1 and 4x4."}
        if not isinstance(data, list) or len(data) != rows_int:
            return {"ok": False, "success": False, "error": f"Data row count ({len(data) if isinstance(data, list) else 0}) does not match rows ({rows_int})."}
        cleaned_data = []
        for r_idx, row in enumerate(data):
            if not isinstance(row, list) or len(row) != cols_int:
                return {"ok": False, "success": False, "error": f"Data col count at row {r_idx} does not match cols ({cols_int})."}
            cleaned_row = []
            for val in row:
                try:
                    f_val = float(val) if val not in ("", None) else 0.0
                    cleaned_row.append(int(f_val) if f_val.is_integer() else f_val)
                except (ValueError, TypeError):
                    return {"ok": False, "success": False, "error": f"Invalid numeric value in matrix data: {val!r}"}
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
            return {"ok": False, "success": False, "error": f"Invalid vector name '{vector_name}'. Must be A, B, C, or D."}
        try:
            dim_int = int(dim)
        except (ValueError, TypeError):
            return {"ok": False, "success": False, "error": "Dim must be an integer."}
        if not (1 <= dim_int <= 4):
            return {"ok": False, "success": False, "error": "Vector dimension must be between 1 and 4."}
        if not isinstance(data, list) or len(data) != dim_int:
            return {"ok": False, "success": False, "error": f"Data length ({len(data) if isinstance(data, list) else 0}) does not match dim ({dim_int})."}
        cleaned = []
        for val in data:
            try:
                f_val = float(val) if val not in ("", None) else 0.0
                cleaned.append(int(f_val) if isinstance(f_val, float) and f_val.is_integer() else f_val)
            except (ValueError, TypeError):
                return {"ok": False, "success": False, "error": f"Invalid numeric value: {val!r}"}
        self.vectors[name] = {"dim": dim_int, "data": cleaned}
        return {"ok": True, "success": True}

    def set_statistics(self, stat_type: int, data: list) -> dict:
        try:
            t = int(stat_type)
        except (ValueError, TypeError):
            return {"ok": False, "success": False, "error": "Type must be an integer 1-8."}
        if not (1 <= t <= 8):
            return {"ok": False, "success": False, "error": "Statistics type must be 1-8."}
        if not isinstance(data, list):
            return {"ok": False, "success": False, "error": "Data must be a list."}
        is_one_var = (t == 1)
        cleaned = []
        for i, row in enumerate(data):
            if not isinstance(row, dict):
                return {"ok": False, "success": False, "error": f"Row {i} must be a dict."}
            try:
                x_val = float(row.get("x", 0))
            except (ValueError, TypeError):
                return {"ok": False, "success": False, "error": f"Invalid x at row {i}."}
            if is_one_var:
                cleaned.append({"x": x_val})
            else:
                try:
                    y_val = float(row.get("y", 0))
                except (ValueError, TypeError):
                    return {"ok": False, "success": False, "error": f"Invalid y at row {i}."}
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
            return {"ok": False, "success": False, "error": f"Math ERROR: {exc}"}

    def calculate_table(self, expr: str, x_start: float, x_end: float, x_step: float) -> dict:
        try:
            self.engine.set_mode("TABLE")
            # The calculator editor emits ^ notation; TableEngine evaluates
            # Python expressions and therefore needs exponentiation as **.
            self.engine.table_set_f(str(expr).replace("^", "**"))
            return {"ok": True, "success": True, "rows": self.engine.table_generate(float(x_start), float(x_end), float(x_step))}
        except Exception as exc:
            return {"ok": False, "success": False, "error": f"Math ERROR: {exc}"}

    def solve_equation(self, kind: str, coefficients, count_or_degree: int) -> dict:
        try:
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
            return {"ok": True, "success": True, "result": json_safe(result)}
        except Exception as exc:
            return {"ok": False, "success": False, "error": f"Math ERROR: {exc}"}

    def solve_inequality(self, degree: int, operator: str, coefficients: list) -> dict:
        try:
            self.engine.set_mode("INEQUALITY")
            vals = [float(v) for v in coefficients]
            op = operator.replace(" 0", "").strip()
            if int(degree) == 2: self.engine.inequality_set_quadratic(*vals, operator=op)
            elif int(degree) == 3: self.engine.inequality_set_cubic(*vals, operator=op)
            elif int(degree) == 4: self.engine.inequality_set_quartic(*vals, operator=op)
            else: raise ValueError("degree must be 2-4")
            return {"ok": True, "success": True, "result": self.engine.inequality_solve(), "solution": self.engine.inequality_solution_as_string()}
        except Exception as exc:
            return {"ok": False, "success": False, "error": f"Math ERROR: {exc}"}

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
                return {"ok": False, "success": False, "error": f"Invalid distribution type {t}"}
            formatted = self._format_result(result)
            self.distribution = {"type": t, "params": params, "result": formatted}
            return {"ok": True, "success": True, "result": formatted}
        except KeyError as exc:
            return {"ok": False, "success": False, "error": f"Missing parameter: {exc}"}
        except Exception as exc:
            return {"ok": False, "success": False, "error": f"Math ERROR: {exc}"}

    def set_spreadsheet_cell(self, cell_ref: str, value: str) -> dict:
        ref = str(cell_ref).strip().upper()
        if not ref:
            return {"ok": False, "success": False, "error": "Invalid cell reference"}
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
        except Exception as exc:
            formatted_computed = "ERROR"

        self.spreadsheet[ref] = {
            "raw": val_str,
            "value": formatted_computed if val_str.startswith("=") else val_str,
            "formula": val_str if val_str.startswith("=") else ""
        }
        if self.settings.get("autoCalc", True):
            self.eval_spreadsheet()

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
                pass
        for ref, item in list(self.spreadsheet.items()):
            raw = item.get("raw", item.get("value", ""))
            try:
                computed = self.spreadsheet_engine.get_cell_value(ref)
                res_fmt = self._format_result(computed) if computed is not None else ""
            except Exception:
                res_fmt = "ERROR"
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
            return {"ok": False, "success": False, "error": "Math ERROR"}
        except Exception as exc:
            return {"ok": False, "success": False, "error": f"Math ERROR: {exc}"}

    def convert_units_calc(self, category: str, from_unit: str, to_unit: str, value: float) -> dict:
        try:
            val = float(value)
            res = _convert_units(category, from_unit, to_unit, val)
            formatted = self._format_result(res)
            return {"ok": True, "success": True, "result": formatted, "numericResult": res}
        except Exception as exc:
            return {"ok": False, "success": False, "error": f"Conversion ERROR: {exc}"}

    def get_constants(self) -> dict:
        return {"ok": True, "success": True, "constants": SCIENTIFIC_CONSTANTS}

    def reset_calculator(self, target: str) -> dict:
        t = str(target).strip().lower()
        if t in ("setup", "setup_data"):
            self.settings = dict(DEFAULT_SETTINGS)
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
            self.settings = dict(DEFAULT_SETTINGS)
            self.ans = "0"
            self.variables = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0, "F": 0.0, "x": 0.0, "y": 0.0, "M": 0.0}
            self.matrices = {k: {"rows": 0, "cols": 0, "data": []} for k in ("A", "B", "C", "D")}
            self.vectors = {k: {"dim": 0, "data": []} for k in ("A", "B", "C", "D")}
            self.statistics = {"type": 0, "data": []}
            self.distribution = {"type": 0, "params": {}, "result": None}
            self.spreadsheet = {}
            self.spreadsheet_engine.clear_all()
            self.ratio = {"type": 1, "a": None, "b": None, "c_or_d": None, "x": None}
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
            return {"ok": False, "success": False, "error": f"Unknown reset target: {target}"}

    def _convert_base(self, value_str, from_base, to_base):
        try:
            decimal_val = int(str(value_str).strip(), from_base)
            if to_base == 10:
                return str(decimal_val)
            elif to_base == 2:
                return bin(decimal_val)[2:]
            elif to_base == 8:
                return oct(decimal_val)[2:]
            elif to_base == 16:
                return hex(decimal_val)[2:].upper()
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
        if self.mode_name == "Base-N":
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
                "integral": "sigma(", "variable": "diff(",
            }.get(key, "")
        if self.alpha:
            return {
                "negate": "A", "ellipsis": "B", "inverse": "C",
                "sin": "D", "cos": "E", "tan": "F",
                "right_paren": "x", "s_to_d": "y", "m_plus": "M",
                "scientific": "e", "ans": "e", "decimal": "RanInt(",
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

            if key == "equals":
                if self.state == "MENU":
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
                        return self._state(display=result_str)
                    except ZeroDivisionError:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        return self._state(False, "Math ERROR", "Math ERROR")
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

                try:
                    # Evaluate with safe mathematical evaluator
                    angle_u = self.settings.get("angleUnit", self.settings.get("angle_unit", "Degree"))
                    res_val = safe_evaluate_expression(eval_expr, ans_float, angle_u)
                    self.last_result = self._format_result(res_val)
                    self.ans = self.last_result
                    self.result_displayed = True
                    self.shift = False
                    self.alpha = False
                    self.state = "RESULT"
                    return self._state(display=self.last_result)
                except ZeroDivisionError:
                    self.shift = False
                    self.alpha = False
                    self.state = "ERROR"
                    return self._state(False, "Math ERROR", "Math ERROR")
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
                        return self._state(display=self.last_result)
                    except ZeroDivisionError:
                        self.shift = False
                        self.alpha = False
                        self.state = "ERROR"
                        return self._state(False, "Math ERROR", "Math ERROR")
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
                for page_number, page_items in enumerate(MENU_PAGES, start=1):
                    for item_index, (number, _) in enumerate(page_items):
                        if number == key:
                            self.menu_page = page_number
                            self.menu_index = item_index
                            return self._enter_selected_mode()

            if key in {"dpad_up", "dpad_down", "dpad_left", "dpad_right"} and self.state == "MENU":
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
        length = int(self.headers.get("Content-Length", "0"))
        if length > 64 * 1024:
            raise ValueError("request too large")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

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

        if path == "/api/state":
            self._send_json(CONTROLLER.get_state())
            return

        if path == "/api/settings":
            self._send_json({"ok": True, "settings": CONTROLLER.get_settings()})
            return

        if path == "/api/constants":
            self._send_json(CONTROLLER.get_constants())
            return

        if path in {"/api/spreadsheet", "/api/spreadsheet/get"}:
            self._send_json(CONTROLLER.get_spreadsheet())
            return

        self._send_json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            with CONTROLLER_LOCK:
                if path == "/api/key":
                    response = CONTROLLER.press_key(payload)
                elif path == "/api/mode":
                    response = CONTROLLER.set_mode(payload.get("mode", ""), payload.get("number", ""))
                elif path == "/api/settings":
                    response = CONTROLLER.set_settings(payload)
                elif path == "/api/calculate":
                    payload["key"] = "equals"
                    response = CONTROLLER.press_key(payload)
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
                elif path in {"/api/constants"}:
                    response = CONTROLLER.get_constants()
                elif path in {"/api/spreadsheet", "/api/spreadsheet/get"}:
                    response = CONTROLLER.get_spreadsheet()
                elif path == "/api/spreadsheet/set":
                    ref = payload.get("cell", payload.get("cell_ref", ""))
                    val = payload.get("value", payload.get("formula", payload.get("val", "")))
                    response = CONTROLLER.set_spreadsheet_cell(ref, val)
                elif path == "/api/spreadsheet/eval":
                    response = CONTROLLER.eval_spreadsheet()
                elif path == "/api/spreadsheet/clear":
                    response = CONTROLLER.clear_spreadsheet()
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
                else:
                    self._send_json({"ok": False, "error": "not found"}, 404)
                    return
            self._send_json(response, 200 if response.get("ok") or response.get("success") else 400)
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
