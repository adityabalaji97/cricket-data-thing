"""
Duckworth-Lewis run-production curves, as used by Ganjoo's *T20 Metrics: A Primer* (Aug 2026).

R(b, w) is the average number of runs still to come with `b` legal balls left and `w` wickets down.

DL Standard (Primer eq. 6):
    R_std(b, w) = R0 * F(w) * (1 - exp(-b / beta(w)))

DL Pro (eq. 7), straightened for high-scoring conditions by lambda >= 1:
    R_pro(b, w, lam) = R0 * F(w) * lam**(n_w + 1) * (1 - exp(-b / (beta(w) * lam**n_w)))
    n_w = n0 * F(w)

F and beta are cubics in w with F(0) = 1. The Primer counts seven coefficients (R0 plus three
each for F and beta); it does not say which three of beta's four are free, so here beta keeps its
constant term (beta(0) = beta0) and three slopes -- eight numbers, one more than the Primer, and
the fit is no worse for it. n0 is the Primer's 1.04 unless refit.

lambda for a match comes from its par score (section 4.4): solve R_pro(120, 0, lam) = par, with
lam = 1 whenever par <= R_std(120, 0), so average and low-scoring conditions use the standard curve.

Everything here is vectorised numpy so it runs over millions of balls at once.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, Tuple

import numpy as np

FULL_INNINGS_BALLS = 120
MAX_WICKETS = 10


@dataclass(frozen=True)
class DLParams:
    r0: float
    f: Tuple[float, float, float]  # F(w) = 1 + f1 w + f2 w^2 + f3 w^3
    beta: Tuple[float, float, float, float]  # beta(w) = b0 + b1 w + b2 w^2 + b3 w^3
    n0: float = 1.04
    balls: int = FULL_INNINGS_BALLS

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "DLParams":
        return cls(
            r0=float(data["r0"]),
            f=tuple(float(x) for x in data["f"]),
            beta=tuple(float(x) for x in data["beta"]),
            n0=float(data.get("n0", 1.04)),
            balls=int(data.get("balls", FULL_INNINGS_BALLS)),
        )


def _poly_f(w: np.ndarray, f: Tuple[float, float, float]) -> np.ndarray:
    w = np.asarray(w, dtype=float)
    return np.clip(1.0 + f[0] * w + f[1] * w**2 + f[2] * w**3, 0.0, None)


def _poly_beta(w: np.ndarray, beta: Tuple[float, float, float, float]) -> np.ndarray:
    w = np.asarray(w, dtype=float)
    # A floor keeps the exponent finite if a fitted cubic dips late in the wicket range.
    return np.clip(beta[0] + beta[1] * w + beta[2] * w**2 + beta[3] * w**3, 1.0, None)


def r_std(b, w, params: DLParams) -> np.ndarray:
    """Standard DL runs-to-come. Zero with no balls or no wickets left."""
    b = np.asarray(b, dtype=float)
    w = np.asarray(w, dtype=float)
    value = params.r0 * _poly_f(w, params.f) * (1.0 - np.exp(-np.clip(b, 0, None) / _poly_beta(w, params.beta)))
    return np.where((b <= 0) | (w >= MAX_WICKETS), 0.0, value)


def r_pro(b, w, lam, params: DLParams) -> np.ndarray:
    """DL Pro runs-to-come for straightening factor `lam` (>= 1; 1 reproduces r_std)."""
    b = np.asarray(b, dtype=float)
    w = np.asarray(w, dtype=float)
    lam = np.asarray(lam, dtype=float)
    f_w = _poly_f(w, params.f)
    n_w = params.n0 * f_w
    value = (
        params.r0
        * f_w
        * lam ** (n_w + 1.0)
        * (1.0 - np.exp(-np.clip(b, 0, None) / (_poly_beta(w, params.beta) * lam**n_w)))
    )
    return np.where((b <= 0) | (w >= MAX_WICKETS), 0.0, value)


def solve_lambda(par, params: DLParams, balls: int = FULL_INNINGS_BALLS, lam_max: float = 4.0) -> np.ndarray:
    """
    lambda such that R_pro(balls, 0, lambda) = par (Primer eq. 8 with the par score in place of
    the first-innings total). 1 when par is at or below the standard curve's full-innings value.

    R_pro(balls, 0, lam) increases monotonically in lam, so a vectorised bisection is exact enough
    (40 halvings of [1, lam_max] is ~1e-12).
    """
    par = np.asarray(par, dtype=float)
    base = float(r_std(balls, 0, params))
    lo = np.ones_like(par)
    hi = np.full_like(par, lam_max)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        above = r_pro(balls, 0, mid, params) > par
        hi = np.where(above, mid, hi)
        lo = np.where(above, lo, mid)
    lam = 0.5 * (lo + hi)
    return np.where(np.isnan(par) | (par <= base), 1.0, lam)


@dataclass
class FitResult:
    params: DLParams
    rmse: float
    cells: int
    weights_total: float
    notes: Dict = field(default_factory=dict)


def fit_dl_standard(balls_left, wickets_down, mean_runs_to_come, counts, n0: float = 1.04) -> FitResult:
    """
    Weighted least squares fit of the standard curve to cell means.

    One observation per (balls left, wickets down) cell: the mean of (final total - score so far)
    over every complete first innings that passed through that state, weighted by how many did.
    """
    from scipy.optimize import least_squares

    b = np.asarray(balls_left, dtype=float)
    w = np.asarray(wickets_down, dtype=float)
    y = np.asarray(mean_runs_to_come, dtype=float)
    n = np.asarray(counts, dtype=float)
    sqrt_n = np.sqrt(n)

    def unpack(theta):
        return DLParams(r0=theta[0], f=tuple(theta[1:4]), beta=tuple(theta[4:8]), n0=n0)

    def residuals(theta):
        return (r_std(b, w, unpack(theta)) - y) * sqrt_n

    # Start from a curve with the right order of magnitude: ~170 at the start, ~140-ball decay,
    # and each wicket costing roughly a tenth of the remaining resource.
    theta0 = np.array([250.0, -0.08, -0.002, 0.0, 140.0, -8.0, 0.0, 0.0])
    fit = least_squares(residuals, theta0, method="trf", max_nfev=20000)
    params = unpack(fit.x)
    rmse = float(np.sqrt(np.sum((r_std(b, w, params) - y) ** 2 * n) / np.sum(n)))
    return FitResult(params=params, rmse=rmse, cells=int(len(y)), weights_total=float(n.sum()))
