"""Measured surface-height maps through the geometric monitoring chain.

Data: Zenodo 10.5281/zenodo.21285367 (CC BY 4.0), ``height_maps.zip`` from the NSF
Future Manufacturing Data Challenge: white-light interferometry of real SS316L
directed-energy-deposition single tracks, 480 x ~20 000 px at 3.982 um.  Place the
four ``.ASC`` maps at ``data/hm/Heightmap_{8,10,14,21}.ASC``.

The chain is the one described for the geometric module: the nominal track
cross-section (the column-wise median, since the section is constant along the
scan) is removed, the residual is summarised robustly, a quiet stripe of the same
scan supplies the noise floor, and a 0.25 mm sliding window is thresholded at 10
and 20 um.  No public in-situ LPBF height map carries defect labels, so nothing is
scored against a labelled truth; what is reported is the operating point of the
chain -- robust deviation 2.9-5.0 um, 37-56 % of pixels flagged invalid by the
instrument on the steep flanks, and no 0.25 mm window above 10 um.

Reproduces the measured-track rows of Table 4/9 of the integrated manuscript.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("Heightmap_8", "Heightmap_14", "Heightmap_10", "Heightmap_21")
PIXEL_UM = 3.982
WINDOW_PX = 64
THRESHOLDS_MM = (0.010, 0.020)


def resolve(data_root: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/")
    if rel.startswith("data/"):
        rel = rel[len("data/"):]
    return Path(data_root) / rel


def read_asc(path: Path):
    nx = ny = px = skip = None
    with open(path, "r", errors="ignore") as f:
        for i, line in enumerate(f):
            if line.startswith("X Size"):
                nx = int(line.split()[-1])
            elif line.startswith("Y Size"):
                ny = int(line.split()[-1])
            elif line.startswith("Pixel_size"):
                px = float(line.split()[-1])
            elif line.startswith("RAW_DATA"):
                skip = i + 1
                break
    d = pd.read_csv(path, sep=r"\s+", skiprows=skip, header=None,
                    names=["x", "y", "z"], usecols=[0, 1, 2], na_values=["Bad"],
                    dtype={0: np.float64, 1: np.float64})
    z = d["z"].to_numpy(dtype=np.float64)
    return np.asarray(z[: nx * ny]).reshape(ny, nx), px


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=str(ROOT / "data"),
                    help="directory that plays the role of data/ (default: <repo>/data)")
    ap.add_argument("--out", default=str(ROOT / "results" / "pointcloud_real.json"))
    ap.add_argument("--save-arrays", action="store_true",
                    help="also write the residual fields next to the JSON")
    args = ap.parse_args()

    out = {}
    for name in NAMES:
        path = resolve(Path(args.data_root), f"data/hm/{name}.ASC")
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
        z, px = read_asc(path)
        bad = ~np.isfinite(z) | (z > 1e6) | (z < -1e6)
        zz = np.where(bad, np.nan, z) / 1e6          # instrument Z is in nm
        prof = np.nanmedian(zz, axis=1)              # nominal track cross-section
        r = zz - prof[:, None]
        r = r - np.nanmedian(r)
        m = np.isfinite(r)
        sd = 1.4826 * np.nanmedian(np.abs(r[m] - np.nanmedian(r[m])))
        rough = ndi.uniform_filter(np.abs(np.nan_to_num(r)), size=(1, 64))
        colr = np.nanmean(rough, 0)
        quiet = np.argsort(colr)[: max(50, colr.size // 10)]
        sig_q = float(1.4826 * np.nanmedian(np.abs(r[:, quiet])))
        mean_r = ndi.uniform_filter(np.nan_to_num(r), size=WINDOW_PX)
        for thr_mm in THRESHOLDS_MM:
            det = np.abs(mean_r) > thr_mm
            lab, n = ndi.label(det)
            sizes = ndi.sum(det, lab, range(1, n + 1)) if n else np.array([])
            out[f"{name}__thr{int(thr_mm * 1000)}um"] = {
                "threshold_mm": thr_mm,
                "covered_fraction": float(det.mean()),
                "regions": int((sizes > 20).sum()) if n else 0,
                "largest_region_px": int(sizes.max()) if sizes.size else 0,
            }
        out[name] = {
            "shape": list(z.shape), "pixel_um": float(px * 1000) if px else PIXEL_UM,
            "invalid_fraction": float(bad.mean()),
            "detrend": "column-wise median (nominal track cross-section)",
            "residual_sd_mm": float(sd), "quiet_stripe_sd_mm": sig_q,
            "nn_ratio": float(sd / sig_q) if sig_q > 0 else None,
            "window_px": WINDOW_PX,
            "residual_p99_mm": float(np.nanpercentile(np.abs(r), 99)),
        }
        if args.save_arrays:
            stem = Path(args.out).with_suffix("")
            np.save(f"{stem}_{name}_resid.npy", r.astype(np.float32))
        print(f"  {name}: invalid {bad.mean()*100:.1f}%, robust sd {sd*1000:.2f} um, "
              f"p99 {out[name]['residual_p99_mm']*1000:.1f} um")

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
