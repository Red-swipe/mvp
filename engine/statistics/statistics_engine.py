"""Statistics engine for the Casio fx-991EX style calculator.

Implements one-variable and two-variable descriptive statistics plus simple
linear regression over frequency-weighted data, mirroring the statistics mode
of a scientific calculator. The module depends only on the standard library.
"""

from __future__ import annotations

import math


class StatisticsEngine:
    """Stateful statistics calculator for 1-var and 2-var data sets."""

    def __init__(self):
        self.mode = None
        self.data = []
        self.freq = []
        self.y_data = []

    def set_1var(self, data, freq=None):
        """Load a one-variable data set with optional frequencies."""
        data = list(data)
        if not data:
            raise ValueError("data must not be empty")
        if freq is None:
            freq = [1] * len(data)
        freq = list(freq)
        if len(freq) != len(data):
            raise ValueError("freq must have the same length as data")
        for f in freq:
            if f <= 0:
                raise ValueError("frequencies must be positive")
        self.data = [float(d) for d in data]
        self.freq = [float(f) for f in freq]
        self.y_data = []
        self.mode = "1-var"

    def set_2var(self, xdata, ydata, freq=None):
        """Load a two-variable data set with optional frequencies."""
        xdata = list(xdata)
        ydata = list(ydata)
        if not xdata or not ydata:
            raise ValueError("xdata and ydata must not be empty")
        if len(xdata) != len(ydata):
            raise ValueError("xdata and ydata must have the same length")
        if freq is None:
            freq = [1] * len(xdata)
        freq = list(freq)
        if len(freq) != len(xdata):
            raise ValueError("freq must have the same length as xdata")
        for f in freq:
            if f <= 0:
                raise ValueError("frequencies must be positive")
        self.data = [float(x) for x in xdata]
        self.y_data = [float(y) for y in ydata]
        self.freq = [float(f) for f in freq]
        self.mode = "2-var"

    def clear(self):
        """Reset the engine to an empty, mode-less state."""
        self.mode = None
        self.data = []
        self.freq = []
        self.y_data = []

    def reset(self):
        """Alias for clear()."""
        self.clear()

    def get_state(self):
        """Return a summary of the current engine state."""
        return {"mode": self.mode, "n": self.n() if self.mode else 0}

    def _flat_data(self):
        """Expand the frequency-weighted data into a plain list of values."""
        return [d for d, f in zip(self.data, self.freq) for _ in range(int(f))]

    def n(self):
        """Total number of observations (sum of frequencies)."""
        if self.mode is None:
            raise RuntimeError("no data loaded")
        return sum(self.freq)

    def sum_x(self):
        """Sum of x values (frequency-weighted)."""
        if self.mode is None:
            raise RuntimeError("no data loaded")
        return sum(d * f for d, f in zip(self.data, self.freq))

    def sum_x2(self):
        """Sum of squared x values (frequency-weighted)."""
        if self.mode is None:
            raise RuntimeError("no data loaded")
        return sum(d * d * f for d, f in zip(self.data, self.freq))

    def _require_1var(self):
        if self.mode != "1-var":
            raise RuntimeError("operation requires 1-var mode")

    def _require_2var(self):
        if self.mode != "2-var":
            raise RuntimeError("operation requires 2-var mode")

    def mean(self):
        """Arithmetic mean of the x values."""
        self._require_1var()
        return self.sum_x() / self.n()

    def population_variance(self):
        """Population variance of the x values."""
        self._require_1var()
        m = self.mean()
        return sum((d - m) ** 2 * f for d, f in zip(self.data, self.freq)) / self.n()

    def sample_variance(self):
        """Sample variance of the x values."""
        self._require_1var()
        if self.n() < 2:
            raise ValueError("sample variance requires at least 2 observations")
        return self.population_variance() * self.n() / (self.n() - 1)

    def population_std(self):
        """Population standard deviation of the x values."""
        self._require_1var()
        return math.sqrt(self.population_variance())

    def sample_std(self):
        """Sample standard deviation of the x values."""
        self._require_1var()
        return math.sqrt(self.sample_variance())

    def min_val(self):
        """Minimum x value (ignores frequency)."""
        self._require_1var()
        return min(self.data)

    def max_val(self):
        """Maximum x value (ignores frequency)."""
        self._require_1var()
        return max(self.data)

    def median(self):
        """Median of the frequency-weighted x values."""
        self._require_1var()
        flat = sorted(self._flat_data())
        n = len(flat)
        if n % 2 == 1:
            return flat[n // 2]
        return (flat[n // 2 - 1] + flat[n // 2]) / 2.0

    def mode_val(self):
        """Most frequent value of the frequency-weighted x values."""
        self._require_1var()
        counts = {}
        for v in self._flat_data():
            counts[v] = counts.get(v, 0) + 1
        max_count = max(counts.values())
        return min(v for v, c in counts.items() if c == max_count)

    def sum_y(self):
        """Sum of y values (frequency-weighted)."""
        self._require_2var()
        return sum(y * f for y, f in zip(self.y_data, self.freq))

    def sum_y2(self):
        """Sum of squared y values (frequency-weighted)."""
        self._require_2var()
        return sum(y * y * f for y, f in zip(self.y_data, self.freq))

    def sum_xy(self):
        """Sum of x*y products (frequency-weighted)."""
        self._require_2var()
        return sum(x * y * f for x, y, f in zip(self.data, self.y_data, self.freq))

    def mean_x(self):
        """Arithmetic mean of the x values (2-var mode)."""
        self._require_2var()
        return self.sum_x() / self.n()

    def mean_y(self):
        """Arithmetic mean of the y values."""
        self._require_2var()
        return self.sum_y() / self.n()

    def linear_regression(self):
        """Fit y = a + b*x by least squares. Returns a/type dict."""
        self._require_2var()
        n = self.n()
        sx = self.sum_x()
        sy = self.sum_y()
        sx2 = self.sum_x2()
        sxy = self.sum_xy()
        denom = n * sx2 - sx * sx
        if denom == 0:
            raise ValueError("cannot fit a linear regression to this data")
        b = (n * sxy - sx * sy) / denom
        a = (sy - b * sx) / n
        return {"a": a, "b": b, "type": "linear"}

    def correlation(self):
        """Pearson correlation coefficient of the x and y values."""
        self._require_2var()
        n = self.n()
        sx = self.sum_x()
        sy = self.sum_y()
        sx2 = self.sum_x2()
        sy2 = self.sum_y2()
        sxy = self.sum_xy()
        denom = math.sqrt((n * sx2 - sx * sx) * (n * sy2 - sy * sy))
        if denom == 0:
            raise ValueError("correlation is undefined for this data")
        return (n * sxy - sx * sy) / denom

    def predict_y(self, x):
        """Predict y for a given x using the fitted regression line."""
        fit = self.linear_regression()
        return fit["a"] + fit["b"] * x

    def predict_x(self, y):
        """Predict x for a given y using the fitted regression line."""
        fit = self.linear_regression()
        if fit["b"] == 0:
            raise ValueError("cannot invert a horizontal regression line")
        return (y - fit["a"]) / fit["b"]

    def _ols(self, u_list: list, v_list: list) -> tuple:
        """
        Ordinary Least Squares: regress v on u.
        Returns (slope, intercept, r, r_squared).
        All computed using pure arithmetic — no numpy.
        """
        n = len(u_list)
        if n < 2:
            raise ValueError("Need at least 2 data points for regression")
        Su  = sum(u_list)
        Sv  = sum(v_list)
        Suu = sum(u * u for u in u_list)
        Suv = sum(u * v for u, v in zip(u_list, v_list))
        Svv = sum(v * v for v in v_list)
        denom = n * Suu - Su * Su
        if abs(denom) < 1e-12:
            raise ValueError("Regression failed: x values produce singular system")
        slope     = (n * Suv - Su * Sv) / denom
        intercept = (Sv - slope * Su) / n
        num_r = n * Suv - Su * Sv
        den_r_sq = (n * Suu - Su**2) * (n * Svv - Sv**2)
        r = num_r / math.sqrt(den_r_sq) if den_r_sq > 0 else 0.0
        return slope, intercept, r, r * r

    def log_regression(self) -> dict:
        """
        Logarithmic regression: y = a + b*ln(x)
        Requires all x > 0.
        Returns {'a': float, 'b': float, 'r': float, 'r_squared': float}
        """
        if not self.data or not self.y_data:
            raise ValueError("No data. Call set_2var first.")
        if any(x <= 0 for x in self.data):
            raise ValueError("Logarithmic regression requires all x > 0")
        u = [math.log(x) for x in self.data]
        slope, intercept, r, r2 = self._ols(u, self.y_data)
        return {'a': intercept, 'b': slope, 'r': r, 'r_squared': r2}

    def exp_e_regression(self) -> dict:
        """
        e-Exponential regression: y = a * e^(bx)
        Requires all y > 0.
        Returns {'a': float, 'b': float, 'r': float, 'r_squared': float}
        """
        if not self.data or not self.y_data:
            raise ValueError("No data. Call set_2var first.")
        if any(y <= 0 for y in self.y_data):
            raise ValueError("e-Exponential regression requires all y > 0")
        v = [math.log(y) for y in self.y_data]
        slope, intercept, r, r2 = self._ols(self.data, v)
        return {'a': math.exp(intercept), 'b': slope, 'r': r, 'r_squared': r2}

    def exp_ab_regression(self) -> dict:
        """
        ab-Exponential regression: y = a * b^x
        Requires all y > 0.
        Returns {'a': float, 'b': float, 'r': float, 'r_squared': float}
        """
        if not self.data or not self.y_data:
            raise ValueError("No data. Call set_2var first.")
        if any(y <= 0 for y in self.y_data):
            raise ValueError("ab-Exponential regression requires all y > 0")
        v = [math.log(y) for y in self.y_data]
        slope, intercept, r, r2 = self._ols(self.data, v)
        return {'a': math.exp(intercept), 'b': math.exp(slope), 'r': r, 'r_squared': r2}

    def power_regression(self) -> dict:
        """
        Power regression: y = a * x^b
        Requires all x > 0 and all y > 0.
        Returns {'a': float, 'b': float, 'r': float, 'r_squared': float}
        """
        if not self.data or not self.y_data:
            raise ValueError("No data. Call set_2var first.")
        if any(x <= 0 for x in self.data) or any(y <= 0 for y in self.y_data):
            raise ValueError("Power regression requires all x > 0 and y > 0")
        u = [math.log(x) for x in self.data]
        v = [math.log(y) for y in self.y_data]
        slope, intercept, r, r2 = self._ols(u, v)
        return {'a': math.exp(intercept), 'b': slope, 'r': r, 'r_squared': r2}

    def inverse_regression(self) -> dict:
        """
        Inverse regression: y = a + b/x
        Requires all x != 0.
        Returns {'a': float, 'b': float, 'r': float, 'r_squared': float}
        """
        if not self.data or not self.y_data:
            raise ValueError("No data. Call set_2var first.")
        if any(x == 0 for x in self.data):
            raise ValueError("Inverse regression requires all x != 0")
        u = [1.0 / x for x in self.data]
        slope, intercept, r, r2 = self._ols(u, self.y_data)
        return {'a': intercept, 'b': slope, 'r': r, 'r_squared': r2}

    def quadratic_regression(self) -> dict:
        """
        Quadratic regression: y = a + bx + cx^2
        Solved via 3x3 normal equations using Gaussian elimination with partial pivoting.
        Returns {'a': float, 'b': float, 'c': float, 'r_squared': float}
        """
        if not self.data or not self.y_data:
            raise ValueError("No data. Call set_2var first.")
        n  = len(self.data)
        xs = self.data
        ys = self.y_data

        Sx   = sum(xs)
        Sx2  = sum(x**2 for x in xs)
        Sx3  = sum(x**3 for x in xs)
        Sx4  = sum(x**4 for x in xs)
        Sy   = sum(ys)
        Sxy  = sum(x * y for x, y in zip(xs, ys))
        Sx2y = sum(x**2 * y for x, y in zip(xs, ys))

        mat = [
            [float(n),  float(Sx),  float(Sx2), float(Sy)],
            [float(Sx), float(Sx2), float(Sx3), float(Sxy)],
            [float(Sx2), float(Sx3), float(Sx4), float(Sx2y)],
        ]

        for col in range(3):
            max_row = max(range(col, 3), key=lambda r: abs(mat[r][col]))
            mat[col], mat[max_row] = mat[max_row], mat[col]
            if abs(mat[col][col]) < 1e-12:
                raise ValueError(
                    "Quadratic regression: singular normal equations"
                )
            for row in range(col + 1, 3):
                factor = mat[row][col] / mat[col][col]
                for j in range(col, 4):
                    mat[row][j] -= factor * mat[col][j]

        coeffs = [0.0, 0.0, 0.0]
        for i in range(2, -1, -1):
            coeffs[i] = mat[i][3]
            for j in range(i + 1, 3):
                coeffs[i] -= mat[i][j] * coeffs[j]
            coeffs[i] /= mat[i][i]

        a, b, c = coeffs[0], coeffs[1], coeffs[2]

        y_mean = Sy / n
        SS_tot = sum((y - y_mean)**2 for y in ys)
        SS_res = sum(
            (y - (a + b*x + c*x**2))**2
            for x, y in zip(xs, ys)
        )
        r_squared = 1.0 - SS_res / SS_tot if SS_tot > 1e-12 else 1.0

        return {'a': a, 'b': b, 'c': c, 'r_squared': r_squared}
