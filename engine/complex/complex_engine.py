"""Complex-number engine for the Casio fx-991EX ClassWiz.

Provides construction, decomposition, polar/rectangular display forms and
basic arithmetic on complex numbers, backed by the built-in ``complex`` type.
"""

from __future__ import annotations

import cmath
import math


def to_complex(a: float | int, b: float | int) -> complex:
    """Build a complex number from its rectangular coordinates (a + bj)."""
    return complex(a, b)


def from_polar(r: float | int, theta: float | int) -> complex:
    """Build a complex number from polar coordinates (r, theta).

    Raises:
        ValueError: if ``r`` is negative.
    """
    if r < 0:
        raise ValueError("r must be non-negative")
    return cmath.rect(r, theta)


def real_part(z: complex) -> float:
    """Return the real part of ``z``."""
    return z.real


def imag_part(z: complex) -> float:
    """Return the imaginary part of ``z``."""
    return z.imag


def argument(z: complex) -> float:
    """Return the argument of ``z`` in radians, in the range (-pi, pi].

    Raises:
        ValueError: if ``z`` is zero.
    """
    if z == 0:
        raise ValueError("argument undefined for zero")
    return cmath.phase(z)


def modulus(z: complex) -> float:
    """Return the modulus of ``z`` (its distance from the origin)."""
    return math.hypot(z.real, z.imag)


def conjugate(z: complex) -> complex:
    """Return the complex conjugate of ``z``."""
    return complex(z.real, -z.imag)


def to_polar(z: complex) -> tuple[float, float]:
    """Convert ``z`` to polar form (r, theta) with theta in (-pi, pi]."""
    return cmath.polar(z)


def to_rect(r: float | int, theta: float | int) -> tuple[float, float]:
    """Convert polar coordinates (r, theta) to rectangular (a, b)."""
    return (r * math.cos(theta), r * math.sin(theta))


def cadd(z1: complex, z2: complex) -> complex:
    """Add two complex numbers."""
    return z1 + z2


def csub(z1: complex, z2: complex) -> complex:
    """Subtract ``z2`` from ``z1``."""
    return z1 - z2


def cmul(z1: complex, z2: complex) -> complex:
    """Multiply two complex numbers."""
    return z1 * z2


def cdiv(z1: complex, z2: complex) -> complex:
    """Divide ``z1`` by ``z2``.

    Raises:
        ValueError: if ``z2`` is zero.
    """
    if z2 == 0:
        raise ValueError("division by zero")
    return z1 / z2


def cpow(z1: complex, z2: complex) -> complex:
    """Raise ``z1`` to the power ``z2``."""
    return z1**z2


def csqrt(z: complex) -> complex:
    """Return the principal square root of ``z``."""
    return cmath.sqrt(z)
