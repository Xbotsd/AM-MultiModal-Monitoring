"""Measured clutter inflation on the public X-ray CT stack.

Data: Zenodo 10.5281/zenodo.17602110 (CC BY 4.0), the AlSi10Mg tomographic stack
used for the porosity study.  Place the 212 DICOM slices of the primary volume at
``data/xct/vol_gd``.

The white-noise bound assumes that the noise a matched filter sees is the voxel
noise.  On a reconstruction it is not: the null statistic has a much larger
standard deviation because the metal carries structure at the scale of the
template.  This stage measures that inflation factor kappa on real material:
the voxel noise from the second-difference MAD, the point-spread width from the
noise autocorrelation, and kappa as the ratio of the matched-filter null standard
deviation on real metal to its white-noise value, with bootstrap intervals over
patches.  The decision layer (``src/dbound``) is what performs the measurement.

Reproduces Table 6 of the integrated manuscript: kappa about 24-31 below two
voxels, rising to 125 at a = 16 voxels, which is what turns the three-halves law
into an effective exponent near 0.3.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dbound import experiments  # noqa: E402

DATA = "data/xct/vol_gd"


def resolve(data_root: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/")
    if rel.startswith("data/"):
        rel = rel[len("data/"):]
    return Path(data_root) / rel


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=str(ROOT / "data"),
                    help="directory that plays the role of data/ (default: <repo>/data)")
    ap.add_argument("--out", default=str(ROOT / "results" / "xct_clutter.json"))
    ap.add_argument("--n-trials", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261108)
    args = ap.parse_args()

    folder = resolve(Path(args.data_root), DATA)
    if not folder.is_dir() or len(list(folder.glob("*.dcm"))) < 10:
        raise SystemExit(f"missing input: {folder} (212 DICOM slices expected)")

    res = experiments.measure_group(str(folder), n_trials=args.n_trials,
                                    seed=args.seed)
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"sigma {res['sigma']:.2f} grey levels, PSF {res['psf_fwhm_autocorr']:.2f} voxels")
    for k in res["kappa"]:
        print(f"  a={k['a']:4.1f}  x={k['x']:6.2f}  kappa={k['kappa']:6.1f} "
              f"[{k['kappa_lo']:.1f}, {k['kappa_hi']:.1f}]")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
