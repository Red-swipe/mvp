"""Focused accuracy checks for the five-point Richardson derivative."""

import math

import pytest

from engine.calculus.calculus_engine import CalculusEngine


@pytest.mark.parametrize(
    ("function", "point", "expected"),
    [
        (lambda x: x**5 - 2 * x**3 + 7 * x, 2.0, 63.0),
        (math.sin, 0.7, math.cos(0.7)),
        (math.exp, 1.2, math.exp(1.2)),
        (math.log, 2.0, 0.5),
    ],
)
def test_differentiate_matches_exact_derivative(function, point, expected):
    result = CalculusEngine().differentiate(function, point)
    assert result == pytest.approx(expected, rel=1e-10, abs=1e-11)


def test_richardson_reduces_cancellation_for_small_derivative_on_large_offset():
    # The derivative is small compared with the function's 1e8 offset. A tiny
    # stencil loses useful digits to cancellation; extrapolation keeps the
    # result within 1e-6 of the exact derivative.
    result = CalculusEngine().differentiate(lambda x: 1e8 + x * x, 2.0)
    assert result == pytest.approx(4.0, rel=0, abs=1e-6)
