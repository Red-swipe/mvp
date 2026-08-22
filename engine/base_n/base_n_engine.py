"""Base-N mode engine for the Casio fx-991EX ClassWiz.

Provides conversions between decimal integers and base-2/8/10/16
representations, plus 32-bit bitwise operations.
"""

from __future__ import annotations

import re

_VALID_BASES = (2, 8, 10, 16)
_DIGITS = "0123456789ABCDEF"
_MASK32 = 0xFFFFFFFF

_BASE_PATTERNS = {
    2: re.compile(r"[01]+"),
    8: re.compile(r"[0-7]+"),
    10: re.compile(r"[0-9]+"),
    16: re.compile(r"[0-9a-fA-F]+"),
}


def _require_base(base: int) -> None:
    """Raise ValueError if base is not a supported base."""
    if base not in _VALID_BASES:
        raise ValueError("base must be one of 2, 8, 10, 16")


def to_base(n: int, base: int) -> str:
    """Convert a non-negative integer to a string in the given base.

    Raises:
        ValueError: if n is negative or base is not 2, 8, 10, or 16.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    _require_base(base)
    if n == 0:
        return "0"
    digits = []
    while n:
        n, rem = divmod(n, base)
        digits.append(_DIGITS[rem])
    return "".join(reversed(digits))


def from_base(s: str, base: int) -> int:
    """Convert a string in the given base to a non-negative integer.

    Raises:
        ValueError: if s contains invalid digits or base is not
            2, 8, 10, or 16.
    """
    _require_base(base)
    if not _BASE_PATTERNS[base].fullmatch(s):
        raise ValueError(f"invalid digits for base {base}")
    return int(s, base)


def to_bin(n: int) -> str:
    """Convert a non-negative integer to a binary string."""
    return to_base(n, 2)


def to_oct(n: int) -> str:
    """Convert a non-negative integer to an octal string."""
    return to_base(n, 8)


def to_dec(n: int) -> str:
    """Convert a non-negative integer to a decimal string."""
    return to_base(n, 10)


def to_hex(n: int) -> str:
    """Convert a non-negative integer to an uppercase hexadecimal string."""
    return to_base(n, 16)


def from_bin(s: str) -> int:
    """Convert a binary string to a non-negative integer."""
    return from_base(s, 2)


def from_oct(s: str) -> int:
    """Convert an octal string to a non-negative integer."""
    return from_base(s, 8)


def from_dec(s: str) -> int:
    """Convert a decimal string to a non-negative integer."""
    return from_base(s, 10)


def from_hex(s: str) -> int:
    """Convert a hexadecimal string to a non-negative integer."""
    return from_base(s, 16)


def _require_operands(a: int, b: int) -> None:
    """Raise ValueError if either operand is negative."""
    if a < 0 or b < 0:
        raise ValueError("operands must be non-negative integers")


def band(a: int, b: int) -> int:
    """Return the bitwise AND of two non-negative integers."""
    _require_operands(a, b)
    return a & b


def bor(a: int, b: int) -> int:
    """Return the bitwise OR of two non-negative integers."""
    _require_operands(a, b)
    return a | b


def bxor(a: int, b: int) -> int:
    """Return the bitwise XOR of two non-negative integers."""
    _require_operands(a, b)
    return a ^ b


def bxnor(a: int, b: int) -> int:
    """Return the 32-bit bitwise XNOR of two non-negative integers."""
    _require_operands(a, b)
    return (~(a ^ b)) & _MASK32


def bnot(a: int) -> int:
    """Return the 32-bit bitwise NOT of a non-negative integer."""
    if a < 0:
        raise ValueError("operands must be non-negative integers")
    return _MASK32 ^ a


def bneg(a: int) -> int:
    """Return the two's-complement negation of a non-negative integer."""
    if a < 0:
        raise ValueError("operands must be non-negative integers")
    return (~a + 1) & _MASK32
