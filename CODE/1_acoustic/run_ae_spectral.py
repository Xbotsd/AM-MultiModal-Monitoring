"""Acoustic log-spectrum bound and five-fold cross-validation on the EPFL set.

Data: EPFL LPBF acoustic corpus, Zenodo 10.5281/zenodo.10449883 (CC BY 4.0).
Place ``D1_rawspace_5000.npy`` and ``D1_classspace_5000.npy`` under
``data/epfl_acoustic/Deciphering AE``.

A template detector on class-mean waveforms is limited by the mean's own
estimation noise, so the quantity that actually bounds the acoustic channel is
the second-order deflection: the Mahalanobis distance between class log-spectra
under the pooled covariance, i.e. the Gaussian deflection of a 64-band
log-spectrum statistic.  This stage computes that distance on held-out folds, the
accuracy it implies, and the five-fold accuracy of the linear (LDA) classifier
built on the same 64 bands.

Reproduces the log-spectrum row of Table 4 and the second-order row of Table 5:
88.9 % +/- 0.3 % cross-validated accuracy, pairwise deflections 2.83, 3.02 and
3.12 at 64 bands, against 82.2 % for the 14-descriptor ensemble.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW = "data/epfl_acoustic/Deciphering AE/D1_rawspace_5000.npy"
LAB = "data/epfl_acoustic/Deciphering AE/D1_classspace_5000.npy"
SEED = 42
FRAMES_PER_CLASS = 800
BANDS = (8, 16, 32, 64, 128, 256)


def resolve(data_root: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/")
    if rel.startswith("data/"):
        rel = rel[len("data/"):]
    return Path(data_root) / rel


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=str(ROOT / "data"),
                    help="directory that plays the role of data/ (default: <repo>/data)")
    ap.add_argument("--out", default=str(ROOT / "results" / "ae_spectral.json"))
    args = ap.parse_args()

    raw_path = resolve(Path(args.data_root), RAW)
    lab_path = resolve(Path(args.data_root), LAB)
    for p in (raw_path, lab_path):
        if not p.exists():
            raise SystemExit(f"missing input: {p}")

    raw = np.load(raw_path, mmap_mode="r")
    lab = np.asarray(np.load(lab_path, mmap_mode="r")).ravel()
    rng = np.random.default_rng(SEED)
    classes = [0, 1, 2]
    idx = {c: np.sort(rng.choice(np.flatnonzero(lab == c), FRAMES_PER_CLASS,
                                 replace=False)) for c in classes}
    X = np.concatenate([np.asarray(raw[idx[c]], float) for c in classes])
    y = np.repeat(classes, FRAMES_PER_CLASS)

    power = np.abs(np.fft.rfft(X - X.mean(1, keepdims=True), axis=1)) ** 2

    def logbands(nb):
        edges = np.linspace(1, power.shape[1], nb + 1).astype(int)
        return np.log(np.stack([power[:, edges[i]:edges[i + 1]].sum(1)
                                for i in range(nb)], 1))

    folds = np.zeros(len(y), int)
    for c in classes:
        ii = np.flatnonzero(y == c)
        rng.shuffle(ii)
        folds[ii] = np.arange(ii.size) % 5

    out = {}
    for nb in BANDS:
        F = logbands(nb)
        accs, dps = [], []
        for f in range(5):
            tr, te = folds != f, folds == f
            mu = np.stack([F[tr & (y == c)].mean(0) for c in classes])
            Sw = sum(np.cov(F[tr & (y == c)].T) for c in classes) / 3
            Si = np.linalg.inv(Sw + 1e-6 * np.trace(Sw) / nb * np.eye(nb))
            Dd = F[te][:, None, :] - mu[None]
            pred = np.einsum("nki,ij,nkj->nk", Dd, Si, Dd).argmin(1)
            accs.append((pred == y[te]).mean())
            pw = []
            for i in range(3):
                for j in range(i + 1, 3):
                    w = Si @ (mu[i] - mu[j])
                    a = F[te & (y == i)] @ w
                    b = F[te & (y == j)] @ w
                    pw.append((a.mean() - b.mean()) / np.sqrt(0.5 * (a.var() + b.var())))
            dps.append(pw)
        dps = np.array(dps)
        out[nb] = {
            "cv_acc_mean": float(np.mean(accs)),
            "cv_acc_sd": float(np.std(accs, ddof=1)),
            "pairwise_dprime_heldout_mean": [float(x) for x in dps.mean(0)],
            "pairwise_dprime_heldout_sd": [float(x) for x in dps.std(0, ddof=1)],
        }

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    b64 = out[64]
    print(f"64 bands: CV accuracy {b64['cv_acc_mean']*100:.2f} % "
          f"+/- {b64['cv_acc_sd']*100:.2f} %, d' "
          f"{', '.join(f'{v:.2f}' for v in b64['pairwise_dprime_heldout_mean'])}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
