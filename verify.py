"""Verification test suite for ClassWiz browser MVP."""
import urllib.request
import json
import math
import sys

BASE = "http://127.0.0.1:8000"


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except urllib.request.HTTPError as e:
        return json.loads(e.read())


passed = 0
total = 0


def check(name, condition, detail=""):
    global passed, total
    total += 1
    status = "PASS" if condition else "FAIL"
    msg = "  [%s] %s" % (status, name)
    if detail:
        msg += ": " + str(detail)
    print(msg)
    if condition:
        passed += 1


# --- Reset ---
post("/api/key", {"key": "on"})
post("/api/key", {"key": "ac"})

# 1. Arithmetic
s = post("/api/key", {"key": "equals", "expression": "1+1"})
check("1+1=2", s.get("result") == "2", repr(s.get("result")))

post("/api/key", {"key": "ac"})

# 2. Division by zero
s = post("/api/key", {"key": "equals", "expression": "1/0"})
check("1/0=Math ERROR", s.get("error") == "Math ERROR" and s.get("display") == "Math ERROR",
      repr((s.get("error"), s.get("display"))))

post("/api/key", {"key": "ac"})

# 3. asin
s = post("/api/key", {"key": "equals", "expression": "asin(0.5)"})
r = s.get("result")
check("asin(0.5) numeric", r is not None and abs(float(r) - math.asin(0.5)) < 0.001, repr(r))

post("/api/key", {"key": "ac"})

# 4. atan
s = post("/api/key", {"key": "equals", "expression": "atan(1)"})
r = s.get("result")
check("atan(1) numeric", r is not None and abs(float(r) - math.atan(1)) < 0.001, repr(r))

post("/api/key", {"key": "ac"})

# 5. Fraction
s = post("/api/key", {"key": "equals", "expression": "((3)/(4))"})
r = s.get("result")
check("fraction 3/4=0.75", r is not None and abs(float(r) - 0.75) < 0.001, repr(r))

post("/api/key", {"key": "ac"})

# 6. sqrt
s = post("/api/key", {"key": "equals", "expression": "sqrt(4)"})
check("sqrt(4)=2", s.get("result") == "2", repr(s.get("result")))

post("/api/key", {"key": "ac"})

# 7. cbrt
s = post("/api/key", {"key": "equals", "expression": "cbrt(27)"})
check("cbrt(27)=3", s.get("result") == "3", repr(s.get("result")))

post("/api/key", {"key": "ac"})

# 8. Power
s = post("/api/key", {"key": "equals", "expression": "((2)^(3))"})
check("2^3=8", s.get("result") == "8", repr(s.get("result")))

post("/api/key", {"key": "ac"})

# 9. Integral
s = post("/api/key", {"key": "equals", "expression": "integral(x^2,0,3)"})
r = s.get("result")
check("integral(x^2,0,3)~9", r is not None and abs(float(r) - 9) < 0.1, repr(r))

post("/api/key", {"key": "ac"})

# 10. log_base
s = post("/api/key", {"key": "equals", "expression": "log_base(10,100)"})
check("log_base(10,100)=2", s.get("result") == "2", repr(s.get("result")))

post("/api/key", {"key": "ac"})

# 11. xroot
s = post("/api/key", {"key": "equals", "expression": "xroot(3,27)"})
check("xroot(3,27)=3", s.get("result") == "3", repr(s.get("result")))

# 12. Font serving
try:
    with urllib.request.urlopen(BASE + "/ClassWizFontSet/CASIO%20ClassWiz.ttf", timeout=5) as rf:
        data = rf.read()
    check("font_served_over_http", len(data) > 10000, "size=" + str(len(data)))
except Exception as e:
    check("font_served_over_http", False, str(e))

# 13. Frontend HTML serves
try:
    with urllib.request.urlopen(BASE + "/", timeout=5) as rf:
        html = rf.read().decode("utf-8")
    check("frontend_serves", "MENTIS" in html and "lcdCalc" in html, "len=" + str(len(html)))
    check("font_face_declared", "@font-face" in html, "")
    check("template_engine_in_js", "insertFraction" in html, "")
    check("status_bar_in_html", "lcdSplash" in html and "lcdMenu" in html, "")
    check("tan_inverse_token", "tan\u207b\u00b9(" in html or "tan\\u207b\\u00b9" in html, "")
except Exception as e:
    check("frontend_serves", False, str(e))

# 14. MENU state
post("/api/key", {"key": "ac"})
s = post("/api/key", {"key": "menu"})
check("menu_opens", s.get("state") == "MENU", repr(s.get("state")))

# 15. Mode selection
s = post("/api/key", {"key": "equals"})
check("mode_select_enters", s.get("state") != "MENU", repr(s.get("state")))

# 16. Back to Calculate
s = post("/api/mode", {"mode": "Calculate", "number": "1"})
check("back_to_calculate", s.get("modeName") == "Calculate", repr(s.get("modeName")))

# 17. SHIFT+AC powers off
post("/api/key", {"key": "ac", "shift": True, "action": "OFF"})
s = post("/api/key", {"key": "ac", "action": "OFF"})
check("power_off_via_OFF", s.get("state") == "OFF" or not s.get("poweredOn"), repr(s.get("state")))

# 18. ON powers back on
s = post("/api/key", {"key": "on"})
check("on_powers_on", s.get("poweredOn") is True, repr(s.get("poweredOn")))

print()
print("TOTAL: %d/%d passed" % (passed, total))
sys.exit(0 if passed == total else 1)
