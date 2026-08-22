import math


class CalcEngineError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self._message = message

    def __str__(self):
        return self._message


class CalculusEngine:
    def __init__(self):
        pass

    def differentiate(self, f, x, tol=1e-8):
        if x != 0:
            h = max(1e-8, abs(x) * 1e-8)
        else:
            h = 1e-8
        try:
            fm2 = f(x - 2 * h)
            fm1 = f(x - h)
            fp1 = f(x + h)
            fp2 = f(x + 2 * h)
        except Exception:
            raise CalcEngineError("Math ERROR")
        result = (-fp2 + 8 * fp1 - 8 * fm1 + fm2) / (12 * h)
        if math.isnan(result) or math.isinf(result):
            raise CalcEngineError("Math ERROR")
        return result

    def integrate(self, f, a, b, n=1000):
        if a == b:
            return 0.0
        negate = False
        if a > b:
            a, b = b, a
            negate = True
        if n % 2 != 0:
            n += 1
        h = (b - a) / n
        total = 0.0
        try:
            total += f(a)
            for i in range(1, n):
                coeff = 4 if i % 2 == 1 else 2
                total += coeff * f(a + i * h)
            total += f(b)
        except Exception:
            raise CalcEngineError("Math ERROR")
        result = (h / 3) * total
        if negate:
            result = -result
        if math.isnan(result) or math.isinf(result):
            raise CalcEngineError("Math ERROR")
        return result

    def sigma(self, f, start, end, step=1):
        if start > end:
            return 0.0
        num_steps = (end - start) // step + 1
        if num_steps > 1000:
            raise CalcEngineError("Range ERROR")
        total = 0.0
        try:
            for x in range(start, end + 1, step):
                total += f(x)
        except Exception:
            raise CalcEngineError("Math ERROR")
        if math.isnan(total) or math.isinf(total):
            raise CalcEngineError("Math ERROR")
        return total

    def pi_product(self, f, start, end, step=1):
        if start > end:
            return 1.0
        num_steps = (end - start) // step + 1
        if num_steps > 1000:
            raise CalcEngineError("Range ERROR")
        result = 1.0
        try:
            for x in range(start, end + 1, step):
                result *= f(x)
                if math.isnan(result) or math.isinf(result):
                    raise CalcEngineError("Math ERROR")
        except CalcEngineError:
            raise
        except Exception:
            raise CalcEngineError("Math ERROR")
        return result

    def solve(self, func: callable, initial_guess: float,
              tolerance: float = 1e-10, max_iter: int = 1000) -> float:
        """
        Find x such that func(x) = 0.

        Algorithm: Newton-Raphson with 5-point central difference derivative.
        Fallback: Secant method when derivative magnitude < 1e-12.

        Parameters:
            func          : callable, takes float, returns float
            initial_guess : starting x
            tolerance     : convergence criterion on |f(x)|
            max_iter      : iteration cap

        Returns:
            float root of func
        """
        x = float(initial_guess)

        for _ in range(max_iter):
            fx = func(x)

            if abs(fx) < tolerance:
                return x

            # 5-point central difference derivative
            h = max(1e-8, abs(x) * 1e-8)

            try:
                fpx = (
                    -func(x + 2*h)
                    + 8*func(x + h)
                    - 8*func(x - h)
                    + func(x - 2*h)
                ) / (12.0 * h)
            except Exception:
                fpx = 0.0

            if abs(fpx) < 1e-12:
                # Secant fallback
                delta = 1e-4 if x == 0.0 else abs(x) * 1e-4
                x2 = x + delta
                fx2 = func(x2)
                diff = fx2 - fx

                if abs(diff) < 1e-14:
                    raise CalcEngineError(
                        "Solve failed: derivative and secant both near zero — no root near initial guess"
                    )

                x = x - fx * (x2 - x) / diff
            else:
                x = x - fx / fpx

        raise CalcEngineError(
            f"Solve did not converge after {max_iter} iterations"
        )