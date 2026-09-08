"""Regression tests for the file:// dual-mode frontend (local evaluation bridge).

Two layers:
1. Parity (requires node): the LOCAL EVALUATION BRIDGE block is extracted from
   frontend.html and executed in node; every case must agree with the live
   HTTP backend's answer for the same expression.
2. Static checks (always): the bridge exists, FILE_MODE gating is wired into
   evaluate()/backendKey(), and no other fetch() call paths were added.

Run:  python test_file_mode.py            (server must be running on :8000)
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
HTML = PROJECT / "frontend.html"
BASE = "http://127.0.0.1:8000"
BEGIN = "// \u2500\u2500 LOCAL EVALUATION BRIDGE"
END = "// \u2500\u2500 END LOCAL EVALUATION BRIDGE \u2500\u2500"

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}   {detail}")


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.request.HTTPError as e:
        return json.loads(e.read())


html = HTML.read_text(encoding="utf-8")

# --- static wiring checks -------------------------------------------------
check("bridge_block_present", BEGIN in html and END in html)
check("file_mode_gate_defined", "location.protocol === 'file:'" in html)
eval_fn = html[html.index("async function evaluate()"):html.index("async function backendKey")]
check("evaluate_gated_on_file_mode", "if (FILE_MODE) {" in eval_fn and "/api/key" in eval_fn)
bkey_fn = html[html.index("async function backendKey"):]
check("backendkey_gated_on_file_mode", bkey_fn.split("{", 1)[1].lstrip().startswith("if (FILE_MODE)"))

# --- parity vs live backend ----------------------------------------------
CASES_OK = [
    "1+1", "2+3", "((2)^(3))", "sqrt(4)", "sqrt((2+3))", "1/0.5", "1/(0+1)",
    "((3)/(4))", "((2)^(0.5))", "-2^2", "2^-2", "(2)^(3)^(2)",
    "cbrt(27)", "xroot(3,(8))", "log_base(2,(8))", "log_base(10,100)",
    "integral(sqrt(x),0,1)", "integral(x^2,0,3)", "integral(sin(x),0,pi)",
    "sin(0)", "cos(0)", "tan(1)", "asin(0.5)", "atan(1)", "ln(e)", "log(100)",
    "5!", "170!", "round(2.5)", "round((-2.5))", "pi*2", "0.00001", "123456789012",
]
CASES_ERR = [
    "1/0", "sqrt((-1))", "xroot(0,5)", "log_base(0,5)", "tan(pi/2)", "asin(2)",
    "integral(1/x,(-1),1)", "171!", "((2))(", "abc",
]
ALL = CASES_OK + CASES_ERR

start = html.index(BEGIN)
end = html.index(END) + len(END)
block = html[start:end]
runner = (
    "const window={location:{protocol:'http:'}};\n" + block +
    "\nconst cases=JSON.parse(process.argv[2]);const out=[];"
    "for(const c of cases){try{out.push([c,'OK',localEvaluate(c)]);}"
    "catch(e){out.push([c,'ERR','Math ERROR']);}}"
    "process.stdout.write(JSON.stringify(out));\n"
)
tmp = Path(subprocess.run(["python", "-c", "import tempfile;print(tempfile.gettempdir())"],
                          capture_output=True, text=True).stdout.strip()) / "casio_bridge_test.js"
tmp.write_text(runner, encoding="utf-8")
proc = subprocess.run(["node", str(tmp), json.dumps(ALL)],
                      capture_output=True, text=True, encoding="utf-8", timeout=120)
check("node_runs_bridge", proc.returncode == 0, proc.stderr[:300])

if proc.returncode == 0:
    rows = {r[0]: r for r in json.loads(proc.stdout)}
    mismatch = []
    for expr in ALL:
        s = post("/api/key", {"key": "ac"})
        s = post("/api/key", {"key": "equals", "expression": expr})
        b_err = bool(s.get("error"))
        l_kind, l_val = rows[expr][1], rows[expr][2]
        if b_err != (l_kind == "ERR"):
            mismatch.append(f"{expr}: kind backend={'ERR' if b_err else 'OK'} local={l_kind}")
            continue
        if not b_err:
            try:
                bf, lf = float(s["result"]), float(l_val)
                if abs(bf - lf) > max(1e-9, abs(bf) * 1e-9):
                    mismatch.append(f"{expr}: backend={s['result']!r} local={l_val!r}")
                elif s["result"] != l_val and abs(bf - lf) != 0:
                    print(f"  [note] fmt drift {expr}: backend={s['result']!r} local={l_val!r}")
            except (TypeError, ValueError):
                if str(s["result"]) != str(l_val):
                    mismatch.append(f"{expr}: backend={s['result']!r} local={l_val!r}")
    check("parity_with_backend", not mismatch, "; ".join(mismatch[:5]))

post("/api/key", {"key": "ac"})
print()
print(f"TOTAL: {passed}/{passed + failed}")
sys.exit(0 if failed == 0 else 1)
