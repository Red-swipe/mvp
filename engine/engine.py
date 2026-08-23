"""Coordinator engine for the casio_calculator.

Owns every tier-3 engine and dispatches mode-specific operations to the
corresponding engine. Basic arithmetic evaluation stays in this engine and
delegates to the root evaluation pipeline.
"""

from __future__ import annotations

from engine.evaluator import evaluate
from engine.parser import parse
from engine.tokenizer import tokenize

from engine.base_n import base_n_engine as bn
from engine.calculus.calculus_engine import CalculusEngine
from engine.complex import complex_engine as ce
from engine.distribution.distribution_engine import DistributionEngine
from engine.equation.equation_engine import EquationEngine
from engine.inequality.inequality_engine import InequalityEngine
from engine.matrix.matrix_engine import MatrixEngine
from engine.spreadsheet.spreadsheet_engine import SpreadsheetEngine
from engine.statistics.statistics_engine import StatisticsEngine
from engine.table.table_engine import TableEngine
from engine.vector.vector_engine import VectorEngine

MODE_CALC = "CALC"
MODE_COMPLEX = "COMPLEX"
MODE_BASE_N = "BASE_N"
MODE_STATISTICS = "STATISTICS"
MODE_EQUATION = "EQUATION"
MODE_MATRIX = "MATRIX"
MODE_VECTOR = "VECTOR"
MODE_INEQUALITY = "INEQUALITY"
MODE_DISTRIBUTION = "DISTRIBUTION"
MODE_TABLE = "TABLE"
MODE_SPREADSHEET = "SPREADSHEET"
MODE_CALCULUS = "CALCULUS"

MODES = frozenset([
    MODE_CALC,
    MODE_COMPLEX,
    MODE_BASE_N,
    MODE_STATISTICS,
    MODE_EQUATION,
    MODE_MATRIX,
    MODE_VECTOR,
    MODE_INEQUALITY,
    MODE_DISTRIBUTION,
    MODE_TABLE,
    MODE_SPREADSHEET,
    MODE_CALCULUS,
])


class Engine:
    """Central coordinator that owns every tier-3 engine and dispatches
    mode-specific operations to them."""

    def __init__(self) -> None:
        self._display_text: str = ""
        self._expression: list[str] = []
        self._last_result: float | None = None
        self._mode: str = MODE_CALC
        self._statistics = StatisticsEngine()
        self._matrix = MatrixEngine()
        self._inequality = InequalityEngine()
        self._table = TableEngine()
        self._spreadsheet = SpreadsheetEngine()
        self._distribution = DistributionEngine()
        self._equation = EquationEngine()
        self._calculus = CalculusEngine()
        self._vector = VectorEngine()

    @property
    def display_text(self) -> str:
        return self._display_text

    @property
    def last_result(self) -> float | None:
        return self._last_result

    def get_mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode!r}")
        self._mode = mode

    def _require_mode(self, expected: str) -> None:
        if self._mode != expected:
            raise RuntimeError(
                f"Operation requires mode {expected!r}, current mode is {self._mode!r}"
            )

    def reset(self) -> None:
        self._display_text = ""
        self._expression = []
        self._last_result = None
        self._mode = MODE_CALC
        self._statistics.reset()
        self._vector.reset()
        self._inequality.reset()
        self._table.clear()
        self._spreadsheet.clear_all()

    def evaluate(self, text: str) -> float:
        self._require_mode(MODE_CALC)
        self._display_text = text
        self._expression = tokenize(text)
        self._last_result = float(evaluate(parse(self._expression)))
        return self._last_result

    def complex_rect(self, a: float, b: float):
        self._require_mode(MODE_COMPLEX)
        return ce.to_complex(a, b)

    def complex_polar(self, r: float, theta: float):
        self._require_mode(MODE_COMPLEX)
        return ce.from_polar(r, theta)

    def complex_real(self, z):
        self._require_mode(MODE_COMPLEX)
        return ce.real_part(z)

    def complex_imag(self, z):
        self._require_mode(MODE_COMPLEX)
        return ce.imag_part(z)

    def complex_argument(self, z):
        self._require_mode(MODE_COMPLEX)
        return ce.argument(z)

    def complex_modulus(self, z):
        self._require_mode(MODE_COMPLEX)
        return ce.modulus(z)

    def complex_conjugate(self, z):
        self._require_mode(MODE_COMPLEX)
        return ce.conjugate(z)

    def complex_to_polar(self, z):
        self._require_mode(MODE_COMPLEX)
        return ce.to_polar(z)

    def complex_to_rect(self, r: float, theta: float):
        self._require_mode(MODE_COMPLEX)
        return ce.to_rect(r, theta)

    def complex_add(self, z1, z2):
        self._require_mode(MODE_COMPLEX)
        return ce.cadd(z1, z2)

    def complex_subtract(self, z1, z2):
        self._require_mode(MODE_COMPLEX)
        return ce.csub(z1, z2)

    def complex_multiply(self, z1, z2):
        self._require_mode(MODE_COMPLEX)
        return ce.cmul(z1, z2)

    def complex_divide(self, z1, z2):
        self._require_mode(MODE_COMPLEX)
        return ce.cdiv(z1, z2)

    def complex_power(self, z1, z2):
        self._require_mode(MODE_COMPLEX)
        return ce.cpow(z1, z2)

    def complex_sqrt(self, z):
        self._require_mode(MODE_COMPLEX)
        return ce.csqrt(z)

    def base_n_to_base(self, n, base):
        self._require_mode(MODE_BASE_N)
        return bn.to_base(n, base)

    def base_n_from_base(self, s, base):
        self._require_mode(MODE_BASE_N)
        return bn.from_base(s, base)

    def base_n_to_bin(self, n):
        self._require_mode(MODE_BASE_N)
        return bn.to_bin(n)

    def base_n_to_oct(self, n):
        self._require_mode(MODE_BASE_N)
        return bn.to_oct(n)

    def base_n_to_dec(self, n):
        self._require_mode(MODE_BASE_N)
        return bn.to_dec(n)

    def base_n_to_hex(self, n):
        self._require_mode(MODE_BASE_N)
        return bn.to_hex(n)

    def base_n_from_bin(self, s):
        self._require_mode(MODE_BASE_N)
        return bn.from_bin(s)

    def base_n_from_oct(self, s):
        self._require_mode(MODE_BASE_N)
        return bn.from_oct(s)

    def base_n_from_dec(self, s):
        self._require_mode(MODE_BASE_N)
        return bn.from_dec(s)

    def base_n_from_hex(self, s):
        self._require_mode(MODE_BASE_N)
        return bn.from_hex(s)

    def base_n_band(self, a, b):
        self._require_mode(MODE_BASE_N)
        return bn.band(a, b)

    def base_n_bor(self, a, b):
        self._require_mode(MODE_BASE_N)
        return bn.bor(a, b)

    def base_n_bxor(self, a, b):
        self._require_mode(MODE_BASE_N)
        return bn.bxor(a, b)

    def base_n_bxnor(self, a, b):
        self._require_mode(MODE_BASE_N)
        return bn.bxnor(a, b)

    def base_n_bnot(self, n):
        self._require_mode(MODE_BASE_N)
        return bn.bnot(n)

    def base_n_bneg(self, n):
        self._require_mode(MODE_BASE_N)
        return bn.bneg(n)

    def stats_set_1var(self, data, freq=None):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.set_1var(data, freq)

    def stats_set_2var(self, xdata, ydata, freq=None):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.set_2var(xdata, ydata, freq)

    def stats_clear(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.clear()

    def stats_reset(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.reset()

    def stats_get_state(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.get_state()

    def stats_n(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.n()

    def stats_sum_x(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.sum_x()

    def stats_sum_x2(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.sum_x2()

    def stats_sum_y(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.sum_y()

    def stats_sum_y2(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.sum_y2()

    def stats_sum_xy(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.sum_xy()

    def stats_mean(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.mean()

    def stats_population_variance(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.population_variance()

    def stats_sample_variance(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.sample_variance()

    def stats_population_std(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.population_std()

    def stats_sample_std(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.sample_std()

    def stats_min(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.min_val()

    def stats_max(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.max_val()

    def stats_median(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.median()

    def stats_mode(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.mode_val()

    def stats_mean_x(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.mean_x()

    def stats_mean_y(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.mean_y()

    def stats_linear_regression(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.linear_regression()

    def stats_correlation(self):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.correlation()

    def stats_predict_y(self, x):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.predict_y(x)

    def stats_predict_x(self, y):
        self._require_mode(MODE_STATISTICS)
        return self._statistics.predict_x(y)

    def stats_log_regression(self) -> dict:
        return self._statistics.log_regression()

    def stats_exp_e_regression(self) -> dict:
        return self._statistics.exp_e_regression()

    def stats_exp_ab_regression(self) -> dict:
        return self._statistics.exp_ab_regression()

    def stats_power_regression(self) -> dict:
        return self._statistics.power_regression()

    def stats_inverse_regression(self) -> dict:
        return self._statistics.inverse_regression()

    def stats_quadratic_regression(self) -> dict:
        return self._statistics.quadratic_regression()

    def equation_solve_quadratic(self, a, b, c):
        self._require_mode(MODE_EQUATION)
        return self._equation.solve_quadratic(a, b, c)

    def equation_solve_cubic(self, a, b, c, d):
        self._require_mode(MODE_EQUATION)
        return self._equation.solve_cubic(a, b, c, d)

    def equation_solve_simultaneous_2(self, coeffs):
        self._require_mode(MODE_EQUATION)
        return self._equation.solve_simultaneous_2(coeffs)

    def equation_solve_simultaneous_3(self, coeffs):
        self._require_mode(MODE_EQUATION)
        return self._equation.solve_simultaneous_3(coeffs)

    def equation_solve_simultaneous_4(self, coefficients: list) -> list:
        self._require_mode(MODE_EQUATION)
        return self._equation.solve_simultaneous_4(coefficients)

    def equation_solve_quartic(self, a: float, b: float, c: float,
                               d: float, e: float) -> list:
        self._require_mode(MODE_EQUATION)
        return self._equation.solve_quartic(a, b, c, d, e)


    def matrix_define(self, name, data):
        self._require_mode(MODE_MATRIX)
        return self._matrix.define_matrix(name, data)

    def matrix_get(self, name):
        self._require_mode(MODE_MATRIX)
        return self._matrix.get_matrix(name)

    def matrix_dimensions(self, name):
        self._require_mode(MODE_MATRIX)
        return self._matrix.dimensions(name)

    def matrix_add(self, name_a, name_b):
        self._require_mode(MODE_MATRIX)
        return self._matrix.add(name_a, name_b)

    def matrix_subtract(self, name_a, name_b):
        self._require_mode(MODE_MATRIX)
        return self._matrix.subtract(name_a, name_b)

    def matrix_multiply(self, name_a, name_b):
        self._require_mode(MODE_MATRIX)
        return self._matrix.multiply(name_a, name_b)

    def matrix_scalar_multiply(self, name, scalar):
        self._require_mode(MODE_MATRIX)
        return self._matrix.scalar_multiply(name, scalar)

    def matrix_transpose(self, name):
        self._require_mode(MODE_MATRIX)
        return self._matrix.transpose(name)

    def matrix_determinant(self, name):
        self._require_mode(MODE_MATRIX)
        return self._matrix.determinant(name)

    def matrix_inverse(self, name):
        self._require_mode(MODE_MATRIX)
        return self._matrix.inverse(name)

    def matrix_ref(self, name):
        self._require_mode(MODE_MATRIX)
        return self._matrix.ref(name)

    def matrix_rref(self, name):
        self._require_mode(MODE_MATRIX)
        return self._matrix.rref(name)

    def matrix_identity(self, n: int) -> list:
        self._require_mode(MODE_MATRIX)
        return self._matrix.identity(n)

    def vector_set_dimension(self, dim):
        self._require_mode(MODE_VECTOR)
        return self._vector.set_dimension(dim)

    def vector_store(self, name, components):
        self._require_mode(MODE_VECTOR)
        return self._vector.store_vector(name, components)

    def vector_get(self, name):
        self._require_mode(MODE_VECTOR)
        return self._vector.get_vector(name)

    def vector_add(self, a, b):
        self._require_mode(MODE_VECTOR)
        return self._vector.add(a, b)

    def vector_subtract(self, a, b):
        self._require_mode(MODE_VECTOR)
        return self._vector.subtract(a, b)

    def vector_scalar_multiply(self, name, scalar):
        self._require_mode(MODE_VECTOR)
        return self._vector.scalar_multiply(name, scalar)

    def vector_magnitude(self, name):
        self._require_mode(MODE_VECTOR)
        return self._vector.magnitude(name)

    def vector_unit(self, name):
        self._require_mode(MODE_VECTOR)
        return self._vector.unit_vector(name)

    def vector_dot(self, a, b):
        self._require_mode(MODE_VECTOR)
        return self._vector.dot_product(a, b)

    def vector_cross(self, a, b):
        self._require_mode(MODE_VECTOR)
        return self._vector.cross_product(a, b)

    def vector_angle(self, a, b):
        self._require_mode(MODE_VECTOR)
        return self._vector.angle_between(a, b)

    def vector_reset(self):
        self._require_mode(MODE_VECTOR)
        return self._vector.reset()

    def vector_get_state(self):
        self._require_mode(MODE_VECTOR)
        return self._vector.get_state()

    def inequality_set_quadratic(self, a, b, c, operator=">"):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.set_quadratic(a, b, c, operator)

    def inequality_set_cubic(self, a, b, c, d, operator=">"):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.set_cubic(a, b, c, d, operator)

    def inequality_set_quartic(self, a, b, c, d, e, operator=">"):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.set_quartic(a, b, c, d, e, operator)

    def inequality_get_state(self):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.get_state()

    def inequality_evaluate(self, x):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.evaluate(x)

    def inequality_satisfies(self, x):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.satisfies(x)

    def inequality_solve(self):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.solve()

    def inequality_solution_as_string(self):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.solution_as_string()

    def inequality_reset(self):
        self._require_mode(MODE_INEQUALITY)
        return self._inequality.reset()

    def distribution_set_parameters(self, mu, sigma):
        self._require_mode(MODE_DISTRIBUTION)
        return self._distribution.set_parameters(mu, sigma)

    def distribution_normal_pd(self, x):
        self._require_mode(MODE_DISTRIBUTION)
        return self._distribution.normal_pd(x)

    def distribution_normal_cd(self, lower, upper):
        self._require_mode(MODE_DISTRIBUTION)
        return self._distribution.normal_cd(lower, upper)

    def distribution_inverse_normal(self, area):
        self._require_mode(MODE_DISTRIBUTION)
        return self._distribution.inverse_normal(area)

    def distribution_binomial_pd(self, x: int, n: int, p: float) -> float:
        return self._distribution.binomial_pd(x, n, p)

    def distribution_binomial_cd(self, x: int, n: int, p: float) -> float:
        return self._distribution.binomial_cd(x, n, p)

    def distribution_poisson_pd(self, x: int, mu: float) -> float:
        return self._distribution.poisson_pd(x, mu)

    def distribution_poisson_cd(self, x: int, mu: float) -> float:
        return self._distribution.poisson_cd(x, mu)

    def table_set_f(self, expr):
        self._require_mode(MODE_TABLE)
        return self._table.set_f(expr)

    def table_set_g(self, expr):
        self._require_mode(MODE_TABLE)
        return self._table.set_g(expr)

    def table_generate(self, x_start, x_end, x_step):
        self._require_mode(MODE_TABLE)
        return self._table.generate(x_start, x_end, x_step)

    def table_clear(self):
        self._require_mode(MODE_TABLE)
        return self._table.clear()

    def table_last(self):
        self._require_mode(MODE_TABLE)
        return self._table.last_table()

    def spreadsheet_set_cell(self, cell_ref, value):
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.set_cell(cell_ref, value)

    def spreadsheet_get_value(self, cell_ref):
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.get_cell_value(cell_ref)

    def spreadsheet_get_cell_raw(self, cell_ref):
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.get_cell_raw(cell_ref)

    def spreadsheet_clear_cell(self, cell_ref):
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.clear_cell(cell_ref)

    def spreadsheet_clear_all(self):
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.clear_all()

    def spreadsheet_evaluate_all(self):
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.evaluate_all()

    def spreadsheet_fill_value(
        self, start_cell: str, end_cell: str, value: float
    ) -> None:
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.fill_value(start_cell, end_cell, value)

    def spreadsheet_fill_formula(
        self, start_cell: str, end_cell: str, formula: str
    ) -> None:
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.fill_formula(start_cell, end_cell, formula)

    def spreadsheet_min(self, start_cell: str, end_cell: str) -> float:
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.min_val(start_cell, end_cell)

    def spreadsheet_max(self, start_cell: str, end_cell: str) -> float:
        self._require_mode(MODE_SPREADSHEET)
        return self._spreadsheet.max_val(start_cell, end_cell)

    def calculus_differentiate(self, f, x, tol=1e-8):
        self._require_mode(MODE_CALCULUS)
        return self._calculus.differentiate(f, x, tol)

    def calculus_integrate(self, f, a, b, n=1000):
        self._require_mode(MODE_CALCULUS)
        return self._calculus.integrate(f, a, b, n)

    def calculus_sigma(self, f, start, end, step=1):
        self._require_mode(MODE_CALCULUS)
        return self._calculus.sigma(f, start, end, step)

    def calculus_pi_product(self, f, start, end, step=1):
        self._require_mode(MODE_CALCULUS)
        return self._calculus.pi_product(f, start, end, step)

    def calculus_solve(self, func: callable, initial_guess: float,
                       tolerance: float = 1e-10, max_iter: int = 1000) -> float:
        self._require_mode(MODE_CALCULUS)
        return self._calculus.solve(func, initial_guess, tolerance, max_iter)
