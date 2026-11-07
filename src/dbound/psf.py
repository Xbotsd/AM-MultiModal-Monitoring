"""Point spread function, flaw rendering, blurring and PSF estimation.

Lengths are in voxels unless stated otherwise.  The voxel edge is 1 and the point
spread function is a Gaussian whose full width at half maximum is ``L`` voxels.
The radius grid and the kernel are cached because the energy curve evaluates the
same geometry dozens of times.
"""

from __future__ import annotations

import numpy as np

FWHM_PER_SIGMA = 2.3548200450309493

_RADIUS: dict[int, np.ndarray] = {}
_KERNEL: dict[tuple[int, float], np.ndarray] = {}


def radius_grid(n: int) -> np.ndarray:
    if n not in _RADIUS:
        ax = np.arange(n, dtype=float) - n // 2
        x, y, z = np.meshgrid(ax, ax, ax, indexing="ij")
        _RADIUS[n] = np.sqrt(x * x + y * y + z * z)
    return _RADIUS[n]


def gaussian_kernel(n: int, fwhm: float) -> np.ndarray:
    key = (n, float(fwhm))
    if key not in _KERNEL:
        sigma = fwhm / FWHM_PER_SIGMA
        g = np.exp(-(radius_grid(n) ** 2) / (2.0 * sigma * sigma))
        _KERNEL[key] = g / g.sum()
    return _KERNEL[key]


def sphere(n: int, diameter: float, contrast: float = 1.0) -> np.ndarray:
    """Hard indicator of a centred sphere."""
    return contrast * (radius_grid(n) <= diameter / 2.0)


def sphere_soft(n: int, diameter: float, aa: float = 1.0) -> np.ndarray:
    """Anti-aliased indicator with a one-cell ramp (partial volume)."""
    return np.clip((diameter / 2.0 - radius_grid(n)) / aa + 0.5, 0.0, 1.0)


def sphere_mass(n: int, diameter: float) -> np.ndarray:
    """Anti-aliased sphere renormalised to the exact analytic volume."""
    obj = sphere_soft(n, diameter)
    target = (np.pi / 6.0) * diameter ** 3
    got = float(obj.sum())
    return obj * (target / got) if got > 0 else obj


def blur(obj: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    return np.real(np.fft.ifftn(np.fft.fftn(obj) * np.fft.fftn(kernel)))


def energy(obj: np.ndarray) -> float:
    """Squared L2 norm of a (blurred) image, sampled on the voxel grid."""
    return float((obj * obj).sum())


# --------------------------------------------------------------------------
# PSF estimation from data
# --------------------------------------------------------------------------

def psf_from_autocorrelation(vol: np.ndarray, mask: np.ndarray,
                             erode: int = 6) -> float:
    """PSF width in voxels, from the noise autocorrelation inside the material.

    The noise of a reconstructed volume is correlated over the reconstruction
    kernel, so the autocorrelation half-width *is* the detection PSF.  For a
    Gaussian kernel the autocorrelation is sqrt(2) wider than the kernel itself,
    which is the factor applied here.
    """
    from scipy import ndimage as ndi

    core = ndi.binary_erosion(mask, iterations=erode) if erode else mask
    if core.sum() < 5000:
        core = mask
    resid = np.where(core, vol - ndi.median_filter(vol, size=(1, 5, 5)), 0.0)
    f = np.fft.rfft(resid, axis=2)
    ac = np.fft.irfft(f * np.conj(f), n=vol.shape[2], axis=2).mean(axis=(0, 1))
    if ac[0] <= 0:
        return float("nan")
    ac = ac / ac[0]
    below = np.where(ac < 0.5)[0]
    if below.size == 0:
        return float("nan")
    i = int(below[0])
    if i == 0:
        w = 0.5
    else:
        a0, a1 = ac[i - 1], ac[i]
        w = (i - 1) + (a0 - 0.5) / (a0 - a1)
    return float(2.0 * w / np.sqrt(2.0))


def psf_from_edge(vol: np.ndarray, mask: np.ndarray, n_profiles: int = 60) -> float:
    """PSF width in voxels, from the edge spread function at the specimen edge.

    Independent of :func:`psf_from_autocorrelation`: the autocorrelation sees the
    noise correlation, this sees the geometric edge.  Agreement between the two
    is a check that neither is dominated by an artefact.
    """
    mid = vol.shape[0] // 2
    slab = vol[mid - 3:mid + 4].mean(axis=0) if vol.shape[0] >= 7 else vol[mid]
    lbl = mask[mid] if mask.ndim == 3 else mask
    cols = np.where(lbl.any(axis=0))[0]
    if cols.size < 20:
        return float("nan")
    left = cols[0]
    rows = np.where(lbl[:, left + 5])[0]
    if rows.size == 0:
        return float("nan")
    grid = np.arange(-15, 15, 0.25)
    profiles = []
    for r in rows[:: max(1, len(rows) // n_profiles)]:
        seg = slab[r][max(0, left - 25): left + 25]
        if seg.size < 30:
            continue
        lo, hi = np.percentile(seg, 5), np.percentile(seg, 95)
        if hi - lo < 5:
            continue
        norm = (seg - lo) / (hi - lo)
        idx = np.arange(seg.size)
        cross = np.interp(0.5, norm, idx)
        profiles.append(np.interp(cross + grid, idx, norm))
    if len(profiles) < 10:
        return float("nan")
    esf = np.mean(profiles, axis=0)
    w = float(np.interp(0.90, esf, grid) - np.interp(0.10, esf, grid))
    return 0.919 * w
