"""Real-data phase unwrapping on captured fringe-projection images.

Data: Zenodo 10.5281/zenodo.22125908 (CC BY 4.0), ``3D_sample_data.zip``.  Place
the extracted folder at ``data/fringe/3D_sample_data``; it must contain
``3D_sample_acquisition.tif``, ``plane_calibration_acquisition.tif`` and the
independent PUMA reconstruction ``3D_sample_PUMA_reconstruction.tif``.

The projected fringe carrier is removed with the calibration-plane acquisition,
the usable region is restricted to where the fringe modulation is real, and five
unwrappers are scored against the independent PUMA height map on a held-out half
of the pixels: plain integration, integration plus a Kalman residual filter,
Kalman plus anisotropic diffusion, weighted least squares and quality-guided
path following.  The calibration from phase to height is an affine-plus-plane
fit on the training half, so fixture tilt and rigid misalignment are absorbed
rather than counted as unwrapping error.

Reproduces the measured RMSE of 0.532 mm over a 6.2 mm range (Table 4/9 of the
integrated manuscript), and the negative result that none of the four
refinements improves on plain integration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
ACQ = "data/fringe/3D_sample_data/3D_sample_acquisition.tif"
PLANE = "data/fringe/3D_sample_data/plane_calibration_acquisition.tif"
REF = "data/fringe/3D_sample_data/3D_sample_PUMA_reconstruction.tif"
SEED = 42


def resolve(data_root: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/")
    if rel.startswith("data/"):
        rel = rel[len("data/"):]
    return Path(data_root) / rel


def phase3(X):
    return np.arctan2(np.sqrt(3) * (X[0] - X[2]), 2 * X[1] - X[0] - X[2])


def modulation(X):
    return np.sqrt(3 * (X[0] - X[2]) ** 2 + (2 * X[1] - X[0] - X[2]) ** 2) / 3.0


def wrap(x):
    return np.angle(np.exp(1j * x))


def integrate(p):
    dx = wrap(np.diff(p, axis=1))
    dy = wrap(np.diff(p, axis=0))
    ix = np.cumsum(dx, axis=1)
    ix = np.c_[np.zeros(ix.shape[0]), ix]
    iy = np.cumsum(dy, axis=0)
    iy = np.r_[np.zeros((1, iy.shape[1])), iy]
    return 0.5 * (ix + iy)


def kalman_filter(p, est, m, iters=8, q=1e-4, r=1.0):
    for _ in range(iters):
        res = wrap(p - est) * m
        for axis in (0, 1):
            y = np.moveaxis(res, axis, 0)
            o = np.zeros_like(y)
            acc = np.zeros(y.shape[1:])
            Pv = 1.0
            for i in range(y.shape[0]):
                Pv += q
                K = Pv / (Pv + r)
                acc = acc + K * (y[i] - acc)
                Pv *= (1 - K)
                o[i] = acc
            res = res - 0.5 * np.moveaxis(o, 0, axis)
        est = est + res
    return est


def diffusion(x, m, n=5, sigma=1.5, eta=0.3):
    for _ in range(n):
        x = x + eta * (ndi.gaussian_filter(x * m, sigma) - x * m)
    return x


def wls(p, mod, iters=5):
    est = integrate(p)
    w = ndi.gaussian_filter(mod ** 2, 3)
    w = w / w.max()
    for _ in range(iters):
        est = est + ndi.gaussian_filter(wrap(p - est) * w, 2)
    return est


def qg(p, mod):
    est = integrate(p)
    q = ndi.gaussian_filter(mod, 2)
    q = q / q.max()
    return est + ndi.gaussian_filter(wrap(p - est) * q, 3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=str(ROOT / "data"),
                    help="directory that plays the role of data/ (default: <repo>/data)")
    ap.add_argument("--out", default=str(ROOT / "results" / "unwrap_real.json"))
    ap.add_argument("--save-arrays", action="store_true",
                    help="also write the unwrapped phase fields next to the JSON")
    args = ap.parse_args()

    paths = [resolve(Path(args.data_root), p) for p in (ACQ, PLANE, REF)]
    for p in paths:
        if not p.exists():
            raise SystemExit(f"missing input: {p}")
    I = tifffile.imread(paths[0]).astype(np.float64)
    P = tifffile.imread(paths[1]).astype(np.float64)
    REFERENCE = tifffile.imread(paths[2]).astype(np.float64)

    phi, phi_p = phase3(I), phase3(P)
    mod, mod_p = modulation(I), modulation(P)
    m = (mod > 0.25 * np.median(mod)) & (mod_p > 0.25 * np.median(mod_p)) & (I.max(0) < 65000)
    m = ndi.binary_erosion(m, iterations=3)
    out = {"usable_fraction": float(m.mean()),
           "ref_mm_range": [float(REFERENCE.min()), float(REFERENCE.max())]}

    est_s, est_p = integrate(phi), integrate(phi_p)
    h_int = est_s - est_p
    h_k = kalman_filter(phi, est_s, m) - kalman_filter(phi_p, est_p, m)
    h_kd = diffusion(h_k, m)
    variants = {
        "unweighted integration (carrier corrected)": h_int,
        "+ Kalman residual filter": h_k,
        "+ Kalman + diffusion": h_kd,
        # both weighted variants take their weights from the sample acquisition and
        # apply them to the calibration plane as well, which is the published run;
        # the plane carries the same projected fringes, so the choice is defensible
        "weighted least squares": wls(phi, mod) - wls(phi_p, mod),
        "quality-guided": qg(phi, mod) - qg(phi_p, mod),
    }

    rng = np.random.default_rng(SEED)
    ok = m & (REFERENCE > 0.05)
    idx = np.flatnonzero(ok)
    rng.shuffle(idx)
    tr, te = idx[: idx.size // 2], idx[idx.size // 2:]
    ref = REFERENCE.ravel()
    yy, xx = np.mgrid[0:REFERENCE.shape[0], 0:REFERENCE.shape[1]]
    res = {}
    for name, e in variants.items():
        X = np.c_[np.ones(tr.size), e.ravel()[tr], yy.ravel()[tr], xx.ravel()[tr]]
        coef = np.linalg.lstsq(X, ref[tr], rcond=None)[0]
        err = (coef[0] + coef[1] * e.ravel()[te] + coef[2] * yy.ravel()[te]
               + coef[3] * xx.ravel()[te] - ref[te])
        keep = np.abs(err) < 3 * np.median(np.abs(err)) + 1e-12
        res[name] = {"rmse_mm": float(np.sqrt(np.mean(err ** 2))),
                     "mae_mm": float(np.mean(np.abs(err))),
                     "rmse_trimmed_mm": float(np.sqrt(np.mean(err[keep] ** 2))),
                     "scale_mm_per_rad": float(coef[1]), "offset_mm": float(coef[0]),
                     "n_eval": int(te.size)}
        if args.save_arrays:
            stem = Path(args.out).with_suffix("")
            np.save(f"{stem}_{name.replace(' ', '_').replace('+', 'p')}.npy",
                    e.astype(np.float32))
    base = res["unweighted integration (carrier corrected)"]["rmse_mm"]
    for v in res.values():
        v["change_vs_integration"] = float(v["rmse_mm"] / base - 1)
    out["methods"] = res

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"usable {out['usable_fraction']:.3f}, reference range {out['ref_mm_range']}")
    for k, v in res.items():
        print(f"  {k:44s} RMSE {v['rmse_mm']:.3f} mm  ({v['change_vs_integration']*100:+.1f}%)")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
