"""Loading and measuring the public XCT stack.

Everything here operates on real DICOM slices.  Three quantities are measured,
never assumed:

``sigma``   voxel noise, from the second difference inside the material;
``L``       PSF width, from the noise autocorrelation (and, as an independent
            check, from the edge spread function at the specimen boundary);
``kappa``   clutter inflation, the ratio of the matched-filter null standard
            deviation on real material to its white-noise value ``sigma*||T||``.

``kappa`` is the factor by which the white-noise bound is slack, so the operative
noise is ``sigma_eff = kappa * sigma``.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, asdict

import numpy as np
from scipy import ndimage as ndi

try:
    import pydicom
except ImportError as exc:  # pragma: no cover
    raise ImportError("pydicom is required for realdata") from exc

from . import detectors, psf


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

@dataclass
class Series:
    volume: np.ndarray
    pixel_spacing_mm: tuple[float, float]
    slice_spacing_mm: float
    n_slices: int
    rows: int
    cols: int
    first_file: str
    last_file: str

    @property
    def voxel_um(self) -> tuple[float, float, float]:
        return (self.pixel_spacing_mm[0] * 1000.0,
                self.pixel_spacing_mm[1] * 1000.0,
                self.slice_spacing_mm * 1000.0)

    def meta(self) -> dict:
        d = asdict(self)
        d.pop("volume")
        d["voxel_um"] = self.voxel_um
        return d


def load_series(folder: str | pathlib.Path) -> Series:
    folder = pathlib.Path(folder)
    files = sorted(folder.glob("*.dcm"))
    if not files:
        raise FileNotFoundError(f"no DICOM files in {folder}")
    slices = [pydicom.dcmread(str(f)) for f in files]
    if all(getattr(d, "InstanceNumber", None) is not None for d in slices):
        slices.sort(key=lambda d: int(d.InstanceNumber))
    ds0 = slices[0]
    slope = float(getattr(ds0, "RescaleSlope", 1.0))
    inter = float(getattr(ds0, "RescaleIntercept", 0.0))
    vol = np.stack([s.pixel_array.astype(np.float32) * slope + inter
                    for s in slices])
    px = getattr(ds0, "PixelSpacing", [1.0, 1.0])
    dz = getattr(ds0, "SliceThickness", None)
    if dz is None:
        zs = [float(d.ImagePositionPatient[2]) for d in slices
              if getattr(d, "ImagePositionPatient", None) is not None]
        dz = float(np.median(np.diff(zs))) if len(zs) > 1 else float(px[0])
    return Series(vol, (float(px[0]), float(px[1])), float(dz), len(slices),
                  int(vol.shape[1]), int(vol.shape[2]),
                  files[0].name, files[-1].name)


def sha256_file(path: str | pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(folder: str | pathlib.Path) -> list[dict]:
    """Per-slice size and SHA-256, so the exact data used can be verified."""
    out = []
    for f in sorted(pathlib.Path(folder).glob("*.dcm")):
        out.append({"name": f.name, "bytes": f.stat().st_size,
                    "sha256": sha256_file(f)})
    return out


def write_manifest(folder: str | pathlib.Path, dest: str | pathlib.Path) -> None:
    pathlib.Path(dest).write_text(
        json.dumps({"folder": str(folder), "files": manifest(folder)}, indent=1),
        encoding="utf-8")


# --------------------------------------------------------------------------
# masks and noise
# --------------------------------------------------------------------------

def otsu(img: np.ndarray, bins: int = 256) -> float:
    hist, edges = np.histogram(img, bins=bins)
    centres = 0.5 * (edges[1:] + edges[:-1])
    w = np.cumsum(hist).astype(float)
    w /= w[-1]
    mu = np.cumsum(hist * centres)
    with np.errstate(invalid="ignore", divide="ignore"):
        var_b = (mu[-1] * w - mu) ** 2 / (w * (1 - w))
    return float(centres[int(np.nanargmax(var_b))])


def material_mask(vol: np.ndarray, thr: float | None = None) -> np.ndarray:
    if thr is None:
        thr = otsu(vol[vol.shape[0] // 2])
    mask = vol > thr
    lab, n = ndi.label(mask)
    if n > 1:
        sizes = ndi.sum(mask, lab, range(1, n + 1))
        mask = lab == (int(np.argmax(sizes)) + 1)
    return mask


def sigma_second_diff(vol: np.ndarray, mask: np.ndarray) -> float:
    """Robust noise: 1.4826 * MAD of the along-column second difference.

    Differencing cancels the smooth structure and the MAD ignores the residual
    pores; a plain standard deviation inside the material returns the
    microstructure, not the noise.
    """
    core = ndi.binary_erosion(mask, iterations=3)
    if core.sum() < 1000:
        core = mask
    d = np.diff(vol, axis=2)
    m = core[:, :, 1:] & core[:, :, :-1]
    vals = d[m]
    if vals.size < 100:
        return float("nan")
    mad = np.median(np.abs(vals - np.median(vals)))
    return float(1.4826 * mad / np.sqrt(2.0))


def sigma_plain_std(vol: np.ndarray, mask: np.ndarray) -> float:
    """Naive alternative: standard deviation inside the eroded material."""
    core = ndi.binary_erosion(mask, iterations=3)
    if core.sum() < 1000:
        core = mask
    return float(vol[core].std())


def sigma_percentile(vol: np.ndarray, mask: np.ndarray, q: float = 0.99) -> float:
    """Alternative: (q-th percentile - median) / z_q, assuming a Gaussian tail."""
    core = ndi.binary_erosion(mask, iterations=3)
    if core.sum() < 1000:
        core = mask
    v = vol[core]
    from .bound import z_from_p
    return float((np.percentile(v, q * 100) - np.median(v)) / z_from_p(q))


# --------------------------------------------------------------------------
# patch sampling and clutter inflation
# --------------------------------------------------------------------------

def patch_at(vol: np.ndarray, centre: tuple[int, int, int], n: int):
    half = n // 2
    for c, size in zip(centre, vol.shape):
        if c - half < 0 or c - half + n > size:
            return None
    i, j, k = centre
    return vol[i - half:i - half + n, j - half:j - half + n,
               k - half:k - half + n]


def sample_centres(mask: np.ndarray, n_patch: int, n_want: int,
                   rng: np.random.Generator, erode: int | None = None,
                   interior: np.ndarray | None = None):
    if interior is None:
        er = n_patch // 2 + 2 if erode is None else erode
        interior = ndi.binary_erosion(mask, iterations=er)
        if interior.sum() < n_want:
            interior = ndi.binary_erosion(mask, iterations=max(2, er // 3))
    pts = np.argwhere(interior)
    if len(pts) == 0:
        return []
    idx = rng.choice(len(pts), size=min(len(pts), n_want * 6), replace=False)
    return [tuple(map(int, pts[i])) for i in idx]


def kappa(vol: np.ndarray, mask: np.ndarray, sigma: float, a: float,
          fwhm: float, kind: str = "annular", n_trials: int = 400,
          alpha: float = 0.01, pad: int = 0,
          rng: np.random.Generator | None = None,
          interior: np.ndarray | None = None) -> dict:
    """Clutter inflation of the matched-filter null on real material."""
    rng = rng or np.random.default_rng(7)
    t = detectors.template(a, fwhm, kind=kind, pad=pad)
    n = t.shape[0]
    centres = sample_centres(mask, n, n_trials, rng, interior=interior)
    stats = []
    for c in centres:
        p = patch_at(vol, c, n)
        if p is None:
            continue
        stats.append(detectors.matched_filter(p, t))
        if len(stats) >= n_trials:
            break
    stats = np.asarray(stats, dtype=float)
    if stats.size < 50:
        return {"a": a, "kind": kind, "n": int(stats.size), "kappa": float("nan")}
    e_sig = detectors.signal_energy(a, fwhm, n=n)
    inc = detectors.increment(t, a, fwhm)
    sd = float(stats.std())
    bs = rng.choice(stats, size=(400, stats.size), replace=True).std(axis=1)
    denom = sigma * np.sqrt(e_sig)
    return {
        "a": float(a), "x": float(a / fwhm), "kind": kind, "pad": pad,
        "n": int(stats.size), "sigma": float(sigma), "fwhm": float(fwhm),
        "sqrt_E": float(np.sqrt(e_sig)), "increment": float(inc),
        "kappa": float(sd / denom), "kappa_lo": float(np.percentile(bs, 2.5) / denom),
        "kappa_hi": float(np.percentile(bs, 97.5) / denom),
        "threshold": float(np.quantile(stats, 1.0 - alpha)),
        "mean_stat": float(stats.mean()), "sd_stat": sd,
    }


def pod_curve_real(vol: np.ndarray, mask: np.ndarray, sigma: float, a: float,
                   fwhm: float, ratios=(1.0, 2.0, 4.0, 8.0, 16.0, 54.0),
                   kind: str = "annular", n_trials: int = 400,
                   alpha: float = 0.01, rng=None) -> list[dict]:
    """Measured POD versus the bound, sweeping contrast at fixed geometry."""
    rng = rng or np.random.default_rng(7)
    k = kappa(vol, mask, sigma, a, fwhm, kind=kind, n_trials=n_trials,
              alpha=alpha, rng=rng)
    if not np.isfinite(k.get("kappa", float("nan"))):
        return []
    t = detectors.template(a, fwhm, kind=kind)
    n = t.shape[0]
    centres = sample_centres(mask, n, n_trials, rng)
    stats = []
    for c in centres:
        p = patch_at(vol, c, n)
        if p is None:
            continue
        stats.append(detectors.matched_filter(p, t))
        if len(stats) >= n_trials:
            break
    stats = np.asarray(stats, dtype=float)
    thr = float(np.quantile(stats, 1.0 - alpha))
    from . import bound as bd
    rows = []
    for ratio in ratios:
        s1 = stats + ratio * sigma * k["increment"]
        d_bound = ratio * k["sqrt_E"]
        rows.append({
            "a": float(a), "x": float(a / fwhm), "dI_over_sigma": float(ratio),
            "d_bound": float(d_bound),
            "pod_bound": float(bd.ndtr(d_bound - bd.z_from_p(1.0 - alpha))),
            "pod_meas": float((s1 > thr).mean()),
            "kappa": k["kappa"],
        })
    return rows
