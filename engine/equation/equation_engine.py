import math
import cmath
import copy


class EquationEngineError(Exception):
    """Custom exception for all errors in the EquationEngine module."""

    def __str__(self):
        return self.args[0] if self.args else ""


class EquationEngine:
    """Numerical equation solver emulating the Casio fx-991EX ClassWiz."""

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # METHOD 1: Quadratic solver
    # ------------------------------------------------------------------

    def solve_quadratic(self, a: float, b: float, c: float) -> list:
        """Solve a*x^2 + b*x + c = 0 and return [x1, x2] as complex values."""
        if abs(a) < 1e-15:
            raise EquationEngineError("Not a quadratic (a=0)")

        D = b * b - 4.0 * a * c
        sqrt_D = cmath.sqrt(complex(D))

        # Numerically stable form to avoid catastrophic cancellation
        if b >= 0:
            x1 = (-b - sqrt_D) / (2.0 * a)
            if abs(x1) > 1e-15:
                x2 = c / (a * x1)
            else:
                x2 = (-b + sqrt_D) / (2.0 * a)
        else:
            x1 = (-b + sqrt_D) / (2.0 * a)
            if abs(x1) > 1e-15:
                x2 = c / (a * x1)
            else:
                x2 = (-b - sqrt_D) / (2.0 * a)

        return [x1, x2]

    # ------------------------------------------------------------------
    # METHOD 2: Cubic solver
    # ------------------------------------------------------------------

    def solve_cubic(self, a: float, b: float, c: float, d: float) -> list:
        """Solve a*x^3 + b*x^2 + c*x + d = 0 and return [r1, r2, r3] as complex values."""
        if abs(a) < 1e-15:
            raise EquationEngineError("Not a cubic (a=0)")

        # STEP 1 – Normalise
        p_coef = b / a   # coefficient of x²
        q_coef = c / a   # coefficient of x
        r_coef = d / a   # constant term

        # STEP 2 – Depress the cubic: x = t - p_coef/3
        P = q_coef - (p_coef ** 2) / 3.0
        Q = r_coef - p_coef * q_coef / 3.0 + 2.0 * (p_coef ** 3) / 27.0
        shift = p_coef / 3.0

        # STEP 3 – Discriminant
        DELTA = -(4.0 * P ** 3 + 27.0 * Q ** 2)

        # STEP 4 – Solve by case

        # CASE A: three distinct real roots — trigonometric method
        if DELTA > 1e-10:
            m = 2.0 * math.sqrt(-P / 3.0)
            theta = math.acos((3.0 * Q) / (P * m)) / 3.0
            t0 = m * math.cos(theta)
            t1 = m * math.cos(theta - 2.0 * math.pi / 3.0)
            t2 = m * math.cos(theta + 2.0 * math.pi / 3.0)
            roots = [
                complex(t0 - shift),
                complex(t1 - shift),
                complex(t2 - shift),
            ]

        # CASE B: repeated root
        elif abs(DELTA) <= 1e-10:
            if abs(Q) < 1e-15:
                # Triple root at the depressed origin → t = 0
                roots = [
                    complex(-shift),
                    complex(-shift),
                    complex(-shift),
                ]
            else:
                # Double root r and simple root s = -2*r
                # r = sign(Q) * |Q/2|^(1/3)
                sign_Q = 1.0 if Q >= 0 else -1.0
                r = sign_Q * abs(Q / 2.0) ** (1.0 / 3.0)
                s = -2.0 * r
                roots = [
                    complex(r - shift),   # double root (first occurrence)
                    complex(r - shift),   # double root (second occurrence)
                    complex(s - shift),   # simple root
                ]

        # CASE C: one real root + two complex conjugates — Cardano's formula
        else:
            inner = (Q / 2.0) ** 2 + (P / 3.0) ** 3
            sqrt_inner = math.sqrt(inner)
            u_base = -Q / 2.0 + sqrt_inner
            v_base = -Q / 2.0 - sqrt_inner
            # Real cube roots, sign-preserving
            u = math.copysign(abs(u_base) ** (1.0 / 3.0), u_base)
            v = math.copysign(abs(v_base) ** (1.0 / 3.0), v_base)
            # Enforce u*v == -P/3 for numerical stability
            if abs(u) > 1e-15:
                v = -P / (3.0 * u)
            real_root = u + v - shift
            real_part_complex = -(u + v) / 2.0 - shift
            imag_part = (u - v) * math.sqrt(3.0) / 2.0
            roots = [
                complex(real_root),
                complex(real_part_complex,  imag_part),
                complex(real_part_complex, -imag_part),
            ]

        return roots

    # ------------------------------------------------------------------
    # METHOD 3: Simultaneous 2×2 solver
    # ------------------------------------------------------------------

    def solve_simultaneous_2(self, coeffs: list) -> list:
        """Solve a 2×2 linear system via Cramer's rule.

        coeffs = [[a1, b1, c1], [a2, b2, c2]]
        Equations: a1*x + b1*y = c1, a2*x + b2*y = c2
        Returns [x, y].
        """
        if len(coeffs) != 2 or not all(len(row) == 3 for row in coeffs):
            raise EquationEngineError("Invalid coefficient format")

        a1, b1, c1 = coeffs[0]
        a2, b2, c2 = coeffs[1]

        det = a1 * b2 - a2 * b1
        if abs(det) < 1e-15:
            raise EquationEngineError("No unique solution")

        x = (c1 * b2 - c2 * b1) / det
        y = (a1 * c2 - a2 * c1) / det
        return [x, y]

    # ------------------------------------------------------------------
    # METHOD 4: Simultaneous 3×3 solver
    # ------------------------------------------------------------------

    def solve_simultaneous_3(self, coeffs: list) -> list:
        """Solve a 3×3 linear system via Gaussian elimination with partial pivoting.

        coeffs = [[a1,b1,c1,d1], [a2,b2,c2,d2], [a3,b3,c3,d3]]
        Returns [x, y, z].
        """
        if len(coeffs) != 3 or not all(len(row) == 4 for row in coeffs):
            raise EquationEngineError("Invalid coefficient format")

        m = copy.deepcopy(coeffs)

        # Forward elimination with partial pivoting
        for col in range(3):
            # Find pivot row
            pivot_row = col
            for r in range(col + 1, 3):
                if abs(m[r][col]) > abs(m[pivot_row][col]):
                    pivot_row = r
            m[col], m[pivot_row] = m[pivot_row], m[col]

            if abs(m[col][col]) < 1e-15:
                raise EquationEngineError("No unique solution")

            for r in range(col + 1, 3):
                factor = m[r][col] / m[col][col]
                for j in range(col, 4):
                    m[r][j] -= factor * m[col][j]

        # Back substitution
        result = [0.0, 0.0, 0.0]
        for i in range(2, -1, -1):
            result[i] = m[i][3]
            for j in range(i + 1, 3):
                result[i] -= m[i][j] * result[j]
            result[i] /= m[i][i]

        return result

    # ------------------------------------------------------------------
    # METHOD 5: Simultaneous 4×4 solver
    # ------------------------------------------------------------------

    def solve_simultaneous_4(self, coefficients: list) -> list:
        """
        Solve a 4x4 linear system via Gaussian elimination with partial pivoting.

        Parameters:
            coefficients: list of 4 rows, each row = [a, b, c, d, e]
                          representing: ax + by + cz + dw = e

        Returns:
            [x, y, z, w] as list of floats
        """
        n = 4
        if len(coefficients) != 4 or any(len(row) != 5 for row in coefficients):
            raise EquationEngineError(
                "solve_simultaneous_4 requires exactly 4 rows of 5 coefficients each"
            )
        mat = [list(map(float, row)) for row in coefficients]

        # Forward elimination with partial pivoting
        for col in range(n):
            max_row = max(range(col, n), key=lambda r: abs(mat[r][col]))
            mat[col], mat[max_row] = mat[max_row], mat[col]
            if abs(mat[col][col]) < 1e-12:
                raise EquationEngineError(
                    "No unique solution: singular coefficient matrix"
                )
            for row in range(col + 1, n):
                factor = mat[row][col] / mat[col][col]
                for j in range(col, n + 1):
                    mat[row][j] -= factor * mat[col][j]

        # Back substitution
        solution = [0.0] * n
        for i in range(n - 1, -1, -1):
            solution[i] = mat[i][n]
            for j in range(i + 1, n):
                solution[i] -= mat[i][j] * solution[j]
            solution[i] /= mat[i][i]

        return solution

    # ------------------------------------------------------------------
    # METHOD 6: Quartic solver
    # ------------------------------------------------------------------

    def solve_quartic(self, a: float, b: float, c: float,
                      d: float, e: float) -> list:
        """
        Solve quartic ax^4 + bx^3 + cx^2 + dx + e = 0.

        Algorithm: Durand-Kerner simultaneous iteration.
        Finds all 4 roots including complex ones.

        Returns:
            List of 4 roots. Real roots as float.
            Complex roots as (real, imag) tuple.
        """
        import cmath

        if abs(a) < 1e-14:
            raise EquationEngineError(
                "Leading coefficient 'a' cannot be zero for quartic"
            )

        # Monic form
        p0 = b / a
        p1 = c / a
        p2 = d / a
        p3 = e / a

        def poly_eval(z):
            return z**4 + p0*z**3 + p1*z**2 + p2*z + p3

        # Initial guesses
        base = complex(0.4, 0.9)
        roots = [base**k for k in range(4)]

        # Durand-Kerner iterations
        for _ in range(2000):
            new_roots = []
            for i in range(4):
                fz = poly_eval(roots[i])
                denom = complex(1.0, 0.0)
                for j in range(4):
                    if i != j:
                        denom *= (roots[i] - roots[j])

                if abs(denom) < 1e-30:
                    new_roots.append(roots[i])
                else:
                    new_roots.append(roots[i] - fz / denom)

            if all(
                abs(new_roots[i] - roots[i]) < 1e-12
                for i in range(4)
            ):
                roots = new_roots
                break

            roots = new_roots

        # Format results.
        # Imaginary part below 1e-8 becomes a real float.
        result = []
        for r in roots:
            if abs(r.imag) < 1e-8:
                result.append(round(r.real, 10))
            else:
                result.append((round(r.real, 10), round(r.imag, 10)))

        return result

