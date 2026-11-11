"""Laser-ultrasound echo detection against the detectability bound.

Data: Cranfield laser-induced phased array capture, doi:10.17862/cranfield.rd.15190191
(CC BY 4.0).  Place ``201120_Ti_FMC_128ave.mat`` at
``data/laser_ultrasound/201120_Ti_FMC_128ave.mat``.

The capture carries no verified defect label, so no porosity claim is made from it.
What it does carry is two reflectors whose arrival time follows a smooth move-out
across the aperture: the pulse-echo back wall (18--29 us) and a weaker late arrival
(36--47 us).  The move-out surfaces are fitted to envelope picks, every A-scan
contributes one positive window on the predicted arrival and one time-matched
negative window from its own arrival-free region, and the question "is there an echo
in this window" then has a truth independent of any classifier.

Three detectors are compared at a 1 % false alarm: an energy detector, a
matched filter built from the aligned training echo, and the 14-descriptor kNN+MLP
ensemble.  The known-position deflection ``d'`` is estimated from the projection of
the positive window on the template subspace, and the clutter factor ``kappa`` from
the robust spread of the time-matched negatives, so the white-noise bound can be
placed against what the channel actually delivers.

Reproduces Table 5 of the integrated manuscript: d' 16.4 / 6.0, kappa 0.99 / 0.98,
POD 0.838 / 0.427 for the descriptor ensemble against a permitted value of one, and
the 88.2 % / AUC 0.947 held-out echo detection of Table 4.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import scipy.io as sio
from scipy.signal import butter, filtfilt, hilbert
from scipy.special import ndtr, ndtri
from scipy.stats import binomtest, kurtosis, skew
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
MAT = "data/laser_ultrasound/201120_Ti_FMC_128ave.mat"
W, LAG, NE = 32, 4, 68


def resolve(data_root: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/")
    if rel.startswith("data/"):
        rel = rel[len("data/"):]
    return Path(data_root) / rel


def design(u, v):
    return np.stack([np.ones_like(u), u, u * u, v * v, u * v * v], 1)


def fit_moveout(t, env, u, v, t_lo, t_hi, seed_fn):
    """Iteratively pick envelope maxima in a narrowing band around a move-out."""
    pred = seed_fn(u, v)
    half = 3.0e-6
    for _ in range(6):
        picks = np.full(env.shape[0], np.nan)
        amp = np.zeros(env.shape[0])
        for k in range(env.shape[0]):
            lo = np.searchsorted(t, max(t_lo, pred[k] - half))
            hi = np.searchsorted(t, min(t_hi, pred[k] + half))
            if hi - lo < 4:
                continue
            j = lo + np.argmax(env[k, lo:hi])
            picks[k] = t[j]
            amp[k] = env[k, j]
        ok = np.isfinite(picks) & (amp > np.percentile(amp[np.isfinite(picks)], 40))
        X = design(u, v)
        c = np.linalg.lstsq(X[ok], picks[ok], rcond=None)[0]
        pred = X @ c
        r = picks[ok] - pred[ok]
        half = max(0.4e-6, 3 * 1.4826 * np.median(np.abs(r - np.median(r))))
    return pred, c, float(np.sqrt(np.mean(r ** 2))), float(ok.mean())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=str(ROOT / "data"),
                    help="directory that plays the role of data/ (default: <repo>/data)")
    ap.add_argument("--out", default=str(ROOT / "results" / "lu_echo.json"))
    args = ap.parse_args()

    path = resolve(Path(args.data_root), MAT)
    if not path.exists():
        raise SystemExit(f"missing input: {path}")

    m = sio.loadmat(path)
    raw = m["data"].T.astype(float)
    t = m["time"].ravel() * 1e-3
    fs = 1 / np.median(np.diff(t))
    tx = np.arange(4624) // NE
    rx = np.arange(4624) % NE
    u = (tx + rx) / 2.0 - (NE - 1) / 2
    v = (tx - rx).astype(float)
    D = raw - np.median(raw, 1, keepdims=True)
    b, a = butter(4, [0.5e6 / (fs / 2), 8e6 / (fs / 2)], btype="band")
    D = filtfilt(b, a, D, axis=1)
    env = np.abs(hilbert(D, axis=1))

    bw_pred, bw_c, bw_rms, bw_ok = fit_moveout(
        t, env, u, v, 10e-6, 35e-6, lambda uu, vv: 23.6e-6 + 0.167e-6 * uu)
    l2_pred, l2_c, l2_rms, l2_ok = fit_moveout(
        t, env, u, v, 32e-6, 47.4e-6, lambda uu, vv: 41.5e-6 + 0.165e-6 * uu)

    # positive window centred on the fitted arrival, negative window time-matched in
    # the same A-scan from an arrival-free region; both carry +/-LAG samples so the
    # matched filter can search over shifts
    tR = 0.0911e-6 + 0.0837e-6 * np.abs(tx - rx)
    rng = np.random.default_rng(0)
    P, N, SIG, TAG, AS, TN = [], [], [], [], [], []
    for k in range(4624):
        s = D[k]
        excl = ((t < 1.5e-6) | (np.abs(t - tR[k]) < 1.5e-6)
                | (np.abs(t - bw_pred[k]) < 2e-6) | (np.abs(t - l2_pred[k]) < 2e-6))
        free = np.flatnonzero(~excl)
        sg = (1.4826 * np.median(np.abs(s[free][t[free] > 35e-6]
                                        - np.median(s[free][t[free] > 35e-6])))
              if (t[free] > 35e-6).sum() > 50
              else 1.4826 * np.median(np.abs(s[free] - np.median(s[free]))))
        ok = [c for c in free
              if c - W // 2 - LAG >= 0 and c + W // 2 + LAG <= s.size
              and not excl[c - W // 2 - LAG:c + W // 2 + LAG].any()]
        if len(ok) < 2:
            continue
        for tag, tp in (("bw", bw_pred[k]), ("late", l2_pred[k])):
            c0 = int(round((tp - t[0]) * fs))
            if c0 - W // 2 - LAG < 0 or c0 + W // 2 + LAG > s.size:
                continue
            okv = np.asarray(ok)
            cand = okv[np.abs(okv - c0) >= W + 2 * LAG]
            if cand.size == 0:
                continue
            c1 = int(cand[np.argsort(np.abs(cand - c0))[rng.integers(0, min(5, cand.size))]])
            P.append(s[c0 - W // 2 - LAG: c0 + W // 2 + LAG])
            N.append(s[c1 - W // 2 - LAG: c1 + W // 2 + LAG])
            SIG.append(sg)
            TAG.append(tag)
            AS.append(k)
            TN.append(t[c1])
    P, N, SIG, TAG, AS, TN = map(np.array, (P, N, SIG, TAG, AS, TN))
    P /= SIG[:, None]
    N /= SIG[:, None]
    n = len(P)
    core = slice(LAG, LAG + W)

    # split by A-scan, so a scan's two reflector windows stay in one split
    scans = np.unique(AS)
    rng2 = np.random.default_rng(42)
    rng2.shuffle(scans)
    s_tr = set(scans[: len(scans) // 2])
    s_ca = set(scans[len(scans) // 2: 3 * len(scans) // 4])
    tr = np.array([x in s_tr for x in AS])
    ca = np.array([x in s_ca for x in AS])
    te = ~(tr | ca)

    # template per reflector from training positives, aligned by cross-correlation
    T = {}
    for tag in ("bw", "late"):
        Xp = P[tr & (TAG == tag)][:, core]
        ref = Xp[np.argmax((Xp ** 2).sum(1))]
        aligned = []
        for x in Xp:
            c = np.correlate(x, ref, "full")
            j = np.argmax(np.abs(c))
            sh = j - (W - 1)
            aligned.append(np.sign(c[j]) * np.roll(x, -sh))
        tt = np.mean(aligned, 0)
        T[tag] = tt / np.linalg.norm(tt)

    def mf_stat(X, tag):
        return np.max(np.abs(np.stack(
            [X[:, LAG + s: LAG + s + W] @ T[tag] for s in range(-LAG, LAG + 1)], 1)), 1)

    MFp, MFn = np.zeros(n), np.zeros(n)
    for tag in ("bw", "late"):
        i = TAG == tag
        MFp[i] = mf_stat(P[i], tag)
        MFn[i] = mf_stat(N[i], tag)
    null_mean, null_sd = float(MFn[tr].mean()), float(MFn[tr].std())
    dk = np.maximum(MFp - null_mean, 0) / 1.0

    ENp = (P[:, core] ** 2).sum(1)
    ENn = (N[:, core] ** 2).sum(1)

    def feats(X):
        out = []
        for x in X[:, core]:
            xm = x - x.mean()
            pw = np.abs(np.fft.rfft(xm)) ** 2
            f = np.fft.rfftfreq(W, 1 / fs)
            tot = pw.sum() + 1e-12
            cen = (f * pw).sum() / tot
            bwd = np.sqrt((((f - cen) ** 2) * pw).sum() / tot)
            p = pw / tot
            e = np.linspace(0, pw.size, 9).astype(int)
            out.append([kurtosis(x), skew(x),
                        np.abs(x).max() / (np.sqrt((x ** 2).mean()) + 1e-12),
                        cen, bwd, -(p * np.log(p + 1e-12)).sum()]
                       + [pw[e[j]:e[j + 1]].sum() / tot for j in range(8)])
        return np.array(out)

    Fp, Fn = feats(P), feats(N)
    Xtr = np.vstack([Fp[tr], Fn[tr]])
    ytr = np.r_[np.ones(tr.sum()), np.zeros(tr.sum())]
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
    scale = lambda Z: (Z - mu) / sd

    def knn(Xq, k=9):
        out = []
        for i in range(0, len(Xq), 512):
            dd = ((scale(Xq[i:i + 512])[:, None] - scale(Xtr)[None]) ** 2).sum(-1)
            nn = np.argsort(dd, 1)[:, :k]
            w = 1 / (np.sqrt(np.take_along_axis(dd, nn, 1)) + 1e-9)
            out.append((w * ytr[nn]).sum(1) / w.sum(1))
        return np.concatenate(out)

    r = np.random.default_rng(42)
    Xs = scale(Xtr)
    Y = ytr[:, None]
    Ws = [r.standard_normal((14, 64)) * np.sqrt(2 / 14),
          r.standard_normal((64, 32)) * np.sqrt(2 / 64),
          r.standard_normal((32, 1)) * np.sqrt(2 / 32)]
    bs = [np.zeros(64), np.zeros(32), np.zeros(1)]
    lr = 0.02
    for ep in range(2000):
        h1 = np.maximum(0, Xs @ Ws[0] + bs[0])
        h2 = np.maximum(0, h1 @ Ws[1] + bs[1])
        o = 1 / (1 + np.exp(-(h2 @ Ws[2] + bs[2])))
        g = (o - Y) / len(Y)
        g2 = (g @ Ws[2].T) * (h2 > 0)
        g1 = (g2 @ Ws[1].T) * (h1 > 0)
        for W_, b_, gw, gb in ((Ws[2], bs[2], h2.T @ g, g.sum(0)),
                               (Ws[1], bs[1], h1.T @ g2, g2.sum(0)),
                               (Ws[0], bs[0], Xs.T @ g1, g1.sum(0))):
            W_ -= lr * (gw + 1e-4 * W_)
            b_ -= lr * gb
        if ep and ep % 500 == 0:
            lr *= 0.7

    def mlp(Z):
        h1 = np.maximum(0, scale(Z) @ Ws[0] + bs[0])
        h2 = np.maximum(0, h1 @ Ws[1] + bs[1])
        return (1 / (1 + np.exp(-(h2 @ Ws[2] + bs[2])))).ravel()

    ens = lambda Z: 0.4 * knn(Z) + 0.6 * mlp(Z)
    EnsP, EnsN = np.zeros(n), np.zeros(n)
    for msk in (ca, te):
        EnsP[msk] = ens(Fp[msk])
        EnsN[msk] = ens(Fn[msk])

    thr = {"energy": np.quantile(ENn[ca], 0.99),
           "mf": {g: np.quantile(MFn[ca & (TAG == g)], 0.99) for g in ("bw", "late")},
           "ens": np.quantile(EnsN[ca], 0.99)}
    det_mf_p = np.array([MFp[i] > thr["mf"][TAG[i]] for i in range(n)])
    det_mf_n = np.array([MFn[i] > thr["mf"][TAG[i]] for i in range(n)])
    yte = np.r_[np.ones(te.sum()), np.zeros(te.sum())]
    z = ndtri(0.99)
    zmf = {g: (thr["mf"][g] - null_mean) for g in ("bw", "late")}

    sig_local = 1.4826 * np.median(np.abs(N[:, core] - np.median(N[:, core], 1, keepdims=True)), 1)
    out = {
        "n_pairs": int(n), "W": W, "lag": LAG, "alpha": 0.01,
        "window_us": float(W / fs * 1e6),
        "fit": {
            "backwall": {"coef_us": [float(x * 1e6) for x in bw_c],
                         "resid_rms_us": bw_rms * 1e6, "inlier_frac": bw_ok},
            "late": {"coef_us": [float(x * 1e6) for x in l2_c],
                     "resid_rms_us": l2_rms * 1e6, "inlier_frac": l2_ok},
        },
        "heldout_all": {
            "n_pairs": int(te.sum()),
            "descriptor_accuracy": float(((np.r_[EnsP[te], EnsN[te]] > 0.5) == yte).mean()),
            "descriptor_auc": float(roc_auc_score(yte, np.r_[EnsP[te], EnsN[te]])),
            "energy_auc": float(roc_auc_score(yte, np.r_[ENp[te], ENn[te]])),
            "matched_filter_auc": float(roc_auc_score(yte, np.r_[MFp[te], MFn[te]])),
            "far": {"energy": float((ENn[te] > thr["energy"]).mean()),
                    "matched_filter": float(det_mf_n[te].mean()),
                    "descriptor": float((EnsN[te] > thr["ens"]).mean())},
        },
    }
    for g in ("bw", "late"):
        s = te & (TAG == g)
        dE = (P[s][:, core] ** 2).sum(1) - (N[s][:, core] ** 2).sum(1)
        d_white = float(np.sqrt(max(dE.mean(), 0)))
        kap = float(np.median(sig_local[s]))
        out[g] = {
            "n": int(s.sum()), "d_white": d_white, "kappa": kap, "d_eff": d_white / kap,
            "pod_bound_white": float(ndtr(d_white - z)),
            "pod_bound_corrected": float(ndtr(d_white / kap - z)),
            "pod_matched_filter": float(det_mf_p[s].mean()),
            "pod_energy": float((ENp[s] > thr["energy"]).mean()),
            "pod_descriptor": float((EnsP[s] > thr["ens"]).mean()),
            "descriptor_auc": float(roc_auc_score(
                np.r_[np.ones(s.sum()), np.zeros(s.sum())], np.r_[EnsP[s], EnsN[s]])),
            "mf_auc": float(roc_auc_score(
                np.r_[np.ones(s.sum()), np.zeros(s.sum())], np.r_[MFp[s], MFn[s]])),
        }
    out["pod_vs_dprime"] = []
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 10), (10, 1e9)):
        s = te & (dk >= lo) & (dk < hi)
        if s.sum() < 30:
            continue
        pb = float(np.mean([ndtr(dk[i] - zmf[TAG[i]]) for i in np.flatnonzero(s)]))
        k_mf = int(det_mf_p[s].sum())
        out["pod_vs_dprime"].append({
            "dprime": [lo, None if hi > 1e8 else hi], "n": int(s.sum()),
            "pod_bound": pb, "pod_matched_filter": k_mf / int(s.sum()),
            "mf_exceeds_bound_p": float(binomtest(k_mf, int(s.sum()), min(pb, 1 - 1e-12),
                                                  alternative="greater").pvalue),
            "pod_energy": float((ENp[s] > thr["energy"]).mean()),
            "pod_descriptor": float((EnsP[s] > thr["ens"]).mean()),
        })

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"pairs {n}; held-out AUC {out['heldout_all']['descriptor_auc']:.3f}, "
          f"accuracy {out['heldout_all']['descriptor_accuracy']*100:.1f} %")
    for g in ("bw", "late"):
        v = out[g]
        print(f"  {g:4s} d' {v['d_white']:.1f}  kappa {v['kappa']:.2f}  "
              f"POD mf/energy/desc {v['pod_matched_filter']:.3f}/"
              f"{v['pod_energy']:.3f}/{v['pod_descriptor']:.3f}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
