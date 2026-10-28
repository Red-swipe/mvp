"""Regression coverage for calculator numerical differentiation precision."""

import math

import pytest

from engine.calculus.calculus_engine import CalculusEngine


@pytest.mark.parametrize(
    ("function", "point", "expected"),
    [
        (lambda x: x, 3.0, 1.0),
        (lambda x: x**2, 2.0, 4.0),
        (lambda x: x**3, 2.0, 12.0),
        (math.sin, 0.0, 1.0),
        (math.exp, 0.0, 1.0),
    ],
)
def test_differentiate_precision(function, point, expected):
    assert round(CalculusEngine().differentiate(function, point), 10) == expected
