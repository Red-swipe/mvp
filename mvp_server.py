"""Local browser MVP server for the ClassWiz HTML frontend."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent
CALCULATOR_ROOT = PROJECT_ROOT.parent / "casio_calculator"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(1, str(CALCULATOR_ROOT))

from engine.engine import Engine


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
}

MENU_PAGES = [
    [
        ("1", "Calculate"), ("2", "Complex"), ("3", "Base-N"), ("4", "Matrix"),
        ("5", "Vector"), ("6", "Statistics"), ("7", "Distribution"), ("8", "Spreadsheet"),
    ],
    [("9", "Table"), ("10", "Equation/Func"), ("11", "Inequality"), ("12", "Ratio")],
]


class CalculatorController:
    def __init__(self) -> None:
        self.engine = Engine()
        self.expression = ""
        self.last_result = None
        self.shift = False
        self.alpha = False
        self.powered_on = True
        self.state = "MENU"
        self.mode_name = "Calculate"
        self.mode_number = "1"
        self.menu_page = 1
        self.menu_index = 0

    def _format_result(self, result):
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 10)).rstrip("0").rstrip(".")

    def _state(self, ok=True, error=None, display=None):
        if not self.powered_on:
            display = "OFF"
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

    def _selected_menu(self):
        return MENU_PAGES[self.menu_page - 1][self.menu_index]

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
            self.menu_index = max(0, self.menu_index - 4)
        elif key == "dpad_down":
            self.menu_index = min(len(page_items) - 1, self.menu_index + 4)

    def _enter_selected_mode(self):
        number, mode_name = self._selected_menu()
        return self.set_mode(mode_name, number)

    def _token_for(self, key):
        if self.shift:
            return {
                "sin": "asin(", "cos": "acos(", "tan": "atan(",
                "log": "10^(", "ln": "e^(", "sqrt": "cbrt(",
                "square": "^3", "power": "xroot(", "scientific": "π",
                "0": "round(", "decimal": "rand()",
            }.get(key, "")
        if self.alpha:
            return {
                "negate": "A", "ellipsis": "B", "inverse": "C",
                "sin": "D", "cos": "E", "tan": "F",
                "right_paren": "x", "s_to_d": "y", "m_plus": "M",
                "scientific": "e", "decimal": "RanInt(",
            }.get(key, "")
        return {
            **{str(number): str(number) for number in range(10)},
            "decimal": ".", "plus": "+", "minus": "-",
            "multiply": "*", "divide": "/", "left_paren": "(",
            "right_paren": ")", "negate": "(-", "sin": "sin(",
            "cos": "cos(", "tan": "tan(", "log": "log(",
            "ln": "ln(", "sqrt": "sqrt(", "square": "^2",
            "power": "^", "inverse": "^(-1)", "scientific": "*10^",
            "ans": str(self.last_result) if self.last_result is not None else "0",
            "fraction": "/", "variable": "x", "integral": "∫(",
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
            self.state = "MENU"
            return self._state()
        except Exception as exc:
            return self._state(False, str(exc))

    def press_key(self, payload):
        key = str(payload.get("key", ""))
        action = str(payload.get("action", key))

        try:
            if key == "on":
                if not self.powered_on:
                    self.powered_on = True
                    self.state = "MENU" if not self.expression else "INPUT"
                return self._state()

            if not self.powered_on:
                return self._state()

            if key == "ac" and action.upper() == "OFF":
                self.powered_on = False
                self.shift = False
                self.alpha = False
                self.state = "OFF"
                return self._state(display="OFF")

            if key == "shift":
                self.shift = not self.shift
                self.alpha = False
                return self._state()
            if key == "alpha":
                self.alpha = not self.alpha
                self.shift = False
                return self._state()
            if key == "ac":
                self.engine.reset()
                self.expression = ""
                self.last_result = None
                self.shift = False
                self.alpha = False
                self.powered_on = True
                self.state = "MENU"
                self.mode_name = "Calculate"
                self.mode_number = "1"
                return self._state(display="0")
            if key == "del":
                self.expression = self.expression[:-1]
                self.shift = False
                self.alpha = False
                self.state = "INPUT"
                return self._state()
            if key == "equals":
                result = self.engine.evaluate(self.expression)
                self.last_result = self._format_result(result)
                self.shift = False
                self.alpha = False
                self.state = "RESULT"
                return self._state(display=self.last_result)
            if key in {"dpad_up", "dpad_down", "dpad_left", "dpad_right"}:
                self._move_menu(key)
                self.state = "MENU"
                return self._state()
            if key == "dpad_center":
                return self._enter_selected_mode()
            if key in {"menu", "setup"}:
                return self._state()

            token = self._token_for(key)
            if token:
                self.expression += token
                self.state = "INPUT"
            self.shift = False
            self.alpha = False
            return self._state()
        except Exception as exc:
            print(f"calculator key error for {key!r}: {exc}", file=sys.stderr)
            self.shift = False
            self.alpha = False
            self.state = "ERROR"
            return self._state(False, "Math ERROR", "Math ERROR")


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
        path = urlparse(self.path).path
        if path in {"/", "/frontend.html"}:
            body = (PROJECT_ROOT / "frontend.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/health":
            self._send_json({"ok": True})
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
                else:
                    self._send_json({"ok": False, "error": "not found"}, 404)
                    return
            self._send_json(response, 200 if response.get("ok") else 400)
        except Exception as exc:
            print(f"request error: {exc}", file=sys.stderr)
            self._send_json({"ok": False, "error": "invalid request"}, 400)

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


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
