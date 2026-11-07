"""Matched-filter templates and reference detectors.

Three template constructions are provided, and the difference between them is the
subject of one of the ablations:

``dc``          sphere blurred by the PSF, no mean removal at all.  The statistic
                then measures the local grey level times the template sum, which
                swamps the defect on real data.
``zero_mean``   the same, minus its mean over the patch.  Correct for white noise
                with unknown offset, but the mean is taken over a large support,
                which leaves a long lever arm on the far field.
``annular``     minus a concentric shell of equal volume.  Zero-mean locally, so a
                background gradient cannot dominate.  This is the reference
                implementation for all real-data results.
"""

from __future__ import annotations

import numpy as np

from . import psf


def template(a: float, fwhm: float, kind: str = "annular",
             pad: int = 0) -> np.ndarray:
    """Matched-filter template for a sphere of diameter ``a`` (voxels)."""
    sigma = fwhm / psf.FWHM_PER_SIGMA
    t_shell = a / 6.0 + 1.0
    reach = a / 2.0 + t_shell + 4.0 * sigma + 4.0
    n = int(2 * np.ceil(reach)) + 1 + 2 * pad
    n += n % 2 == 0
    ax = np.arange(n, dtype=float) - n // 2
    x, y, z = np.meshgrid(ax, ax, ax, indexing="ij")
    r = np.sqrt(x * x + y * y + z * z)

    sphere = np.clip((a / 2.0 - r) + 0.5, 0.0, 1.0)
    g = np.exp(-(x * x + y * y + z * z) / (2.0 * sigma * sigma))
    g /= g.sum()

    def bl(o):
        return np.real(np.fft.ifftn(np.fft.fftn(o) * np.fft.fftn(g)))

    b_sphere = bl(sphere)
    if kind == "dc":
        return b_sphere
    if kind == "zero_mean":
        return b_sphere - b_sphere.mean()
    if kind == "annular":
        shell = ((r > a / 2.0 + 0.5) & (r <= a / 2.0 + 0.5 + t_shell)).astype(float)
        b_shell = bl(shell)
        return b_sphere - (sphere.sum() / max(shell.sum(), 1.0)) * b_shell
    raise ValueError(f"unknown template kind {kind!r}")


def _signal(a: float, n: int, fwhm: float) -> np.ndarray:
    """Unit-contrast sphere blurred by the PSF, sampled on an n^3 grid."""
    return psf.blur(psf.sphere_mass(n, a), psf.gaussian_kernel(n, fwhm))


def signal_energy(a: float, fwhm: float, n: int | None = None) -> float:
    """||blur(sphere)||^2 — the quantity the bound uses.

    Pass ``n`` to match the template's sampling grid exactly; the value is
    grid-independent once the grid comfortably contains the blur.
    """
    if n is None:
        sigma = fwhm / psf.FWHM_PER_SIGMA
        n = int(2 * np.ceil(a / 2.0 + 4.0 * sigma + 4.0)) + 1
        n += n % 2 == 0
    return float((_signal(a, n, fwhm) ** 2).sum())


def increment(t: np.ndarray, a: float, fwhm: float) -> float:
    """Statistic gain per unit of injected contrast (projection of signal on T)."""
    s = _signal(a, t.shape[0], fwhm)
    return float((t * s).sum())


def matched_filter(patch: np.ndarray, t: np.ndarray) -> float:
    return float((patch * t).sum())


def scanned_mf(volume: np.ndarray, t: np.ndarray) -> float:
    """Matched filter scanned over all positions; the maximum is the statistic."""
    t_hat = np.fft.fftn(t, s=volume.shape)
    return float(np.real(np.fft.ifftn(np.fft.fftn(volume) * t_hat)).max())


def peak(volume: np.ndarray) -> float:
    return float(volume.max())
