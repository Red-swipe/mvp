"""FILE_MODE bridge tests (pytest).

Two layers (same intent as the original script, now automated):
1. Static wiring: the LOCAL EVALUATION BRIDGE block exists, FILE_MODE gating
   is wired into evaluate()/backendKey(), and the bridge carries the
   parity-critical helpers (complex mode flag, Mat/Vec routing, Rnd).
2. Parity (requires node): the bridge block is extracted from frontend.html
   and executed in node against stub app state, then every case is compared
   with the live HTTP backend (which this module spawns itself on a free
   port, so no manual server is needed).

Run:  pytest test_file_mode.py -q   (or: python test_file_mode.py)
"""
import json
import math
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent
HTML = PROJECT / "frontend.html"
SERVER = PROJECT / "mvp_server.py"
BEGIN = "// \u2500\u2500 LOCAL EVALUATION BRIDGE"
END = "// \u2500\u2500 END LOCAL EVALUATION BRIDGE \u2500\u2500"

DEFAULT_SETTINGS = {
    "angleUnit": "Degree", "numberFormat": "Norm", "numberFormatPrecision": 1,
    "engineeringSymbols": False, "fractionResult": "ab/c",
    "statisticsFrequency": False, "autoCalc": True, "showCell": "Value",
}
DEFAULT_VARS = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0,
                "F": 0, "M": 0, "X": 0, "Y": 0}
DEFAULT_MATS = {
    "A": {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]},
    "B": {"rows": 2, "cols": 2, "data": [[5, 6], [7, 8]]},
    "C": {"rows": 0, "cols": 0, "data": []},
    "D": {"rows": 0, "cols": 0, "data": []},
}
DEFAULT_VCTS = {
    "A": {"dim": 3, "data": [1, 2, 2]},
    "B": {"dim": 3, "data": [1, 0, 0]},
    "C": {"dim": 0, "data": []},
    "D": {"dim": 0, "data": []},
}

node_bin = shutil.which("node")
needs_node = pytest.mark.skipif(node_bin is None, reason="node is not installed")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, str(SERVER), "--port", str(port), "--no-browser"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(150):
            try:
                with urllib.request.urlopen(base + "/health", timeout=2) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.1)
        else:
            pytest.fail("test server did not start")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


def post(base, path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(base + path, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.request.HTTPError as e:
        return e.code, json.loads(e.read())


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=15) as r:
        return json.loads(r.read())


# --------------------------------------------------------------------------
# canonical-value comparison (backend and bridge both emit canonical strings)
# --------------------------------------------------------------------------

def parse_num(s):
    s = str(s).strip()
    if s.startswith("≈"):
        s = s[1:]
    m = re.fullmatch(r"(.*?)[×x]\s*10\^([+-]?\d+)", s)
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


def parse_complex(s):
    s = str(s).strip()
    if s.startswith("≈"):
        s = s[1:]
    t = s.replace("i", "j").replace(" ", "")
    try:
        return complex(t)
    except ValueError:
        return None


def close_enough(a, b, tol=1e-6):
    if a == b:
        return True
    if isinstance(a, str) and isinstance(b, str):
        sa, sb = a.strip(), b.strip()
        if sa == sb:
            return True
        # nested matrix/vector literals: compare element-wise
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
        ca, cb = parse_complex(sa), parse_complex(sb)
        if ca is not None and cb is not None:
            return abs(ca - cb) <= max(tol, abs(ca) * 1e-9)
        try:
            return abs(parse_num(sa) - parse_num(sb)) <= max(tol, abs(parse_num(sa)) * 1e-9)
        except ValueError:
            return False
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------
# node bridge runner
# --------------------------------------------------------------------------

def run_bridge(cases, mode="Calculate", settings=None, variables=None,
               matrices=None, vectors=None):
    html = HTML.read_text(encoding="utf-8")
    start = html.index(BEGIN)
    end = html.index(END) + len(END)
    block = html[start:end]
    stub = (
        "const window={location:{protocol:'file:'}};\n"
        "const appState={mode:%s,settings:%s,variables:%s,matrices:%s,vectors:%s};\n"
        % (json.dumps(mode), json.dumps(settings or DEFAULT_SETTINGS),
           json.dumps(variables or DEFAULT_VARS),
           json.dumps(matrices if matrices is not None else {}),
           json.dumps(vectors if vectors is not None else {}))
    )
    runner = (stub + block +
              "\nlocalAns='0';"
              "\nconst cases=JSON.parse(process.argv[2]);const out=[];"
              "for(const c of cases){try{out.push([c,'OK',String(localEvaluate(c))]);}"
              "catch(e){out.push([c,'ERR',e && e.message || 'ERR']);}}"
              "process.stdout.write(JSON.stringify(out));\n")
    tmp = PROJECT / ".bridge_test_tmp.js"
    tmp.write_text(runner, encoding="utf-8")
    try:
        proc = subprocess.run([node_bin, str(tmp), json.dumps(cases)],
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=120)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    assert proc.returncode == 0, f"node bridge failed: {proc.stderr[:300]}"
    return {r[0]: r for r in json.loads(proc.stdout)}


def backend_eval(base, expr):
    return post(base, "/api/key", {"key": "equals", "expression": expr})


def set_mode(base, number, page=1, index=0):
    post(base, "/api/key", {"key": "menu"})
    return post(base, "/api/key", {"key": str(number), "menuPage": page, "menuIndex": index})


# --------------------------------------------------------------------------
# 1. static wiring
# --------------------------------------------------------------------------

def test_bridge_block_present():
    html = HTML.read_text(encoding="utf-8")
    assert BEGIN in html and END in html


def test_file_mode_gate_defined():
    assert "location.protocol === 'file:'" in HTML.read_text(encoding="utf-8")


def test_evaluate_gated_on_file_mode():
    html = HTML.read_text(encoding="utf-8")
    eval_fn = html[html.index("async function evaluate()"):html.index("async function backendKey")]
    assert "if (FILE_MODE) {" in eval_fn and "/api/key" in eval_fn


def test_backendkey_gated_on_file_mode():
    html = HTML.read_text(encoding="utf-8")
    bkey_fn = html[html.index("async function backendKey"):]
    assert bkey_fn.split("{", 1)[1].lstrip().startswith("if (FILE_MODE)")


def test_bridge_parity_helpers():
    html = HTML.read_text(encoding="utf-8")
    for marker in ("_complexMode", "_hasMatVec", "_evalMatExpr", "_rndLocal",
                   "_cSin", "_mvParse", "displayFormat"):
        assert marker in html, marker


# --------------------------------------------------------------------------
# 2. parity: scalar Calculate mode
# --------------------------------------------------------------------------

CASES_OK = [
    "1+1", "2+3", "((2)^(3))", "sqrt(4)", "sqrt((2+3))", "1/0.5", "1/(0+1)",
    "((3)/(4))", "((2)^(0.5))", "-2^2", "2^-2", "(2)^(3)^(2)",
    "cbrt(27)", "cbrt(0-8)", "xroot(3,(8))", "xroot(3,(0-8))",
    "log_base(2,(8))", "log_base(10,100)",
    "integral(sqrt(x),0,1)", "integral(x^2,0,3)", "integral(sin(x),0,pi)",
    "sin(0)", "cos(0)", "tan(1)", "asin(0.5)", "atan(1)", "ln(e)", "log(100)",
    "5!", "170!", "round(2.5)", "round((-2.5))", "pi*2", "0.00001", "123456789012",
    "50%", "sigma(x,1,5)", "d/dx(x^2,3)", "Rnd(10/3)", "RanInt(1,1)",
    "Pol(2,2)", "Rec(2,45)", "5P2", "5C2", "10^(2)", "Abs(0-7)",
    "FACT(12)", "2+2:3*3", "A*2", "i*i", "Abs(3+4*i)", "(1+i)^2",
]
CASES_ERR = [
    "sqrt((-1))", "xroot(0,5)", "log_base(0,5)", "asin(2)",
    "integral(1/x,(-1),1)", "171!", "((2))(", "abc",
]
# 1/0 is special: both sides must show the custom div-zero message.
DIV_ZERO = "To infinity and beyonddd"

VARS_5 = dict(DEFAULT_VARS, A=5)


@needs_node
def test_parity_calculate(server):
    post(server, "/api/reset", {"target": "all"})
    post(server, "/api/variables/set", {"name": "A", "value": 5})
    rows = run_bridge(CASES_OK + CASES_ERR, mode="Calculate",
                      settings=DEFAULT_SETTINGS, variables=VARS_5)
    mismatch = []
    for expr in CASES_OK + CASES_ERR:
        _, b = backend_eval(server, expr)
        b_err = bool(b.get("error"))
        l_kind, l_val = rows[expr][1], rows[expr][2]
        if b_err != (l_kind == "ERR"):
            mismatch.append(f"{expr}: backend={'ERR' if b_err else 'OK'} local={l_kind}")
            continue
        if not b_err and not close_enough(b.get("result"), l_val):
            mismatch.append(f"{expr}: backend={b.get('result')!r} local={l_val!r}")
    assert not mismatch, "; ".join(mismatch[:8])


@needs_node
def test_parity_div_zero(server):
    _, b = backend_eval(server, "1/0")
    assert b.get("display") == DIV_ZERO
    rows = run_bridge(["1/0"], mode="Calculate")
    assert rows["1/0"][1] == "OK" and rows["1/0"][2] == DIV_ZERO


@needs_node
def test_parity_complex_mode(server):
    set_mode(server, "2", page=1, index=1)
    try:
        cases = ["i*i", "sqrt(0-1)", "(1+i)^2", "Abs(3+4*i)", "asin(2)",
                 "ln(0-1)", "sin(i)"]
        rows = run_bridge(cases, mode="Complex")
        mismatch = []
        for expr in cases:
            _, b = backend_eval(server, expr)
            b_err = bool(b.get("error"))
            l_kind, l_val = rows[expr][1], rows[expr][2]
            if b_err != (l_kind == "ERR"):
                mismatch.append(f"{expr}: backend={'ERR' if b_err else 'OK'} local={l_kind}")
                continue
            if not b_err and not close_enough(b.get("result"), l_val):
                mismatch.append(f"{expr}: backend={b.get('result')!r} local={l_val!r}")
        assert not mismatch, "; ".join(mismatch[:8])
    finally:
        set_mode(server, "1", page=1, index=0)


@needs_node
def test_parity_matrix_vector(server):
    post(server, "/api/reset", {"target": "all"})
    post(server, "/api/matrix/set",
         {"matrix": "A", "rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]})
    post(server, "/api/matrix/set",
         {"matrix": "B", "rows": 2, "cols": 2, "data": [[5, 6], [7, 8]]})
    post(server, "/api/vector/set", {"vector": "A", "dim": 3, "data": [1, 2, 2]})
    post(server, "/api/vector/set", {"vector": "B", "dim": 3, "data": [1, 0, 0]})
    cases = ["MatA+MatB", "MatA*MatB", "Det(MatA)", "Trn(MatA)",
             "MatA^(-1)", "MatA^2", "2*MatA", "Identity(2)", "Abs(MatA)",
             "VctA+VctB", "Dot(VctA,VctB)", "Angle(VctA,VctB)",
             "VctA*VctB", "Abs(VctA)", "UnitV(VctA)", "3*VctA"]
    rows = run_bridge(cases, mode="Matrix", matrices=DEFAULT_MATS,
                      vectors=DEFAULT_VCTS)
    mismatch = []
    for expr in cases:
        _, b = backend_eval(server, expr)
        b_err = bool(b.get("error"))
        l_kind, l_val = rows[expr][1], rows[expr][2]
        if b_err != (l_kind == "ERR"):
            mismatch.append(f"{expr}: backend={'ERR' if b_err else 'OK'} local={l_kind}")
            continue
        if not b_err and not close_enough(b.get("result"), l_val, tol=1e-4):
            mismatch.append(f"{expr}: backend={b.get('result')!r} local={l_val!r}")
    post(server, "/api/reset", {"target": "all"})
    assert not mismatch, "; ".join(mismatch[:8])


@needs_node
def test_parity_rnd_fix(server):
    post(server, "/api/settings", {"numberFormat": "Fix", "numberFormatPrecision": 3})
    try:
        rows = run_bridge(["Rnd(10/3)", "Rnd(10/3)*3"], mode="Calculate",
                          settings=dict(DEFAULT_SETTINGS, numberFormat="Fix",
                                        numberFormatPrecision=3))
        _, b1 = backend_eval(server, "Rnd(10/3)")
        assert close_enough(b1.get("result"), rows["Rnd(10/3)"][2])
        assert close_enough(b1.get("result"), 3.333)
        _, b2 = backend_eval(server, "Rnd(10/3)*3")
        assert close_enough(b2.get("result"), rows["Rnd(10/3)*3"][2])
        assert close_enough(b2.get("result"), 9.999)
    finally:
        post(server, "/api/settings", dict(DEFAULT_SETTINGS))


if __name__ == "__main__":
    sys.exit(__import__("pytest").main([__file__, "-q"]))
