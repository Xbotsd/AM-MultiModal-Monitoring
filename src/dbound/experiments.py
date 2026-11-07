"""Experiments: algebra check, real-data measurement, ablation, comparison.

Every function returns plain dictionaries so results serialise to JSON and the
paper tables are generated from files rather than transcribed by hand.
"""

from __future__ import annotations

import math
import pathlib
from math import erfc

import numpy as np
from scipy import ndimage as ndi

from . import bound, detectors, psf, realdata

Z = bound.z_from_p


# --------------------------------------------------------------------------
# 1. check of the algebra (exact truth; not study data)
# --------------------------------------------------------------------------

def check_algebra(rates=(500, 1000, 2000, 4000, 8000, 16000, 32000),
                  n_sig: int = 250, n_null: int = 400,
                  n_grid: int = 40, alpha: float = 0.05,
                  seed: int = 20261108) -> dict:
    """Verify Propositions 1-2 and the tightness of the bound.

    This is a numerical check of the derivation, carried out with exact truth.
    It is not experimental data and is never presented as such.
    """
    xs, es = bound.energy_curve()
    dp = np.sqrt(es)
    small = xs <= 0.45
    exp_small = float(np.polyfit(np.log(xs[small]), np.log(dp[small]), 1)[0])
    big = xs > 3.0
    slopes = [[float(x), bound.local_dprime_exponent(float(x))] for x in xs[big]]

    rng = np.random.default_rng(seed)
    ker = psf.gaussian_kernel(n_grid, 1.0)
    ker_hat = np.fft.fftn(ker)
    z_a = Z(1.0 - alpha)
    peak_null = np.array([np.max(rng.standard_normal((n_grid,) * 3))
                          for _ in range(n_null)])
    q_peak = float(np.quantile(peak_null, 1.0 - alpha))

    rows = []
    for a in (1, 2, 3, 5, 8, 12):
        s = psf.blur(psf.sphere(n_grid, a), ker)
        sq = float(np.sqrt((s * s).sum()))
        for k in (0.5, 1.0, 2.0):
            d_target = 1.0 / k
            sigma = sq / d_target
            thr_mf = z_a * sigma * sq
            null_mm = np.array([
                detectors.scanned_mf(sigma * rng.standard_normal((n_grid,) * 3), ker)
                for _ in range(n_null)])
            thr_mm = float(np.quantile(null_mm, 1.0 - alpha))
            thr_pk = sigma * q_peak
            h = {"mf": 0, "mm": 0, "pk": 0}
            for _ in range(n_sig):
                y = s + sigma * rng.standard_normal((n_grid,) * 3)
                h["mf"] += float((y * s).sum()) > thr_mf
                h["mm"] += detectors.scanned_mf(y, ker) > thr_mm
                h["pk"] += float(y.max()) > thr_pk
            b = bound.ndtr(d_target - z_a)
            rows.append({"a": a, "d_target": d_target, "pod_bound": b,
                         "pod_mf": h["mf"] / n_sig, "pod_maxmf": h["mm"] / n_sig,
                         "pod_peak": h["pk"] / n_sig,
                         "ci95": 1.96 * math.sqrt(max(b * (1 - b), 1e-9) / n_sig)})
    gap = {k: float(np.mean([r["pod_bound"] - r[k] for r in rows]))
           for k in ("pod_mf", "pod_maxmf", "pod_peak")}
    viol = {k: int(sum(r[k] > r["pod_bound"] + r["ci95"] for r in rows))
            for k in ("pod_mf", "pod_maxmf", "pod_peak")}
    return {"rates": list(rates), "small_exponent": exp_small,
            "large_slopes": slopes, "rows": rows,
            "mean_gap": gap, "violations": viol}


# --------------------------------------------------------------------------
# 2. real data
# --------------------------------------------------------------------------

def measure_group(folder: str, a_values=(1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 16),
                  n_trials: int = 400, alpha: float = 0.01,
                  seed: int = 20261108, pod_a=(2, 4, 8)) -> dict:
    s = realdata.load_series(folder)
    vol = s.volume
    mask = realdata.material_mask(vol)
    sigma = realdata.sigma_second_diff(vol, mask)
    fwhm_ac = psf.psf_from_autocorrelation(vol, mask)
    fwhm_edge = psf.psf_from_edge(vol, mask)
    rng = np.random.default_rng(seed)

    kappas = []
    for a in a_values:
        k = realdata.kappa(vol, mask, sigma, float(a), fwhm_ac, n_trials=n_trials,
                           alpha=alpha, rng=rng)
        kappas.append(k)

    pods = []
    for a in pod_a:
        pods.extend(realdata.pod_curve_real(vol, mask, sigma, float(a), fwhm_ac,
                                            n_trials=n_trials, alpha=alpha,
                                            rng=rng))
    return {"series": s.meta(), "sigma": sigma,
            "psf_fwhm_autocorr": fwhm_ac, "psf_fwhm_edge": fwhm_edge,
            "kappa": kappas, "pod": pods}


def cross_group(folders: dict[str, str], a_values=(2, 4, 8, 16),
                n_trials: int = 300, alpha: float = 0.01,
                seed: int = 20261108) -> dict:
    """Does kappa belong to the material or to the reconstruction?"""
    out = {}
    rng = np.random.default_rng(seed)
    for name, folder in folders.items():
        s = realdata.load_series(folder)
        mask = realdata.material_mask(s.volume)
        sigma = realdata.sigma_second_diff(s.volume, mask)
        fwhm = psf.psf_from_autocorrelation(s.volume, mask)
        rows = [realdata.kappa(s.volume, mask, sigma, float(a), fwhm,
                               n_trials=n_trials, alpha=alpha, rng=rng)
                for a in a_values]
        out[name] = {"series": s.meta(), "sigma": sigma, "fwhm": fwhm,
                     "kappa": rows}
    return out


# --------------------------------------------------------------------------
# 3. ablation
# --------------------------------------------------------------------------

def ablate(folder: str, a: float = 8.0, n_trials: int = 300,
           seed: int = 20261108) -> dict:
    """What each estimator choice does to kappa, and therefore to the bound."""
    s = realdata.load_series(folder)
    vol = s.volume
    mask = realdata.material_mask(vol)
    rng = np.random.default_rng(seed)
    sigma = realdata.sigma_second_diff(vol, mask)
    fwhm = psf.psf_from_autocorrelation(vol, mask)

    templates = {}
    for kind in ("dc", "zero_mean", "annular"):
        k = realdata.kappa(vol, mask, sigma, a, fwhm, kind=kind,
                           n_trials=n_trials, rng=rng)
        templates[kind] = k

    sigmas = {
        "second_diff_mad": sigma,
        "plain_std": realdata.sigma_plain_std(vol, mask),
        "percentile_99": realdata.sigma_percentile(vol, mask, 0.99),
    }

    psfs = {
        "autocorrelation": fwhm,
        "edge_spread": psf.psf_from_edge(vol, mask),
        "assumed_one_voxel": 1.0,
    }

    pads = {}
    for pad in (0, 4):
        pads[str(pad)] = realdata.kappa(vol, mask, sigma, a, fwhm, pad=pad,
                                        n_trials=n_trials, rng=rng)

    alphas = {}
    for al in (0.001, 0.01, 0.05):
        k = realdata.kappa(vol, mask, sigma, a, fwhm, n_trials=n_trials,
                           alpha=al, rng=rng)
        alphas[str(al)] = k

    return {"a": a, "sigma": sigma, "fwhm": fwhm,
            "templates": templates, "sigmas": sigmas, "psfs": psfs,
            "padding": pads, "alpha": alphas}


# --------------------------------------------------------------------------
# 4. comparison of detectors on real data
# --------------------------------------------------------------------------

def compare_detectors(folder: str, a: float = 4.0, ratio: float = 8.0,
                      n_trials: int = 300, alpha: float = 0.01,
                      seed: int = 20261108) -> dict:
    """Oracle matched filter, scanned matched filter and peak, on real metal."""
    s = realdata.load_series(folder)
    vol = s.volume
    mask = realdata.material_mask(vol)
    sigma = realdata.sigma_second_diff(vol, mask)
    fwhm = psf.psf_from_autocorrelation(vol, mask)
    rng = np.random.default_rng(seed)

    t = detectors.template(a, fwhm, kind="annular")
    n = t.shape[0]
    centres = realdata.sample_centres(mask, n, n_trials, rng)
    t_hat = np.fft.fftn(t, s=(n, n, n))
    null = {"mf": [], "mm": [], "pk": []}
    for c in centres:
        p = realdata.patch_at(vol, c, n)
        if p is None:
            continue
        null["mf"].append(detectors.matched_filter(p, t))
        null["mm"].append(float(np.real(
            np.fft.ifftn(np.fft.fftn(p) * t_hat)).max()))
        null["pk"].append(float(p.max()))
        if len(null["mf"]) >= n_trials:
            break
    null = {k: np.asarray(v, dtype=float) for k, v in null.items()}
    thr = {k: float(np.quantile(v, 1.0 - alpha)) for k, v in null.items()}
    # each detector gains a different amount from the same injected flaw:
    # the matched filters project onto the template, the peak detector responds
    # to the peak of the blurred flaw
    inc = detectors.increment(t, a, fwhm)
    peak_gain = float(detectors._signal(a, n, fwhm).max())
    gains = {"mf": inc, "mm": inc, "pk": peak_gain}
    d_i = ratio * sigma
    pod = {k: float(np.mean(null[k] + d_i * gains[k] > thr[k])) for k in null}
    # annihilation check: with no flaw the false-alarm rate must equal alpha
    pod_null = {k: float(np.mean(null[k] > thr[k])) for k in null}
    return {"a": a, "ratio": ratio, "sigma": sigma, "fwhm": fwhm,
            "sqrt_E": float(np.sqrt(detectors.signal_energy(a, fwhm, n=n))),
            "increment": inc, "peak_gain": peak_gain,
            "pod": pod, "false_alarm_rate": pod_null,
            "null_sd": {k: float(v.std()) for k, v in null.items()},
            "threshold": thr}


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def run_all(data_root: str | pathlib.Path, out_dir: str | pathlib.Path) -> dict:
    import json
    root = pathlib.Path(data_root)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result: dict = {}

    result["algebra"] = check_algebra()
    (out / "verify_algebra.json").write_text(
        json.dumps(result["algebra"], indent=1), encoding="utf-8")

    groups = {}
    for name in ("vol_gd", "vol_g1", "vol_g2"):
        folder = root / name
        if folder.is_dir() and len(list(folder.glob("*.dcm"))) > 10:
            groups[name] = str(folder)
    if groups:
        result["groups"] = {}
        for name, folder in groups.items():
            m = measure_group(folder)
            result["groups"][name] = m
            (out / f"measure_{name}.json").write_text(
                json.dumps(m, indent=1), encoding="utf-8")
        result["cross_group"] = cross_group(groups)
        (out / "cross_group.json").write_text(
            json.dumps(result["cross_group"], indent=1), encoding="utf-8")

    if groups:
        first = groups[sorted(groups)[0]]
        result["ablation"] = ablate(first)
        (out / "ablation.json").write_text(
            json.dumps(result["ablation"], indent=1), encoding="utf-8")
        result["comparison"] = compare_detectors(first)
        (out / "comparison.json").write_text(
            json.dumps(result["comparison"], indent=1), encoding="utf-8")
    return result
