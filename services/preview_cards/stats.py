"""Small statistics for card claims: how sure can a viewer be about a split like 29 of 49?"""
from __future__ import annotations

import math
from typing import Tuple

Z95 = 1.959964


def wilson(successes: int, n: int, z: float = Z95) -> Tuple[float, float]:
    """95% Wilson score interval for a proportion, as fractions. (0, 1) when n is 0."""
    if n <= 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def within_noise(successes: int, n: int) -> bool:
    """True when the likely range still includes an even split."""
    lo, hi = wilson(successes, n)
    return lo <= 0.5 <= hi
