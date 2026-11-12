"""Recompute the per-subset five-fold accuracies quoted in Table 5.

Each EPFL subset contributes 500 frames per class; the descriptor and the
kNN/MLP ensemble are those of CODE/1_acoustic/run_eplf_v12.py.  The output is
results/subset_cv.json, the file behind the "Within-subset five-fold accuracy"
row of Table 5.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v12", ROOT / "CODE" / "1_acoustic" / "run_eplf_v12.py")
v12 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v12)

DATA = ROOT / "data" / "epfl_acoustic" / "Deciphering AE"


def main() -> int:
    out = {}
    for subset in ("D1", "D2", "D3", "D4"):
        raw = np.load(DATA / f"{subset}_rawspace_5000.npy", mmap_mode="r")
        lab = np.load(DATA / f"{subset}_classspace_5000.npy").astype(int)
        take = []
        for c in range(3):
            take.extend(np.where(lab == c)[0][:500].tolist())
        take = np.array(take)
        X = np.array([v12.extract_extended_features(np.asarray(raw[i], dtype=np.float64))
                      for i in take])
        y = lab[take]

        folds = [[] for _ in range(5)]
        for c in range(3):
            idx = np.where(y == c)[0]
            np.random.default_rng(42 + c).shuffle(idx)
            for k, i in enumerate(idx):
                folds[k % 5].append(i)

        accs = []
        for k in range(5):
            te = np.array(folds[k])
            tr = np.array([i for f in range(5) if f != k for i in folds[f]])
            mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-10
            knn = v12.WeightedKNN(k=9)
            knn.fit(X[tr], y[tr])
            mlp = v12.DeepMLP(input_dim=14, h1=64, h2=32, output_dim=3,
                              lr=0.02, l2=1e-4)
            mlp.fit((X[tr] - mu) / sd, y[tr], epochs=800)
            p = 0.5 * knn.predict_proba(X[te]) + 0.5 * mlp.predict_proba((X[te] - mu) / sd)
            accs.append(float(np.mean(p.argmax(1) == y[te])))
        out[subset] = {"folds": accs, "mean": float(np.mean(accs))}
        print(subset, "mean %.2f" % (100 * np.mean(accs)))

    path = ROOT / "results" / "subset_cv.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
