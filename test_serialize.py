import math

_id = 1
nextId = lambda: _id
_id = 1
def createSlot(items=[]):
    global _id
    _id += 1
    return {"id": _id, "items": list(items)}

rootSlot = createSlot()
cursor = {"slot": rootSlot, "index": 0}

appState = {"poweredOn": True, "mode": "Calculate", "menuOpen": False, "menuPage": 1,
    "menuSelection": 0, "shift": False, "alpha": False, "splash": False,
    "result": None, "resultDisplayed": False, "error": None}

def serializeSlot(slot):
    if not slot or not slot.get("items"):
        return ""
    out = ""
    for item in slot["items"]:
        if isinstance(item, str):
            out += item
            out = out.replace("sin\u207b\u00b9(", "asin(")
            out = out.replace("cos\u207b\u00b9(", "acos(")
            out = out.replace("tan\u207b\u00b9(", "atan(")
            out = out.replace("\u00d710\^", "*10^")
            out = out.replace("\u00d7", "*")
            out = out.replace("\u00f7", "/")
            out = out.replace("\u2212", "-")
            out = out.replace("\u03c0", "pi")
            out = out.replace("\u00b2", "^2")
            out = out.replace("\u00b3", "^3")
            out = out.replace("\u207b\u00b9", "^(-1)")
    return out

def getExpr():
    return serializeSlot(rootSlot)

def insertToken(tok):
    cursor["slot"]["items"].insert(cursor["index"], tok)
    cursor["index"] += 1

def resetExpr():
    global rootSlot, cursor
    rootSlot = createSlot()
    cursor = {"slot": rootSlot, "index": 0}
    appState["result"] = None
    appState["resultDisplayed"] = False
    appState["error"] = None

# Press 1
insertToken("1")
print("After 1:", repr(getExpr()))

# Press +
insertToken("+")
print("After +:", repr(getExpr()))

# Press 1 again
insertToken("1")
print("After 1 again:", repr(getExpr()))

expr = getExpr()
print("Final expr string:", repr(expr))
print("Expr length:", len(expr))

# Test eval
math_ns = {
    'math': math,
    'sin': math.sin,
    'cos': math.cos,
    'tan': lambda x: math.tan(x) if abs(math.cos(x)) > 1e-12 else (__import__("sys").exit(1)),
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
    val = eval(expr, {"__builtins__": {}}, math_ns)
    print(f"eval result: {float(val)}")
except Exception as e:
    print(f"eval ERROR: {e}")