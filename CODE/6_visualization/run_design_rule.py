"""Design rule: the largest admissible voxel size for a target POD.

Computes Table 1 of the integrated manuscript from the bound alone: for a flaw of
diameter ``a`` and a contrast-to-noise ratio ``dI/sigma``, the largest voxel (or PSF
width) ``L`` for which the permitted detection probability at false-alarm rate
``alpha`` still reaches the target.  Also reports the repeat equivalence behind
Section 2.5 (a halving of the voxel is worth 64 scans below the voxel and 8 above).

No dataset is read: this is a derived table, generated from the same functions the
decision layer exposes, so the paper's design rule cannot drift from the code.

    python CODE/6_visualization/run_design_rule.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ammonitor import decision  # noqa: E402

FLAWS_UM = (50, 100, 200, 500)
CONTRASTS = (2, 5, 10)
POD_TARGET = 0.90
ALPHA = 0.01


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "results" / "design_rule.json"))
    args = ap.parse_args()

    table = {}
    for a in FLAWS_UM:
        row = {}
        for ratio in CONTRASTS:
            req = decision.requirement(a, float(ratio), 1.0,
                                       pod_target=POD_TARGET, alpha=ALPHA)
            row[f"dI_sigma_{ratio}"] = {
                "voxel_max_um": req.voxel_max,
                "energy_needed": req.energy_needed,
            }
        table[str(a)] = row

    payload = {
        "pod_target": POD_TARGET,
        "alpha": ALPHA,
        "single_look": True,
        "flaws_um": list(FLAWS_UM),
        "contrasts": list(CONTRASTS),
        "table": table,
        "repeat_equivalence": {
            "halving_voxel_below": decision.repeats_equivalence(2.0),
            "halving_voxel_above": 2.0 ** 3,
        },
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print("largest admissible voxel (um), POD>=0.90 at alpha=0.01")
    print("  a\\dI/sigma " + " ".join(f"{r:>8d}" for r in CONTRASTS))
    for a in FLAWS_UM:
        vals = [table[str(a)][f"dI_sigma_{r}"]["voxel_max_um"] for r in CONTRASTS]
        print(f"  {a:10d} " + " ".join(f"{v:8.1f}" for v in vals))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
