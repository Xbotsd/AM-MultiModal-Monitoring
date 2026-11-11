"""Measured clutter inflation and detector comparison on the public CT stack.

Data: Zenodo 10.5281/zenodo.17602110 (CC BY 4.0), the AlSi10Mg tomographic stack
used for the porosity study.  Place the 212 DICOM slices of the primary volume at
``data/xct/vol_gd``; two further reconstructions of the same material
(``data/xct/vol_g1``, ``data/xct/vol_g2``, 120 slices each) are optional and are
used for the cross-reconstruction comparison when present.

The white-noise bound assumes that the noise a matched filter sees is the voxel
noise.  On a reconstruction it is not: the null statistic has a much larger
standard deviation because the metal carries structure at the scale of the
template.  This stage measures, on real material and never assuming:

* kappa, the ratio of the matched-filter null standard deviation to its white-noise
  value, with bootstrap intervals over patches (Table 6);
* the same kappa on two other reconstructions of the material, which decides
  whether kappa belongs to the material or to the scan (Table 7);
* the ablation behind the estimator choices -- three template constructions, three
  noise estimators, two support paddings and three false-alarm rates (Fig. 6b,c);
* the POD of the oracle matched filter, the searched filter and a template-free peak
  detector at a matched false-alarm rate, against the white-noise bound (Fig. 6a).

The decision layer (``src/dbound``) performs the measurement; this stage only
supplies the data, the seeds and the result file.  Reproduces Table 6 (kappa 31.2
at one voxel falling to 24.4 at two and rising to 125.2 at sixteen), Table 7 and
the real-metal PODs of Section 4.5 (0.530 / 0.117 / 0.023 at a = 4 voxels).
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
    ap.add_argument("--skip-cross-group", action="store_true")
    ap.add_argument("--skip-ablation", action="store_true")
    ap.add_argument("--skip-comparison", action="store_true")
    args = ap.parse_args()

    folder = resolve(Path(args.data_root), DATA)
    if not folder.is_dir() or len(list(folder.glob("*.dcm"))) < 10:
        raise SystemExit(f"missing input: {folder} (212 DICOM slices expected)")

    out = {"primary": experiments.measure_group(
        str(folder), n_trials=args.n_trials, seed=args.seed)}

    # optional reconstructions of the same material, built from the data root so
    # that they are not declared as required inputs of the stage
    groups = {"vol_gd": folder}
    for name in ("vol_g1", "vol_g2"):
        f = Path(args.data_root) / "xct" / name
        if f.is_dir() and len(list(f.glob("*.dcm"))) > 10:
            groups[name] = f
    if len(groups) > 1 and not args.skip_cross_group:
        out["cross_group"] = experiments.cross_group(
            {k: str(v) for k, v in groups.items()}, n_trials=300, seed=args.seed)
    else:
        out["cross_group"] = None

    out["ablation"] = (None if args.skip_ablation
                       else experiments.ablate(str(folder), a=8.0, n_trials=300))
    out["comparison"] = (None if args.skip_comparison
                         else experiments.compare_detectors(str(folder), a=4.0,
                                                            ratio=8.0, n_trials=300))

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    p = out["primary"]
    print(f"sigma {p['sigma']:.2f} grey levels, PSF {p['psf_fwhm_autocorr']:.2f} voxels")
    for k in p["kappa"]:
        print(f"  a={k['a']:4.1f}  x={k['x']:6.2f}  kappa={k['kappa']:6.1f} "
              f"[{k['kappa_lo']:.1f}, {k['kappa_hi']:.1f}]")
    if out["cross_group"]:
        print("cross-group:", ", ".join(out["cross_group"]))
    if out["ablation"]:
        print("ablation kappa:", {k: round(v["kappa"], 1)
                                  for k, v in out["ablation"]["templates"].items()})
    if out["comparison"]:
        print("POD:", {k: round(v, 3) for k, v in out["comparison"]["pod"].items()})
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
