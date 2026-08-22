"""Tier 3: inequality solving for quadratic, cubic, and quartic polynomials."""

import copy
import math


def _horner_values(coeffs, x):
    result = 0.0
    for c in coeffs:
        result = result * x + c
    return result


class InequalityEngineError(Exception):
    def __str__(self):
        return self.args[0] if self.args else ""


class InequalityEngine:
    _VALID_OPERATORS = ("<", "<=", ">", ">=")

    def __init__(self):
        self.reset()

    def reset(self):
        self.degree = None
        self.coeffs = []
        self.operator = None
        self.solution = []
        return self

    clear = reset

    def _configure(self, coeffs, operator):
        if operator not in self._VALID_OPERATORS:
            raise ValueError("unsupported inequality operator: {0!r}".format(operator))
        if not coeffs:
            raise ValueError("coeffs must not be empty")
        self.coeffs = [float(c) for c in coeffs]
        if abs(self.coeffs[0]) < 1e-15:
            raise ValueError("leading coefficient must be non-zero")
        self.degree = len(self.coeffs) - 1
        self.operator = operator
        self.solution = []
        return self

    def set_quadratic(self, a, b, c, operator=">"):
        return self._configure((a, b, c), operator)

    def set_cubic(self, a, b, c, d, operator=">"):
        return self._configure((a, b, c, d), operator)

    def set_quartic(self, a, b, c, d, e, operator=">"):
        return self._configure((a, b, c, d, e), operator)

    def get_state(self):
        return {
            "degree": self.degree,
            "coeffs": list(self.coeffs),
            "operator": self.operator,
            "solution": copy.deepcopy(self.solution),
        }

    def _f(self, x):
        return _horner_values(self.coeffs, x)

    def _derivative(self):
        degree = self.degree
        coeffs = self.coeffs
        if degree is None or degree <= 1:
            return lambda x: 0.0
        d = []
        for i in range(degree):
            d.append(coeffs[i] * (degree - i))
        return lambda x: _horner_values(d, x)

    def evaluate(self, x):
        if self.degree is None:
            raise InequalityEngineError("no polynomial configured")
        return self._f(x)

    def satisfies(self, x):
        if self.degree is None:
            raise InequalityEngineError("no polynomial configured")
        if self.operator is None:
            raise InequalityEngineError("no operator configured")
        value = self._f(x)
        if self.operator == "<":
            return value < 0.0
        if self.operator == "<=":
            return value <= 0.0
        if self.operator == ">":
            return value > 0.0
        if self.operator == ">=":
            return value >= 0.0
        raise ValueError("unsupported inequality operator: {0!r}".format(self.operator))

    @staticmethod
    def _round_root(value):
        return round(float(value), 10)

    @staticmethod
    def _dedup(roots):
        roots.sort()
        deduped = []
        for r in roots:
            if not deduped or abs(r - deduped[-1]) > 1e-6:
                deduped.append(r)
        return deduped

    @staticmethod
    def _bisect(func, lo, hi):
        f_lo = func(lo)
        f_hi = func(hi)
        for _ in range(200):
            mid = (lo + hi) / 2.0
            f_mid = func(mid)
            if abs(f_mid) < 1e-12 or abs(hi - lo) < 1e-14:
                return InequalityEngine._round_root(mid)
            if (f_lo > 0.0) != (f_mid > 0.0):
                hi = mid
                f_hi = f_mid
            else:
                lo = mid
                f_lo = f_mid
        return InequalityEngine._round_root((lo + hi) / 2.0)

    @staticmethod
    def _bisect_on(func, lo, hi):
        return InequalityEngine._bisect(func, lo, hi)

    def _refine(self, x0):
        f = self._f
        deriv = self._derivative()
        x = float(x0)
        for _ in range(100):
            fx = f(x)
            df = deriv(x)
            if abs(df) < 1e-15:
                break
            x_new = x - fx / df
            if abs(x_new - x) < 1e-13:
                return self._round_root(x_new)
            x = x_new
        return self._round_root(x)

    def _quadratic_roots(self):
        a, b, c = self.coeffs
        disc = b * b - 4.0 * a * c
        if disc < 0.0:
            return []
        if abs(disc) < 1e-15:
            return [self._round_root(-b / (2.0 * a))]
        sq = math.sqrt(disc)
        r1 = (-b - sq) / (2.0 * a)
        r2 = (-b + sq) / (2.0 * a)
        return [self._round_root(min(r1, r2)), self._round_root(max(r1, r2))]

    def _scan_roots(self, lo, hi, step):
        f = self._f
        roots = []
        prev_x = lo
        prev_f = f(prev_x)
        x = lo + step
        while x <= hi + 1e-12:
            fx = f(x)
            if fx == 0.0 or (prev_f > 0.0) != (fx > 0.0):
                root = self._bisect(f, prev_x, x)
                if abs(f(root)) < 1e-6:
                    roots.append(root)
            elif abs(fx) < 1e-9:
                root = self._refine(x)
                if abs(f(root)) < 1e-6:
                    roots.append(root)
            prev_x = x
            prev_f = fx
            x += step
        roots = self._dedup(roots)
        if self.degree is not None and self.degree >= 3:
            roots = self._add_tangent_roots(roots)
        return roots

    def _add_tangent_roots(self, roots):
        f = self._f
        deriv = self._derivative()
        extra = []
        prev_x = -1000.0
        prev_d = deriv(prev_x)
        x = -1000.0 + 0.1
        while x <= 1000.0 + 1e-12:
            d = deriv(x)
            if d == 0.0 or (prev_d > 0.0) != (d > 0.0):
                root = self._bisect_on(deriv, prev_x, x)
                if abs(f(root)) < 1e-6:
                    extra.append(root)
            elif abs(d) < 1e-9:
                root = self._refine(x)
                if abs(f(root)) < 1e-6:
                    extra.append(root)
            prev_x = x
            prev_d = d
            x += 0.1
        if extra:
            roots = self._dedup(roots + extra)
        return roots

    def solve(self):
        if self.degree is None:
            raise InequalityEngineError("no polynomial configured")
        if self.degree == 2:
            roots = self._quadratic_roots()
        else:
            roots = self._scan_roots(-1000.0, 1000.0, 0.1)
        self.solution = self._build_solution(roots)
        return self.solution

    @staticmethod
    def _make_interval(left, left_closed, right, right_closed):
        if left is None and right is None:
            return {"type": "all", "left": None, "right": None}
        if left is not None and right is not None and abs(left - right) < 1e-12:
            return {"type": "point", "left": left, "right": right}
        left_eff = left is not None and left_closed
        right_eff = right is not None and right_closed
        if left_eff and right_eff:
            typ = "closed"
        elif left_eff:
            typ = "closed_open"
        elif right_eff:
            typ = "open_closed"
        else:
            typ = "open"
        return {"type": typ, "left": left, "right": right}

    def _build_solution(self, roots):
        include_roots = self.operator in ("<=", ">=")
        n = len(roots)
        if n == 0:
            if self.satisfies(0.0):
                return [{"type": "all", "left": None, "right": None}]
            return [{"type": "empty", "left": None, "right": None}]

        sat = [False] * (n + 1)
        probe = roots[0] - 1.0
        sat[0] = self.satisfies(probe)
        for j in range(1, n):
            sat[j] = self.satisfies((roots[j - 1] + roots[j]) / 2.0)
        sat[n] = self.satisfies(roots[-1] + 1.0)

        intervals = []
        j = 0
        while j <= n:
            if not sat[j]:
                j += 1
                continue
            left = None if j == 0 else roots[j - 1]
            right = roots[j] if j < n else None
            k = j
            while k < n and sat[k + 1] and include_roots:
                k += 1
                right = roots[k] if k < n else None
            intervals.append(
                self._make_interval(left, include_roots, right, include_roots)
            )
            j = k + 1

        if include_roots:
            for i in range(n):
                if not (sat[i] or sat[i + 1]):
                    intervals.append(
                        self._make_interval(roots[i], True, roots[i], True)
                    )

        if not intervals:
            return [{"type": "empty", "left": None, "right": None}]

        intervals.sort(
            key=lambda iv: (iv["left"] is not None, 0.0 if iv["left"] is None else iv["left"])
        )
        return intervals

    @staticmethod
    def _format_interval(iv):
        if iv["type"] == "empty":
            return "\u2205"
        if iv["type"] == "all":
            return "all real numbers"
        if iv["type"] == "point":
            return "{" + str(iv["left"]) + "}"
        if iv["left"] is None:
            lstr = "-\u221e"
        else:
            lstr = str(iv["left"])
        if iv["right"] is None:
            rstr = "+\u221e"
        else:
            rstr = str(iv["right"])
        if iv["type"] == "closed":
            return "[" + lstr + ", " + rstr + "]"
        if iv["type"] == "open":
            return "(" + lstr + ", " + rstr + ")"
        if iv["type"] == "open_closed":
            return "(" + lstr + ", " + rstr + "]"
        if iv["type"] == "closed_open":
            return "[" + lstr + ", " + rstr + ")"
        return "(" + lstr + ", " + rstr + ")"

    def solution_as_string(self):
        if self.degree is None:
            raise InequalityEngineError("no polynomial configured")
        if not self.solution:
            raise InequalityEngineError("no solution available")
        parts = [self._format_interval(iv) for iv in self.solution]
        return " \u222a ".join(parts)
