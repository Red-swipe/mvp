"""Five independent collectors for the Mentis ClassWiz expression battery.

Every collector returns a list of result dicts with the SAME shape and NEVER
raises: a collector that dies reports itself as an infrastructure failure for
every case rather than aborting the run.

Result shape
------------
    id          int, the case id
    input       the exact string submitted on this path
    observed    raw string as the path returned it (None if nothing came back)
    numeric     canonical float when parseable, else None
    is_error    bool, the path signalled an error
    error_text  the visible error string when is_error
    error_class  one of:
                   "none"            - no error
                   "calculator"      - a genuine maths error (DIV_ZERO, domain, ...)
                   "system"          - an unexpected internal failure
                   "input_build"     - the keypad produced the wrong expression
                   "unparseable"     - output was not a number and not an error
                   "collector_error" - this collector itself failed
    status      one of:
                   "pass" | "fail" | "unresolved" | "unexecuted" | "collector_error"
    detail      free text

Numerics and error classification are left to the comparator; collectors only
report faithfully what they observed.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FRONTEND = os.path.join(REPO, "frontend.html")
SERVER = os.path.join(REPO, "mvp_server.py")
CHROMIUM = r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"

BEGIN_MARK = "// \u2500\u2500 LOCAL EVALUATION BRIDGE"
END_MARK = "// \u2500\u2500 END LOCAL EVALUATION BRIDGE \u2500\u2500"

# --------------------------------------------------------------------------
# Canonical number parsing.
# COPIED VERBATIM from test_file_mode.py (parse_num / close_enough) so the
# comparator and the existing suite canonicalise identically. Attribution kept
# so the duplication is deliberate and traceable. `parse_num` raises
# ValueError on anything it cannot canonicalise; callers MUST NOT coerce that
# to zero.
# --------------------------------------------------------------------------


def parse_num(s):
    s = str(s).strip()
    if s.startswith("\ufffd%\u005e"):
        s = s[1:]
    m = re.fullmatch(r"(.*?)[A-x]\s*10\^([+-]?\d+)", s)
    if m:
        return float(m.group(1)) * (10.0 ** int(m.group(2)))
    m = re.fullmatch(r"(-?\d+)\s+(\d+)/(\d+)", s)
    if m:
        whole = float(m.group(1))
        frac = float(m.group(2)) / float(m.group(3))
        return whole + (frac if whole >= 0 else -frac)
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)) / float(m.group(2))
    if s.endswith("%"):
        return float(s[:-1]) / 100.0
    return float(s)


def close_enough(a, b, tol=1e-6):
    if a == b:
        return True
    if isinstance(a, str) and isinstance(b, str):
        sa, sb = a.strip(), b.strip()
        if sa == sb:
            return True
        if sa.startswith("[") and sb.startswith("["):
            def flat(x):
                return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", x)]
            try:
                fa, fb = flat(sa), flat(sb)
            except ValueError:
                return False
            if len(fa) != len(fb):
                return False
            return all(abs(x - y) <= max(tol, abs(x) * 1e-9) for x, y in zip(fa, fb))
        try:
            return abs(parse_num(sa) - parse_num(sb)) <= max(tol, abs(parse_num(sa)) * 1e-9)
        except ValueError:
            return False
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------
# Server lifecycle shared by the HTTP collector.
# --------------------------------------------------------------------------


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServerProcess:
    """Spawns the real mvp_server.py the way the app's own tests do."""

    def __init__(self):
        self.proc = None
        self.base = None

    def __enter__(self):
        port = _free_port()
        self.proc = subprocess.Popen(
            [sys.executable, SERVER, "--port", str(port), "--no-browser"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.base = "http://127.0.0.1:%d" % port
        for _ in range(150):
            try:
                with urllib.request.urlopen(self.base + "/health", timeout=2) as r:
                    if r.status == 200:
                        return self
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
        raise RuntimeError("mvp_server.py did not become healthy")

    def __exit__(self, *exc):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                self.proc.kill()
        return False

    def post(self, path, data):
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            self.base + path, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())


def normalize_value(s):
    """Canonicalise an already-structured value string.

    Used for appState.result, which the calculator itself produces, e.g.
    '110 1/4'. parse_num understands that mixed form, so the whole string must
    survive; splitting it on spaces would throw away the whole part and turn
    110.25 into 0.25.
    """
    if s is None:
        return None
    s = (s.replace("\u2212", "-")
          .replace("\u00d7", "*")
          .replace("\u00f7", "/")
          .replace("\u00a0", " ")
          .replace("\u200b", "")
          .replace("\u221a", "sqrt"))
    s = " ".join(s.split())
    return s or None


def normalize_lcd(s):
    """Canonicalise a flattened LCD string; keeps only the last token.

    The .lcd inner_text concatenates the expression line and the result line,
    so the result is the LAST whitespace-separated token. Use normalize_value
    instead for anything the calculator already formatted itself.
    """
    s = normalize_value(s)
    if s is None:
        return None
    return s.split(" ")[-1]


def _blank(cid, path, inp, cls, status, detail):
    return {"id": cid, "input": inp, "observed": None, "numeric": None,
            "is_error": False, "error_text": None, "error_class": cls,
            "status": status, "path": path, "detail": detail}


# --------------------------------------------------------------------------
# Collector 1: raw engine.engine.Engine().evaluate()
# --------------------------------------------------------------------------

def collect_engine(cases):
    path = "engine"
    out = []
    try:
        sys.path.insert(0, REPO)
        from engine.engine import Engine
    except Exception as e:  # noqa: BLE001
        return [_blank(c["id"], path, c["internal_expr"], "collector_error",
                       "collector_error", "import failed: %r" % (e,)) for c in cases]

    for c in cases:
        cid, expr = c["id"], c["internal_expr"]
        if expr is None:
            out.append(_blank(cid, path, None, "none", "unexecuted",
                              "no internal expression for this case"))
            continue
        try:
            v = Engine().evaluate(expr)
        except ZeroDivisionError as e:
            out.append({"id": cid, "input": expr, "observed": None, "numeric": None,
                        "is_error": True, "error_text": str(e) or "division by zero",
                        "error_class": "calculator", "status": "pass", "path": path,
                        "detail": "ZeroDivisionError"})
            continue
        except Exception as e:  # noqa: BLE001
            # Engine.evaluate takes RAW CORE syntax only. Template strings the
            # keypad builds -- ((2)^(3)), sqrt(16), 100(1.05^2) -- are rejected
            # at tokenize(). That is a property of this entry point, NOT a
            # calculator defect, so it must not be scored as a failure.
            if type(e).__name__ == "TokenizerError":
                out.append(_blank(cid, path, expr, "none", "unexecuted",
                                  "Engine.evaluate cannot tokenize template syntax: %s"
                                  % (e,)))
                continue
            out.append({"id": cid, "input": expr, "observed": None, "numeric": None,
                        "is_error": True, "error_text": "%s: %s" % (type(e).__name__, e),
                        "error_class": "calculator", "status": "pass", "path": path,
                        "detail": type(e).__name__})
            continue
        try:
            n = parse_num(v)
        except ValueError:
            n = None
        out.append({"id": cid, "input": expr, "observed": str(v), "numeric": n,
                    "is_error": False, "error_text": None, "error_class": "none",
                    "status": "pass", "path": path, "detail": ""})
    return out


# --------------------------------------------------------------------------
# Collector 2: mvp_server.safe_evaluate_expression()
# --------------------------------------------------------------------------

def collect_safe_eval(cases):
    path = "safe_eval"
    out = []
    try:
        sys.path.insert(0, REPO)
        import mvp_server
    except Exception as e:  # noqa: BLE001
        return [_blank(c["id"], path, c["internal_expr"], "collector_error",
                       "collector_error", "import failed: %r" % (e,)) for c in cases]

    for c in cases:
        cid, expr = c["id"], c["internal_expr"]
        if expr is None:
            out.append(_blank(cid, path, None, "none", "unexecuted",
                              "no internal expression for this case"))
            continue
        try:
            v = mvp_server.safe_evaluate_expression(expr)
        except ZeroDivisionError as e:
            out.append({"id": cid, "input": expr, "observed": None, "numeric": None,
                        "is_error": True, "error_text": str(e) or "division by zero",
                        "error_class": "calculator", "status": "pass", "path": path,
                        "detail": "ZeroDivisionError"})
            continue
        except Exception as e:  # noqa: BLE001
            out.append({"id": cid, "input": expr, "observed": None, "numeric": None,
                        "is_error": True, "error_text": "%s: %s" % (type(e).__name__, e),
                        "error_class": "calculator", "status": "pass", "path": path,
                        "detail": type(e).__name__})
            continue
        try:
            n = parse_num(v)
        except ValueError:
            n = None
        out.append({"id": cid, "input": expr, "observed": str(v), "numeric": n,
                    "is_error": False, "error_text": None, "error_class": "none",
                    "status": "pass", "path": path, "detail": ""})
    return out


# --------------------------------------------------------------------------
# Collector 3: node bridge running the real frontend localEvaluate()
# --------------------------------------------------------------------------

_BRIDGE_RUNNER = (
    "\nlocalAns='0';"
    "\nconst cases=JSON.parse(process.argv[2]);const out=[];"
    "for(const c of cases){try{out.push([c,'OK',String(localEvaluate(c))]);}"
    "catch(e){out.push([c,'ERR',(e && e.message)||'ERR']);}}"
    "process.stdout.write(JSON.stringify(out));\n"
)

_SETTINGS = {"inputOutput": "MathI/MathO", "angleUnit": "Degree",
             "numberFormat": "Norm", "numberFormatPrecision": 1,
             "engineeringSymbols": False, "fractionResult": "ab/c",
             "statisticsFrequency": False, "autoCalc": True, "showCell": "Value"}
_VARIABLES = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0, "G": 0, "M": 0,
              "X": 0, "Y": 0}


def _bridge_block():
    html = open(FRONTEND, encoding="utf-8").read()
    start = html.index(BEGIN_MARK)
    end = html.index(END_MARK, start) + len(END_MARK)
    return html[start:end]


def collect_bridge(cases):
    path = "node_bridge"
    todo = [c for c in cases if c["internal_expr"] is not None]
    out = []
    if not todo:
        return out
    try:
        stub = ("const window={location:{protocol:'file:'}};\n"
                "const appState={mode:'Calculate',settings:%s,variables:%s,"
                "matrices:{},vectors:{}};\n"
                % (json.dumps(_SETTINGS), json.dumps(_VARIABLES)))
        runner = stub + _bridge_block() + _BRIDGE_RUNNER
        tmp = os.path.join(REPO, ".comparator_bridge_tmp.js")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(runner)
        try:
            proc = subprocess.run(
                ["node", tmp, json.dumps([c["internal_expr"] for c in todo])],
                capture_output=True, text=True, encoding="utf-8", timeout=180)
        finally:
            os.unlink(tmp)
        if proc.returncode != 0:
            raise RuntimeError("node exited %d: %s" % (proc.returncode, proc.stderr[:400]))
        got = {r[0]: r for r in json.loads(proc.stdout)}
    except Exception as e:  # noqa: BLE001
        return [_blank(c["id"], path, c["internal_expr"], "collector_error",
                       "collector_error", "node bridge failed: %r" % (e,))
                for c in todo]

    for c in cases:
        if c["internal_expr"] is None:
            continue
        r = got.get(c["internal_expr"])
        if r is None:
            out.append(_blank(c["id"], path, c["internal_expr"], "collector_error",
                              "collector_error", "node returned no row"))
            continue
        _, kind, val = r
        if kind == "ERR":
            cls = "calculator" if val in ("DIV_ZERO", "Math ERROR") else "system"
            if val == "Math ERROR":
                cls = "system"   # frontend collapses every failure into this string
            out.append({"id": c["id"], "input": c["internal_expr"], "observed": None,
                        "numeric": None, "is_error": True, "error_text": val,
                        "error_class": cls, "status": "pass", "path": path,
                        "detail": "localEvaluate threw"})
            continue
        try:
            n = parse_num(val)
        except ValueError:
            n = None
        out.append({"id": c["id"], "input": c["internal_expr"], "observed": val,
                    "numeric": n, "is_error": False, "error_text": None,
                    "error_class": "none" if n is not None else "unparseable",
                    "status": "pass", "path": path, "detail": ""})
    return out


# --------------------------------------------------------------------------
# Collector 4: live server, POST /api/key
# --------------------------------------------------------------------------

def collect_http(cases):
    path = "http"
    out = []
    todo = [c for c in cases if c["internal_expr"] is not None]
    if not todo:
        return out
    try:
        with ServerProcess() as srv:
            for c in todo:
                cid, expr = c["id"], c["internal_expr"]
                try:
                    srv.post("/api/reset", {"target": "all"})
                    status, body = srv.post("/api/key",
                                           {"key": "equals", "expression": expr})
                except Exception as e:  # noqa: BLE001
                    out.append(_blank(cid, path, expr, "collector_error",
                                      "collector_error", "request failed: %r" % (e,)))
                    continue
                disp = body.get("display")
                res = body.get("result")
                err = body.get("error")
                is_err = bool(err) or status >= 400
                observed = err if is_err else (res if res not in (None, "") else disp)
                if is_err:
                    cls = "calculator" if err == "DIV_ZERO" or status == 400 else "system"
                    out.append({"id": cid, "input": expr, "observed": observed,
                                "numeric": None, "is_error": True,
                                "error_text": err or ("HTTP %d" % status),
                                "error_class": cls, "status": "pass", "path": path,
                                "detail": "http_status=%d" % status})
                    continue
                try:
                    n = parse_num(observed)
                except (ValueError, TypeError):
                    n = None
                out.append({"id": cid, "input": expr, "observed": observed,
                            "numeric": n, "is_error": False, "error_text": None,
                            "error_class": "none" if n is not None else "unparseable",
                            "status": "pass", "path": path,
                            "detail": "http_status=%d" % status})
    except Exception as e:  # noqa: BLE001
        return [_blank(c["id"], path, c["internal_expr"], "collector_error",
                       "collector_error", "server lifecycle failed: %r" % (e,))
                for c in todo]
    return out


# --------------------------------------------------------------------------
# Collector 5: real Chromium over file://, real keypad clicks
# --------------------------------------------------------------------------

def collect_browser(cases, sequences, expected_by_id):
    """Drives the keypad and preserves full per-case evidence.

    For every attempted case it records: the exact keypad actions taken,
    getExpr() read BEFORE evaluation, the LCD text, the console errors, page
    errors and failed network requests observed during that case, whether the
    run timed out or a selector was missing, and the resulting classification.

    If the constructed expression differs from the case's internal_expr the
    result is classified as an input-construction failure, never as an
    evaluator defect.

    Nothing here is mocked. Every field is read from the live page.
    """
    path = "browser_file"
    out = []
    if not os.path.exists(CHROMIUM):
        return [_blank(c["id"], path, None, "collector_error", "collector_error",
                       "chromium not installed at " + CHROMIUM) for c in cases]
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        return [_blank(c["id"], path, None, "collector_error", "collector_error",
                       "playwright import failed: %r" % (e,)) for c in cases]

    url = "file:///" + FRONTEND.replace("\\", "/")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=CHROMIUM)
            page = browser.new_page()
            console, pageerr, failed = [], [], []
            page.on("console", lambda m: console.append("%s: %s" % (m.type, m.text))
                    if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: pageerr.append(str(e)))
            page.on("requestfailed", lambda r: failed.append("%s %s" % (r.url, r.failure)))
            page.goto(url, wait_until="load")

            for c in cases:
                cid = c["id"]
                keys = sequences.get(str(cid))
                if keys is None:
                    out.append(_blank(cid, path, c["internal_expr"], "none", "unexecuted",
                                      "no keypad sequence defined for this case"))
                    continue
                try:
                    page.evaluate(
                        "() => { if (typeof hardResetExpr === 'function') hardResetExpr(); "
                        "else if (typeof resetExpr === 'function') resetExpr(); }")
                    page.wait_for_timeout(50)
                    missing = []
                    for k in keys:
                        loc = page.locator('[data-key="%s"]' % k)
                        if loc.count() == 0:
                            missing.append(k)
                            continue
                        loc.click()
                    # READ getExpr BEFORE the final `equals`. Pressing `=` mutates
                    # the slot tree, so reading afterwards observes a different
                    # expression than the one that was submitted.
                    built = page.evaluate(
                        "() => (typeof getExpr === 'function') ? getExpr() : null")
                    page.wait_for_timeout(450)
                    # Read the DEDICATED result region, not the flattened .lcd.
                    # .lcd inner_text concatenates the expression line and the
                    # result line, and a stacked fraction renders as separate
                    # "1" "2" tokens, so last-token extraction reads the
                    # denominator. #lcdResultLine is verified at
                    # frontend.html:1989 and is what the app itself renders into.
                    lcd_raw = page.locator(".lcd").inner_text()
                    result_raw = ""
                    try:
                        result_raw = page.locator("#lcdResultLine").inner_text()
                    except Exception:  # noqa: BLE001
                        result_raw = ""
                    if not " ".join((result_raw or "").split()):
                        page.wait_for_timeout(600)
                        lcd_raw = page.locator(".lcd").inner_text()
                        try:
                            result_raw = page.locator("#lcdResultLine").inner_text()
                        except Exception:  # noqa: BLE001
                            result_raw = ""
                    lcd = " ".join((lcd_raw or "").split())
                    result_line = " ".join((result_raw or "").split())
                    # Canonical plain value + error, straight from app state.
                    # #lcdResultLine renders KaTeX, so a stacked 1/2 arrives as
                    # "12\frac{1}{2}21<zwsp>". appState.result is the plain
                    # string the calculator itself computed ("1/2").
                    app = page.evaluate(
                        "() => (typeof appState !== 'undefined') "
                        "? {result: appState.result, error: appState.error, "
                        "  resultDisplayed: appState.resultDisplayed} "
                        ": {result: null, error: null, resultDisplayed: null}")
                    app_result = None if app.get("result") is None else str(app.get("result"))
                    app_error = None if app.get("error") is None else str(app.get("error"))
                except Exception as e:  # noqa: BLE001
                    step_failure = {
                        "type": "timeout_or_selector",
                        "error": "%s: %s" % (type(e).__name__, e),
                        "keys_clicked_before_failure": list(keys[:len(keys) - 1])
                        if missing and keys else list(keys or []),
                    }
                    rec = _blank(cid, path, c["internal_expr"], "collector_error",
                                 "collector_error",
                                 "browser step failed: %r" % (e,))
                    rec["evidence"] = {
                        "keypad_actions": keys,
                        "keys_not_found": missing,
                        "getExpr_before_equals": None,
                        "lcd_text": None,
                        "console_errors": list(console),
                        "page_errors": list(pageerr),
                        "failed_requests": list(failed),
                        "step_failure": step_failure,
                    }
                    out.append(rec)
                    console.clear(); pageerr.clear(); failed.clear()
                    continue

                evidence = {
                    "keypad_actions": list(keys),
                    "keys_not_found": list(missing),
                    "getExpr_before_equals": built,
                    "lcd_text": lcd,
                    "result_region_text": result_line,
                    "appState_result": app_result,
                    "appState_error": app_error,
                    "console_errors": list(console),
                    "page_errors": list(pageerr),
                    "failed_requests": list(failed),
                    "step_failure": None,
                }

                detail = []
                if missing:
                    detail.append("keys_not_found=%s" % ",".join(missing))
                if console:
                    detail.append("console=%s" % console)
                if pageerr:
                    detail.append("pageerror=%s" % pageerr)
                if failed:
                    detail.append("failed_requests=%s" % failed)
                console.clear(); pageerr.clear(); failed.clear()

                exp_internal = c["internal_expr"]
                # The equals key is the last click and does not change the expression.
                if exp_internal is not None and built is not None and built != exp_internal:
                    out.append({"id": cid, "input": built, "observed": lcd,
                                "numeric": None, "is_error": False,
                                "error_text": None, "error_class": "input_build",
                                "status": "unexecuted", "path": path,
                                "evidence": evidence,
                                "detail": ("keypad built %r but the case declares %r; "
                                           "not evaluated as a calculator defect"
                                           % (built, exp_internal))})
                    continue

                # Canonical value first: appState.result (already formatted by
                # the calculator, so NOT split), then the result region, then
                # the flat LCD.
                result_text = normalize_value(app_result) \
                or normalize_lcd(result_line) or normalize_lcd(lcd)
                lcd_is_error = ("ERROR" in lcd) or bool(app_error)
                try:
                    n = parse_num(result_text)
                except (ValueError, TypeError):
                    n = None

                if lcd_is_error:
                    cls = "calculator" if "Math ERROR" in lcd else "system"
                    out.append({"id": cid, "input": built, "observed": lcd,
                                "numeric": None, "is_error": True,
                                "error_text": result_text, "error_class": cls,
                                "status": "pass", "path": path,
                                "evidence": evidence,
                                "detail": "; ".join(detail)})
                elif result_text is None:
                    out.append({"id": cid, "input": built, "observed": lcd,
                                "numeric": None, "is_error": False,
                                "error_text": None, "error_class": "unparseable",
                                "status": "pass", "path": path,
                                "evidence": evidence,
                                "detail": "empty LCD; " + "; ".join(detail)})
                else:
                    out.append({"id": cid, "input": built, "observed": lcd,
                                "numeric": n, "is_error": False, "error_text": None,
                                "error_class": "none" if n is not None else "unparseable",
                                "status": "pass", "path": path,
                                "evidence": evidence,
                                "detail": "; ".join(detail)})
            browser.close()
    except Exception as e:  # noqa: BLE001
        return [_blank(c["id"], path, c["internal_expr"], "collector_error",
                       "collector_error", "browser lifecycle failed: %r" % (e,))
                for c in cases]
    return out


COLLECTORS = {
    "engine": collect_engine,
    "safe_eval": collect_safe_eval,
    "node_bridge": collect_bridge,
    "http": collect_http,
    "browser_file": collect_browser,
}