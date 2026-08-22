"""TABLE-mode engine for the CASIO fx-991EX-style calculator.

Builds a table of f(x) (and optionally g(x)) values across a range of x,
mirroring the handheld's TABLE mode.
"""

import math


class TableEngine:
    """Generate a table of function values.

    The user supplies an f(x) expression (and optionally a g(x) expression).
    generate() evaluates both across x_start..x_end in x_step increments
    (inclusive of the endpoints) and returns a list of rows.  Each row is
    {"x": float, "f": float, "g": float|None}; g is None when no g(x)
    expression is set.  Runtime evaluation errors (e.g. log(0), 1/0, or
    sqrt of a negative) propagate to the caller instead of yielding nan.

    Expressions are evaluated with a restricted namespace exposing only x and
    a whitelist of math helpers (sqrt, abs, sin, cos, tan, log, log10, exp,
    pi, e, floor, ceil).  "ln(" is translated to "log(" first so natural log
    works like it does on the handheld.
    """

    _MAX_ROWS = 30

    _ALLOWED = {
        "x": 0.0,
        "sqrt": math.sqrt,
        "abs": abs,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
        "floor": math.floor,
        "ceil": math.ceil,
    }

    def __init__(self):
        self._f = None
        self._g = None
        self._last = None

    def _validate(self, expr):
        normalized = expr.replace("ln(", "log(")
        try:
            code = compile(normalized, "<table_expression>", "eval")
        except SyntaxError:
            raise ValueError("Invalid expression: {!r}".format(expr))
        namespace = {"__builtins__": {}, **self._ALLOWED}
        try:
            eval(code, namespace)
        except NameError:
            raise ValueError("Unknown name in expression: {!r}".format(expr))
        return code

    def set_f(self, expr):
        """Set the f(x) expression.  Raises ValueError if it is invalid."""
        self._f = self._validate(expr)

    def set_g(self, expr):
        """Set the g(x) expression, or pass None to disable g(x)."""
        if expr is None:
            self._g = None
        else:
            self._g = self._validate(expr)

    def _eval_code(self, code, x):
        namespace = {"__builtins__": {}, **self._ALLOWED, "x": float(x)}
        return float(eval(code, namespace))

    def generate(self, x_start, x_end, x_step):
        """Evaluate f (and g) across the range and return the table rows."""
        if self._f is None:
            raise ValueError("No f(x) expression set; call set_f() first")
        if x_step <= 0:
            raise ValueError("x_step must be greater than 0")
        if x_start > x_end:
            raise ValueError("x_start must be <= x_end")
        start = float(x_start)
        end = float(x_end)
        step = float(x_step)
        count = 0
        x = start
        while x <= end + 1e-9:
            count += 1
            x = start + count * step
        if count > self._MAX_ROWS:
            raise ValueError(
                "Table would require {} rows; maximum is {}".format(
                    count, self._MAX_ROWS
                )
            )
        rows = []
        for i in range(count):
            x = start + i * step
            f = self._eval_code(self._f, x)
            g = self._eval_code(self._g, x) if self._g is not None else None
            rows.append({"x": x, "f": f, "g": g})
        self._last = rows
        return [dict(row) for row in rows]

    def clear(self):
        """Reset f, g and the stored last table."""
        self._f = None
        self._g = None
        self._last = None

    def last_table(self):
        """Return the most recently generated table, or None if none yet."""
        if self._last is None:
            return None
        return [dict(row) for row in self._last]