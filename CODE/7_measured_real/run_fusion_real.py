"""Real multi-source fusion on the ORNL Peregrine coupon table.

Data: Zenodo 10.5281/zenodo.23727492 (CC BY 4.0), per-coupon features and tensile
results derived from ORNL Peregrine v2023-11.  Place it at
``data/peregrine/peregrine_v2023-11_coupon_features.csv``.

Four feature blocks of the same specimen are treated as four co-registered
measurement channels and the destructive tensile test as the reference:

    camera c0, camera c1, DSCNN segmentation, machine telemetry

Two protocols are run: a random five-fold split and a five-fold split grouped by
build, so that no coupon is predicted from its own build.  Per channel a ridge
regression is fitted; the channel predictions are then combined by a simple
average, by inverse-variance weighting (the closed form of sequential Kalman
fusion), by covariance-aware generalised least squares, and by a bias-aware
stack.  The residual correlation matrix is reported because it, not the fuser,
is what limits the measured gain.

Reproduces Table 8 of the integrated manuscript (RMSE 38.20 single channel,
37.43 GLS, 36.03 stacking; 302.30 and 512.67 under the build-held-out split).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold, KFold

ROOT = Path(__file__).resolve().parents[2]
DATA = "data/peregrine/peregrine_v2023-11_coupon_features.csv"
DROP = {"t_absolute_image_capture_timestamp", "t_build_time"}
SEED = 42


def resolve(data_root: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/")
    if rel.startswith("data/"):
        rel = rel[len("data/"):]
    return Path(data_root) / rel


def block_matrix(df, ok, cols):
    A = df.loc[ok, cols].apply(pd.to_numeric, errors="coerce").values.astype(float)
    keep = np.isfinite(A).mean(0) > 0.5
    A = A[:, keep]
    # winsorise, then drop near-constant columns; median/IQR standardisation keeps
    # the per-channel scale out of the fusion weights
    lo = np.nanpercentile(A, 1, axis=0)
    hi = np.nanpercentile(A, 99, axis=0)
    A = np.clip(A, lo, hi)
    med = np.nanmedian(A, 0)
    A = np.where(np.isfinite(A), A, med[None, :])
    iqr = np.percentile(A, 75, 0) - np.percentile(A, 25, 0)
    good = iqr > 1e-9
    A = A[:, good]
    med = np.median(A, 0)
    sd = np.std(A, 0)
    sd = np.where(sd > 1e-12, sd, 1.0)
    return (A - med) / sd, int(keep.sum()), int(good.sum())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=str(ROOT / "data"),
                    help="directory that plays the role of data/ (default: <repo>/data)")
    ap.add_argument("--out", default=str(ROOT / "results" / "fusion_real.json"))
    args = ap.parse_args()

    path = resolve(Path(args.data_root), DATA)
    if not path.exists():
        raise SystemExit(f"missing input: {path}")

    df = pd.read_csv(path)
    blocks = {
        "camera c0": [c for c in df.columns if c.startswith("c0_")],
        "camera c1": [c for c in df.columns if c.startswith("c1_")],
        "DSCNN segmentation": [c for c in df.columns if c.startswith("seg_")],
        "machine telemetry": [c for c in df.columns if c.startswith("t_") and c not in DROP],
    }
    y = pd.to_numeric(df["ultimate_tensile_strength"], errors="coerce")
    ok = y.notna() & (y > 100) & (y < 2000)

    X, cols_used = {}, {}
    for name, cols in blocks.items():
        A, n1, n2 = block_matrix(df, ok, cols)
        X[name] = A
        cols_used[name] = {"columns": len(cols), "with_data": n1, "after_filter": n2}
    yv = y[ok].values
    groups = df.loc[ok, "build"].values
    meta = {"n_coupons": int(len(yv)), "n_builds": int(len(np.unique(groups))),
            "blocks": cols_used, "uts_mean": float(yv.mean()),
            "uts_sd": float(yv.std())}

    def analyse(tr, te):
        Ptr, Pte = {}, {}
        for name, A in X.items():
            m = RidgeCV(alphas=np.logspace(-2, 4, 25)).fit(A[tr], yv[tr])
            Ptr[name], Pte[name] = m.predict(A[tr]), m.predict(A[te])
        Ptr = np.stack(list(Ptr.values()), 1)
        Pte = np.stack(list(Pte.values()), 1)
        res_tr = Ptr - yv[tr][:, None]
        var = np.maximum((res_tr ** 2).mean(0), 1e-12)
        w = 1.0 / var
        w = w / w.sum()
        p_ivw = Pte @ w
        C = np.cov(res_tr.T)
        C = C + 1e-9 * np.eye(len(X)) * np.trace(C) / len(X)
        ones = np.ones(len(X))
        Ci = np.linalg.pinv(C)
        wg = Ci @ ones / (ones @ Ci @ ones)
        p_gls = Pte @ wg
        A = np.c_[Ptr, np.ones(len(Ptr))]
        coef = np.linalg.lstsq(A, yv[tr], rcond=None)[0]
        p_stack = np.c_[Pte, np.ones(len(Pte))] @ coef
        return {"single": {k: Pte[:, i] for i, k in enumerate(X)}, "Ptr": Ptr, "Pte": Pte,
                "avg": Pte.mean(1), "ivw": p_ivw, "gls": p_gls, "stack": p_stack,
                "w": w, "wg": wg, "res_corr": np.corrcoef(res_tr.T)}

    splits = {
        "grouped by build (5 folds)": list(GroupKFold(5).split(X["camera c0"], yv, groups)),
        "random 5-fold": list(KFold(5, shuffle=True, random_state=SEED).split(X["camera c0"])),
    }
    res = {"meta": meta, "splits": {}}
    for name, sp in splits.items():
        acc, corrs, ws = {}, [], []
        for tr, te in sp:
            d = analyse(tr, te)
            corrs.append(d["res_corr"])
            acc.setdefault("single", {})
            for k, p in d["single"].items():
                acc.setdefault(k, []).append((yv[te], p))
            for k, p in (("simple average", d["avg"]), ("inverse-variance / Kalman", d["ivw"]),
                         ("covariance-aware (GLS)", d["gls"]), ("bias-aware stacking", d["stack"])):
                acc.setdefault(k, []).append((yv[te], p))
            ws.append(d["w"])
        tab = {}
        for k, lst in acc.items():
            if k == "single":
                continue
            yt = np.concatenate([a for a, _ in lst])
            yp = np.concatenate([b for _, b in lst])
            tab[k] = {"rmse": float(np.sqrt(np.mean((yp - yt) ** 2))),
                      "mae": float(np.mean(np.abs(yp - yt))),
                      "r2": float(r2_score(yt, yp))}
        best = min((v["rmse"], k) for k, v in tab.items() if k in X)
        for k in ("simple average", "inverse-variance / Kalman",
                  "covariance-aware (GLS)", "bias-aware stacking"):
            tab[k]["reduction_vs_best_single"] = float(1 - tab[k]["rmse"] / best[0])
        tab["_best_single"] = {"model": best[1], "rmse": best[0]}
        rc = np.mean(corrs, 0)
        res["splits"][name] = {
            "table": tab,
            "mean_weights": {kk: float(np.mean([w[i] for w in ws])) for i, kk in enumerate(X)},
            "residual_correlation": {a: {b: float(rc[i, j]) for j, b in enumerate(X)}
                                     for i, a in enumerate(X)},
        }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    best = res["splits"]["random 5-fold"]["table"]
    print(f"coupons {meta['n_coupons']}, builds {meta['n_builds']}")
    for k in ("DSCNN segmentation", "covariance-aware (GLS)", "bias-aware stacking"):
        print(f"  {k:28s} RMSE {best[k]['rmse']:7.2f} MPa")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
