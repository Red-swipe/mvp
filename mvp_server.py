"""Local browser MVP server for the ClassWiz HTML frontend."""

from __future__ import annotations

import argparse
import json
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


def safe_evaluate_expression(expr_str: str, ans_val: float = 0.0) -> float:
    """Evaluate mathematical expressions with scientific functions, roots, powers, and integrals."""
    s = expr_str.strip()
    if not s:
        return 0.0

    # Quick check for division by zero literal patterns
    # e.g., /0, /(0), /(0.0), / 0
    if re.search(r'/\s*\(?\s*0(?:\.0*)?\s*\)?(?!\d)', s):
        raise ZeroDivisionError("division by zero")

    # Replace display / shorthand symbols
    s = s.replace('π', f'({math.pi})').replace('pi', f'({math.pi})')
    s = s.replace('×', '*').replace('÷', '/').replace('−', '-')
    s = s.replace('Ans', f'({ans_val})').replace('ans', f'({ans_val})')

    # Handle definite integral: integral(integrand, a, b)
    def handle_integral(match):
        integrand_str = match.group(1)
        a_val = float(safe_evaluate_expression(match.group(2), ans_val))
        b_val = float(safe_evaluate_expression(match.group(3), ans_val))

        def integrand_func(x):
            sub_expr = re.sub(r'\bx\b', f'({x})', integrand_str)
            return safe_evaluate_expression(sub_expr, ans_val)

        res = CALC_ENGINE.integrate(integrand_func, a_val, b_val)
        return str(res)

    s = re.sub(r'integral\(([^,]+),\s*([^,]+),\s*([^)]+)\)', handle_integral, s)

    # Handle log_base(b, x) -> (math.log(x)/math.log(b))
    s = re.sub(r'log_base\(([^,]+),\s*([^)]+)\)', r'(math.log(\2)/math.log(\1))', s)

    # Handle roots
    s = re.sub(r'xroot\(([^,]+),\s*([^)]+)\)', r'((\2)**(1/(\1)))', s)
    s = re.sub(r'cbrt\(([^)]+)\)', r'((\1)**(1/3))', s)
    s = re.sub(r'sqrt\(([^)]+)\)', r'math.sqrt(\1)', s)

    # Powers ^ -> **
    s = s.replace('^', '**')

    # Factorials n! -> math.factorial(n)
    s = re.sub(r'(\d+)!', r'math.factorial(\1)', s)

    # Prepare safe evaluation namespace
    math_ns = {
        'math': math,
        'sin': math.sin,
        'cos': math.cos,
        'tan': lambda x: math.tan(x) if abs(math.cos(x)) > 1e-12 else (_ for _ in ()).throw(ValueError("Math ERROR")),
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'sinh': math.sinh,
        'cosh': math.cosh,
        'tanh': math.tanh,
        'sqrt': math.sqrt,
        'log': math.log10,
        'log10': math.log10,
        'ln': math.log,
        'exp': math.exp,
        'abs': abs,
        'Abs': abs,
        'e': math.e,
        'pi': math.pi,
        'round': round,
    }

    try:
        val = eval(s, {'__builtins__': {}}, math_ns)
        return float(val)
    except ZeroDivisionError:
        raise
    except Exception as exc:
        raise ValueError(f"Math ERROR: {exc}")


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
        self.powered_on = True
        self.state = "INPUT"
        self.mode_name = "Calculate"
        self.mode_number = "1"
        self.menu_page = 1
        self.menu_index = 0

    def _format_result(self, result):
        if isinstance(result, (int, float)):
            if isinstance(result, float) and result.is_integer():
                return str(int(result))
            val_str = f"{result:.10g}"
            return val_str
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
            "menuPage": self.menu_page,
            "menuIndex": self.menu_index,
            "selectedMode": self._selected_menu()[1],
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
                return self._state()

            if not self.powered_on:
                return self._state()

            if self.state == "MENU" and key == "ac":
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
                self.state = "INPUT"
                return self._state()

            if key == "del":
                self._return_to_editing()
                if expr_override is not None:
                    self.expression = str(expr_override)
                    self.cursor_position = int(payload.get("cursorPosition", len(self.expression)))
                else:
                    if self.cursor_position > 0:
                        self.expression = (self.expression[:self.cursor_position - 1] +
                                           self.expression[self.cursor_position:])
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
                self.expression = eval_expr

                # Check for zero division
                if re.search(r'/\s*\(?\s*0(?:\.0*)?\s*\)?(?!\d)', eval_expr):
                    self.result_displayed = True
                    self.last_result = "TO INFINITY AND BEYOND"
                    self.state = "RESULT"
                    self.shift = False
                    self.alpha = False
                    return self._state()

                try:
                    ans_float = float(self.ans) if self.ans is not None else 0.0
                except (ValueError, TypeError):
                    ans_float = 0.0

                try:
                    # Evaluate with safe mathematical evaluator
                    res_val = safe_evaluate_expression(eval_expr, ans_float)
                    self.last_result = self._format_result(res_val)
                    self.ans = self.last_result
                    self.result_displayed = True
                    self.shift = False
                    self.alpha = False
                    self.state = "RESULT"
                    return self._state(display=self.last_result)
                except ZeroDivisionError:
                    self.result_displayed = True
                    self.last_result = "TO INFINITY AND BEYOND"
                    self.state = "RESULT"
                    self.shift = False
                    self.alpha = False
                    return self._state()
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
                        self.result_displayed = True
                        self.last_result = "TO INFINITY AND BEYOND"
                        self.state = "RESULT"
                        self.shift = False
                        self.alpha = False
                        return self._state()
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

            token = self._token_for(key)
            if token:
                if self.result_displayed:
                    self.expression = ""
                    self.cursor_position = 0
                    self.last_result = None
                    self.result_displayed = False
                self.expression = (self.expression[:self.cursor_position] + token +
                                   self.expression[self.cursor_position:])
                self.cursor_position += len(token)
                self._update_viewport()
                self.state = "INPUT"

            self.shift = False
            self.alpha = False
            return self._state()
        except ZeroDivisionError:
            self.result_displayed = True
            self.last_result = "TO INFINITY AND BEYOND"
            self.state = "RESULT"
            self.shift = False
            self.alpha = False
            return self._state()
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
                elif path == "/api/calculate":
                    payload["key"] = "equals"
                    response = CONTROLLER.press_key(payload)
                else:
                    self._send_json({"ok": False, "error": "not found"}, 404)
                    return
            self._send_json(response, 200 if response.get("ok") else 400)
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
