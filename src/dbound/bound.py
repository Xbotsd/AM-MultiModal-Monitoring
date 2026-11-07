"""The detectability bound and its inverse (design-rule) forms.

Model
-----
A flaw of diameter ``a`` and contrast ``dI`` imaged with a PSF of FWHM ``L`` and
additive white noise of standard deviation ``sigma`` per voxel, with ``N``
independent looks.  The optimal deflection is

    d'(a) = (dI / sigma) * sqrt(E(a/L) * N),     E(x) = ||blur(sphere(x))||^2

Neyman-Pearson plus Cauchy-Schwarz give, for any detector at false-alarm ``alpha``,

    POD(a) <= Phi( d'(a) - z_{1-alpha} )

and the energy functional carries the whole geometry:

    E(x) ~ (pi/6)^2 x^6   (x << 1)      d' ~ a^3
    E(x) ~ (pi/6)   x^3   (x >> 1)      d' ~ a^{3/2}
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import psf

X_MIN, X_MAX = 0.2, 24.0
SMALL_LIMIT = 0.3
_CURVE: tuple[np.ndarray, np.ndarray] | None = None
_S_VOX: float | None = None


def ndtr(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def z_from_p(p: float, lo: float = -12.0, hi: float = 12.0) -> float:
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if ndtr(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def gaussian_energy_sum() -> float:
    """Sum of squared samples of the unit-FWHM Gaussian on the voxel grid."""
    global _S_VOX
    if _S_VOX is None:
        k = psf.gaussian_kernel(64, 1.0)
        _S_VOX = float((k * k).sum())
    return _S_VOX


def energy_at(x: float) -> float:
    """E(x), sampled the way a detector sees it (centre-aligned voxel grid)."""
    if x <= SMALL_LIMIT:
        return gaussian_energy_sum() * (math.pi / 6.0) ** 2 * x ** 6
    ss, grid = (8, 192) if x < 2.0 else (4, 128)
    d_fine = x * ss
    obj = psf.sphere_mass(grid, d_fine)
    blurred = psf.blur(obj, psf.gaussian_kernel(grid, float(ss)))
    sub = blurred[::ss, ::ss, ::ss]
    return float((sub * sub).sum())


def energy_curve(n_points: int = 32) -> tuple[np.ndarray, np.ndarray]:
    global _CURVE
    if _CURVE is None:
        xs = np.geomspace(X_MIN, X_MAX, n_points)
        _CURVE = (xs, np.array([energy_at(float(x)) for x in xs]))
    return _CURVE


def local_dprime_exponent(x: float) -> float:
    xs, es = energy_curve()
    i = int(np.clip(np.searchsorted(xs, x), 1, len(xs) - 2))
    lx, le = np.log(xs[i - 1:i + 2]), np.log(es[i - 1:i + 2])
    return 0.5 * float(np.polyfit(lx, le, 1)[0])


def dprime(dI: float, sigma: float, x: float, n_looks: int = 1) -> float:
    return float((dI / sigma) * math.sqrt(energy_at(x) * n_looks))


def pod_bound(dI: float, sigma: float, x: float, alpha: float = 0.01,
              n_looks: int = 1) -> float:
    return ndtr(dprime(dI, sigma, x, n_looks) - z_from_p(1.0 - alpha))


def _x_from_energy(target_e: float) -> float:
    """Solve E(x) = target with a local cubic in log-log space.

    Linear interpolation is not accurate enough in the transition region, where
    E is neither a power law nor flat and the design rule is most sensitive.
    """
    xs, es = energy_curve()
    lx, le = np.log(xs), np.log(es)
    target = math.log(target_e)
    i = int(np.clip(np.searchsorted(le, target), 1, len(lx) - 3))
    idx = slice(i - 1, i + 3)
    coef = np.polyfit(lx[idx], le[idx], 3)
    lo, hi = lx[idx][0], lx[idx][-1]
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if np.polyval(coef, mid) < target:
            lo = mid
        else:
            hi = mid
    return float(np.exp(0.5 * (lo + hi)))


@dataclass
class Requirement:
    x_star: float
    voxel_max: float
    dprime_at_star: float


def required_voxel(a: float, dI: float, sigma: float, pod: float = 0.9,
                   alpha: float = 0.01, n_looks: int = 1) -> Requirement:
    z_req = z_from_p(pod) + z_from_p(1.0 - alpha)
    target = (z_req * sigma / (dI * math.sqrt(n_looks))) ** 2
    xs, es = energy_curve()
    if not (es.min() <= target <= es.max()):
        return Requirement(float("nan"), float("nan"), float("nan"))
    x_star = _x_from_energy(target)
    return Requirement(x_star, float(a / x_star), float(math.sqrt(target)))


def required_noise(a: float, L: float, dI: float, pod: float = 0.9,
                   alpha: float = 0.01, n_looks: int = 1) -> float:
    z_req = z_from_p(pod) + z_from_p(1.0 - alpha)
    return float(dI * math.sqrt(energy_at(max(a / L, X_MIN)) * n_looks) / z_req)


def repeats_to_match_resolution(ratio: float) -> float:
    """Repeat looks equivalent to shrinking the voxel by ``ratio``.

    Resolution-limited regime: d' ~ (a/L)^3, so the equivalent look count is
    ratio**6.  Noise-limited: ratio**3.
    """
    return float(ratio ** 6)
