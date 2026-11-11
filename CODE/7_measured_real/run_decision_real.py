"""Graded decision rule replayed on measured coupon data.

Data: ORNL Peregrine coupon table, Zenodo 10.5281/zenodo.23727492 (CC BY 4.0).
Place it at ``data/peregrine/peregrine_v2023-11_coupon_features.csv``.  The DSCNN
segmentation columns give, per coupon, the fraction of each anomaly class and the
layer-summed and layer-max indicators; the destructive tensile test gives the
truth.

The four-level grading (record / mark / adjust / pause) is mapped from the total
anomalous area fraction to a build-relative weak-coupon label (lower quartile of
ultimate tensile strength within the build).  What this can test is whether the
grading separates coupons that turned out weak; what it cannot test is what a
parameter change would have done, because no public dataset contains the
counterfactual.

Reproduces the measured graded-decision row of Table 4/9: AUC 0.751 overall,
0.54-0.93 per build, weak-coupon enrichment 2.25 in the pause band.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
DATA = "data/peregrine/peregrine_v2023-11_coupon_features.csv"


def resolve(data_root: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/")
    if rel.startswith("data/"):
        rel = rel[len("data/"):]
    return Path(data_root) / rel


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=str(ROOT / "data"),
                    help="directory that plays the role of data/ (default: <repo>/data)")
    ap.add_argument("--out", default=str(ROOT / "results" / "decision_real.json"))
    args = ap.parse_args()

    path = resolve(Path(args.data_root), DATA)
    if not path.exists():
        raise SystemExit(f"missing input: {path}")

    df = pd.read_csv(path)
    num = lambda c: pd.to_numeric(df[c], errors="coerce")
    uts = num("ultimate_tensile_strength")
    ok = uts.notna() & (uts > 100) & (uts < 2000)
    anom = [c for c in df.columns
            if c.startswith("seg_s_") and c not in ("seg_s_powder", "seg_s_printed")]
    A = df.loc[ok, anom].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = uts[ok].values

    # weakness label: lower quartile of UTS within the build, so no build bias
    grp = df.loc[ok, "build"]
    q25 = y.astype(float).copy()
    for _, idx in grp.groupby(grp).groups.items():
        ii = df.loc[ok].index.get_indexer(idx)
        q25[ii] = np.quantile(y[ii], 0.25) if ii.size > 20 else np.quantile(y, 0.25)
    weak = (y <= q25).astype(int)
    score = A.sum(axis=1).values
    meta = {"n_coupons": int(ok.sum()), "n_weak": int(weak.sum()),
            "n_anomaly_columns": len(anom),
            "uts_quartile_25": float(np.quantile(y, 0.25)),
            "uts_median": float(np.median(y))}

    th = np.quantile(score, [0.30, 0.50, 0.80])
    level = np.digitize(score, th)
    res = {
        "meta": meta,
        "thresholds": [float(t) for t in th],
        "level_counts": {int(k): int((level == k).sum()) for k in range(4)},
        "weak_rate_by_level": {int(k): float(weak[level == k].mean())
                               for k in range(4) if (level == k).sum()},
        "auc_score_vs_weak": float(roc_auc_score(weak, score)),
        "median_uts_by_level": {int(k): float(np.median(y[level == k]))
                                for k in range(4) if (level == k).sum()},
    }
    sev = level == 3
    res["pause_band"] = {
        "n": int(sev.sum()), "weak_rate": float(weak[sev].mean()),
        "weak_rate_base": float(weak.mean()),
        "enrichment": float(weak[sev].mean() / weak.mean()) if weak.mean() > 0 else None,
    }
    per = {}
    for b in grp.unique():
        ii = df.loc[ok].index.get_indexer(grp[grp == b].index)
        if ii.size < 100:
            continue
        s, w = score[ii], weak[ii]
        per[str(b)] = {
            "n": int(ii.size),
            "auc": float(roc_auc_score(w, s)) if len(np.unique(w)) > 1 else None,
            "severe_fraction": float((s >= th[2]).mean()),
            "weak_rate": float(w.mean()),
        }
    res["per_build"] = per
    res["weak_rate_trend"] = [res["weak_rate_by_level"].get(k) for k in range(4)]

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"coupons {meta['n_coupons']}, weak {meta['n_weak']}, AUC "
          f"{res['auc_score_vs_weak']:.3f}, enrichment "
          f"{res['pause_band']['enrichment']:.2f}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
