"""Distribution engine for the Casio fx-991EX ClassWiz emulator (pure Python)."""

import math


# ---------- internal helpers (Wichura AS 241, inverse normal CDF) ----------
# CPython 3.11 has no math.erfinv (added in 3.13), so implement the inverse
# error function via the AS 241 rational approximation of the inverse normal
# CDF: erfinv(x) = sqrt(2) * Phi^-1((x + 1) / 2).  Max abs error ~1e-9,
# which is plenty for the 5-decimal-place assertions used by the tests.

_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)

_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)

_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)

_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)

_PLOW = 0.02425
_PHIGH = 1.0 - _PLOW


def _poly(x, coeffs):
    """Evaluate a polynomial in x with the given coefficients (ascending)."""
    result = 0.0
    for c in reversed(coeffs):
        result = result * x + c
    return result


def _norm_sinv(p):
    """Inverse of the standard normal CDF via the AS 241 approximation."""
    if p <= 0.0 or p >= 1.0:
        raise DistributionEngineError("Inverse Normal ERROR: area must be between 0 and 1")
    if p < _PLOW:
        q = math.sqrt(-2.0 * math.log(p))
        return _poly(q, _C) / _poly(q, _D)
    if p > _PHIGH:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -_poly(q, _C) / _poly(q, _D)
    q = p - 0.5
    r = q * q
    return _poly(r, _A) * q / (1.0 + _poly(r, _B))


def _erfinv(x):
    """Inverse of the error function: erfinv(x) = sqrt(2) * Phi^-1((x+1)/2)."""
    return _norm_sinv(0.5 * (x + 1.0)) / math.sqrt(2.0)


class DistributionEngineError(Exception):
    """Custom exception for all errors in this module."""


class DistributionEngine:
    """Supports Normal distribution calculations (PD, CD, Inverse Normal)."""

    def __init__(self):
        self.mu = 0.0
        self.sigma = 1.0

    # ---------- parameter setters ----------

    def set_parameters(self, mu, sigma):
        if sigma <= 0:
            raise DistributionEngineError("Sigma must be positive")
        self.mu = float(mu)
        self.sigma = float(sigma)

    # ---------- Normal distribution ----------

    def normal_pd(self, x):
        return (1.0 / (self.sigma * math.sqrt(2.0 * math.pi))) * math.exp(
            -(x - self.mu) ** 2 / (2.0 * self.sigma * self.sigma)
        )

    def normal_cd(self, lower, upper):
        if lower > upper:
            raise DistributionEngineError("Normal CD ERROR: lower must not exceed upper")
        z_lower = (lower - self.mu) / (self.sigma * math.sqrt(2.0))
        z_upper = (upper - self.mu) / (self.sigma * math.sqrt(2.0))
        return 0.5 * (math.erf(z_upper) - math.erf(z_lower))

    def inverse_normal(self, area: float, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Inverse normal CDF (probit). area is the cumulative probability."""
        import math
        if area <= 0.0 or area >= 1.0:
            raise ValueError("area must be strictly between 0 and 1")

        # Acklam rational approximation coefficients
        a = [-3.969683028665376e+01,  2.209460984245205e+02,
             -2.759285104469687e+02,  1.383577518672690e+02,
             -3.066479806614716e+01,  2.506628277459239e+00]
        b = [-5.447609879822406e+01,  1.615858368580409e+02,
             -1.556989798598866e+02,  6.680131188771972e+01,
             -1.328068155288572e+01]
        c = [-7.784894002430293e-03, -3.223964580411365e-01,
             -2.400758277161838e+00, -2.549732539343734e+00,
              4.374664141464968e+00,  2.938163982698783e+00]
        d = [ 7.784695709041462e-03,  3.224671290700398e-01,
              2.445134137142996e+00,  3.754408661907416e+00]

        p_low  = 0.02425
        p_high = 1.0 - p_low

        if p_low <= area <= p_high:
            q = area - 0.5
            r = q * q
            num = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q
            den = (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r + 1.0)
            x = num / den
        elif area < p_low:
            q = math.sqrt(-2.0 * math.log(area))
            num = ((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]
            den = (((d[0]*q+d[1])*q+d[2])*q+d[3])*q + 1.0
            x = num / den
        else:
            q = math.sqrt(-2.0 * math.log(1.0 - area))
            num = ((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]
            den = (((d[0]*q+d[1])*q+d[2])*q+d[3])*q + 1.0
            x = -(num / den)

        # Halley refinement (2 iterations for full double precision)
        for _ in range(2):
            e = 0.5 * math.erfc(-x / math.sqrt(2.0)) - area
            u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
            x = x - u / (1.0 + x * u / 2.0)

        return mu + sigma * x

    def binomial_pd(self, x: int, n: int, p: float) -> float:
        """
        Binomial Probability Distribution: P(X = x)
        Formula: C(n,x) * p^x * (1-p)^(n-x)
        Uses log-gamma to avoid overflow for large n.
        Parameters:
            x: number of successes (0 <= x <= n, integer)
            n: number of trials (positive integer)
            p: probability of success (0.0 <= p <= 1.0)
        """
        import math
        if not (0.0 <= p <= 1.0):
            raise ValueError("p must be in [0, 1]")
        x = int(x)
        n = int(n)
        if not (0 <= x <= n):
            raise ValueError("x must satisfy 0 <= x <= n")
        if p == 0.0:
            return 1.0 if x == 0 else 0.0
        if p == 1.0:
            return 1.0 if x == n else 0.0
        log_prob = (math.lgamma(n + 1)
                    - math.lgamma(x + 1)
                    - math.lgamma(n - x + 1)
                    + x * math.log(p)
                    + (n - x) * math.log(1.0 - p))
        return math.exp(log_prob)

    def binomial_cd(self, x: int, n: int, p: float) -> float:
        """
        Binomial Cumulative Distribution: P(X <= x)
        Formula: sum_{k=0}^{x} C(n,k) * p^k * (1-p)^(n-k)
        Parameters:
            x: upper bound (integer)
            n: number of trials (positive integer)
            p: probability of success (0.0 <= p <= 1.0)
        """
        if not (0.0 <= p <= 1.0):
            raise ValueError("p must be in [0, 1]")
        x = int(x)
        n = int(n)
        if x < 0:
            return 0.0
        x = min(x, n)
        return sum(self.binomial_pd(k, n, p) for k in range(x + 1))

    def poisson_pd(self, x: int, mu: float) -> float:
        """
        Poisson Probability Distribution: P(X = x)
        Formula: (mu^x * e^(-mu)) / x!
        Uses log to avoid overflow.
        Parameters:
            x: number of events (non-negative integer)
            mu: mean rate (lambda), must be > 0
        """
        import math
        if mu <= 0:
            raise ValueError("mu (lambda) must be positive")
        x = int(x)
        if x < 0:
            raise ValueError("x must be a non-negative integer")
        log_prob = x * math.log(mu) - mu - math.lgamma(x + 1)
        return math.exp(log_prob)

    def poisson_cd(self, x: int, mu: float) -> float:
        """
        Poisson Cumulative Distribution: P(X <= x)
        Formula: sum_{k=0}^{x} (mu^k * e^(-mu)) / k!
        Parameters:
            x: upper bound (non-negative integer)
            mu: mean rate (lambda), must be > 0
        """
        if mu <= 0:
            raise ValueError("mu (lambda) must be positive")
        x = int(x)
        if x < 0:
            return 0.0
        return sum(self.poisson_pd(k, mu) for k in range(x + 1))