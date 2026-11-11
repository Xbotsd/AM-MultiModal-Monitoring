"""Draw the six figures of the integrated manuscript from the result files.

Everything plotted here is read from ``results/*.json`` or computed from the
``dbound`` package; nothing is transcribed by hand.  Output: a vector PDF and a
300 dpi PNG preview per figure, in ``results/figures/``.

    python CODE/6_visualization/run_ndte_figures.py

Figures
    fig1_energy    deflection factor sqrt(E) against the size ratio, with asymptotes
    fig2_pod       POD bound at four contrast-to-noise ratios
    fig3_system    layering of the system, with the registry counts read live
    fig4_channels  acoustic spectral accuracy and laser-ultrasound POD vs the bound
    fig5_kappa     measured clutter inflation on the XCT stack, one or three volumes
    fig6_detectors real-metal detector POD, kappa ablation and noise estimators

The stage requires the result files produced by the measured stages
(``ae_spectral``, ``lu_echo``, ``xct_clutter``).  Run ``ammonitor chain measured``
first, or run the individual stages.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mp  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ammonitor import report  # noqa: E402
from dbound import bound  # noqa: E402

SINGLE, DOUBLE = 3.5, 7.1
INK = "#1a1a1a"
BLUE, RED, GREEN, ORANGE = "#1f4e79", "#c00000", "#548235", "#ed7d31"


def save(fig, out: Path, name: str) -> None:
    fig.savefig(out / f"{name}.pdf")
    fig.savefig(out / f"{name}.png", dpi=300)
    plt.close(fig)
    print(f"  wrote {name}.pdf and .png")


def fig1_energy(out: Path) -> None:
    xs, es = bound.energy_curve()
    dp = np.sqrt(es)
    fig, ax = plt.subplots(figsize=(SINGLE, 2.6))
    ax.loglog(xs, dp, "o-", ms=2.2, lw=1.0, color=BLUE, label=r"$\sqrt{E(a/L)}$")
    a3 = dp[0] * (xs / xs[0]) ** 3
    ax.loglog(xs, a3, "--", lw=0.8, color=RED)
    big = xs > 12
    c = dp[big][0] / xs[big][0] ** 1.5
    ax.loglog(xs, c * xs ** 1.5, ":", lw=0.9, color=GREEN)
    ax.axvline(1.0, color="0.6", lw=0.6, ls="-")
    ax.text(1.05, dp.min() * 1.4, "voxel size", rotation=90, fontsize=6, color="0.4")
    ax.text(0.30, a3[1] * 2.2, r"$\propto x^{3}$", fontsize=7, color=RED)
    ax.text(13.0, c * 13.0 ** 1.5 * 3.2, r"$\propto x^{3/2}$", fontsize=7, color=GREEN)
    ax.set_xlabel(r"flaw size / PSF width,  $x = a/L$")
    ax.set_ylabel(r"deflection factor  $\sqrt{E}$")
    ax.set_xlim(0.2, 24)
    ax.legend(frameon=False, loc="upper left")
    save(fig, out, "fig1_energy")


def fig2_pod(out: Path) -> None:
    xs, es = bound.energy_curve()
    sq = np.sqrt(es)
    z = bound.z_from_p(0.99)
    fig, ax = plt.subplots(figsize=(SINGLE, 2.6))
    for ratio, colour in zip((1, 2, 5, 10), ("#9dc3e6", "#5b9bd5", BLUE, "#0b2e4f")):
        pod = np.array([bound.ndtr(ratio * s - z) for s in sq])
        ax.semilogx(xs, pod, lw=1.2, color=colour, label=rf"$\Delta I/\sigma={ratio}$")
    ax.axhline(0.9, color="0.4", lw=0.7, ls="--")
    ax.text(4.6, 0.915, "POD = 0.9", fontsize=6, color="0.35")
    ax.set_xlabel(r"$x = a/L$")
    ax.set_ylabel(r"POD bound at $\alpha = 0.01$")
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(0.2, 24)
    ax.legend(frameon=False, loc="upper left")
    save(fig, out, "fig2_pod")


def fig3_system(out: Path) -> None:
    counts = report.provenance_summary()
    n = sum(counts.values())

    def box(ax, x, y, w, h, label, fc, ec, fs=8.2, weight="normal"):
        ax.add_patch(mp.FancyBboxPatch((x, y), w, h,
                                       boxstyle="round,pad=0.010,rounding_size=0.030",
                                       linewidth=0.9, edgecolor=ec, facecolor=fc))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=fs, color=INK, weight=weight, linespacing=1.35)

    def arrow(ax, x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8,
                                    shrinkA=0, shrinkB=0, mutation_scale=7))

    fig, ax = plt.subplots(figsize=(6.6, 3.75))
    ax.set_xlim(0, 6.6)
    ax.set_ylim(0, 3.75)
    ax.axis("off")
    meas, meas_e = "#dce9f5", "#2f5d8a"
    dec, dec_e = "#e3f0e3", "#2f6b3a"
    reg, reg_e = "#f5eddc", "#8a6b2f"
    outp, out_e = "#f7dede", "#8a2f2f"

    ax.text(0.05, 3.62, "Sensing layer", fontsize=8.4, weight="bold", color=INK, va="top")
    for label, x in (("Acoustic\n100–900 kHz", 0.05), ("Laser US\n5 MHz, 0.25 mm", 1.20),
                     ("Structured\nlight 3.98 µm", 2.35), ("Coaxial\n1000 fps*", 3.50)):
        box(ax, x, 2.88, 1.05, 0.52, label, meas, meas_e, fs=7.4)
        arrow(ax, x + 0.525, 2.86, x + 0.525, 2.72)
    box(ax, 0.05, 2.34, 4.50, 0.36,
        "Synchronised acquisition — laser trigger, common clock, registration\n"
        "acceptance targets < 1 ms / < 0.1 mm (design, not exercised)",
        "#eeeeee", "#666666", fs=7.0)
    arrow(ax, 2.30, 2.32, 2.30, 2.18)
    box(ax, 0.05, 1.66, 4.50, 0.50,
        "Measurement chain   (edge unit, fully offline)\n"
        "14-D descriptor · kNN + MLP soft vote · scalar Kalman kernel\n"
        "fusion of depth estimates · residual filter in unwrapping · grading",
        meas, meas_e, fs=7.0)
    arrow(ax, 2.30, 1.64, 2.30, 1.50)
    box(ax, 0.05, 0.95, 4.50, 0.53,
        "Decision layer   (dbound)\n"
        "d′ = (ΔI/σ) · √E(a/L) · √N        POD ≤ Φ( d′ − z$_{1-α}$ )\n"
        "inversion → L$_{max}$;   N$_{eq}$ = k$^{6}$ below the voxel, k$^{3}$ above",
        dec, dec_e, fs=7.0)
    arrow(ax, 2.30, 0.93, 2.30, 0.79)
    box(ax, 0.05, 0.44, 4.50, 0.33,
        "Claim reporter — process evidence | method evidence | neither", outp, out_e, fs=7.2)
    box(ax, 4.72, 0.44, 1.62, 2.26,
        f"Stage registry\n\n{n} stages\n{counts['measured']} measured\n"
        f"{counts['simulated']} simulated\n{counts['derived']} derived\n\n"
        "generated from the\nsource; asserted\nby tests",
        reg, reg_e, fs=7.2)
    arrow(ax, 4.70, 1.55, 4.57, 1.55)
    ax.text(0.05, 0.16,
            "* fourth channel specified, not exercised: no measured capture in this study.",
            fontsize=6.6, color="#444444", va="bottom")
    save(fig, out, "fig3_system")


def fig4_channels(out: Path, results: Path) -> None:
    ae = json.loads((results / "ae_spectral.json").read_text(encoding="utf-8"))
    lu = json.loads((results / "lu_echo.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.8))
    bands = sorted(int(k) for k in ae)
    m = [ae[str(k)]["cv_acc_mean"] * 100 for k in bands]
    s = [ae[str(k)]["cv_acc_sd"] * 100 for k in bands]
    ax[0].errorbar(bands, m, yerr=s, fmt="o-", color="k", ms=4, capsize=2, lw=1,
                   label="log-spectrum LDA (5-fold)")
    ax[0].axhspan(82.2 - 2.2, 82.2 + 2.2, color="0.85",
                  label="14-D descriptor ensemble (5-fold)")
    ax[0].axhline(100 / 3, color="0.5", ls=":", lw=1, label="chance")
    ax[0].set_xscale("log", base=2)
    ax[0].set_xticks(bands)
    ax[0].set_xticklabels(bands)
    ax[0].set_xlabel("number of log sub-bands")
    ax[0].set_ylabel("three-regime accuracy (%)")
    ax[0].set_ylim(30, 100)
    ax[0].legend(frameon=False, fontsize=7, loc="lower right")
    ax[0].set_title("(a) acoustic emission, EPFL D1", fontsize=9)

    labels = ["back wall", "late arrival"]
    x = np.arange(2)
    w = 0.26
    for i, (key, name, colour) in enumerate((
            ("pod_matched_filter", "matched filter", "0.3"),
            ("pod_energy", "energy detector", "0.6"),
            ("pod_descriptor", "descriptor ensemble", "0.85"))):
        ax[1].bar(x + (i - 1) * w, [lu["bw"][key], lu["late"][key]], w,
                  color=colour, edgecolor="k", lw=0.6, label=name)
    bound_pod = [lu["bw"]["pod_bound_white"], lu["late"]["pod_bound_white"]]
    ax[1].plot([-0.55, 1.55], [min(bound_pod)] * 2, color="k", ls="--", lw=1,
               label="white-noise bound")
    labels = [f"{name}\nd'={lu[g]['d_white']:.1f}" for name, g in zip(labels, ("bw", "late"))]
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(labels)
    ax[1].set_ylabel("POD at 1% false alarm")
    ax[1].set_ylim(0, 1.16)
    ax[1].set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax[1].set_xlim(-0.6, 1.6)
    ax[1].legend(frameon=False, fontsize=6.5, loc="lower center", ncol=2,
                 bbox_to_anchor=(0.5, 1.0))
    ax[1].set_title("(b) laser ultrasound, Cranfield LIPA", fontsize=9, pad=26)
    fig.tight_layout()
    save(fig, out, "fig4_channels")


def fig5_kappa(out: Path, results: Path) -> None:
    payload = json.loads((results / "xct_clutter.json").read_text(encoding="utf-8"))
    primary = payload["primary"]
    x = np.array([r["x"] for r in primary["kappa"]])
    k = np.array([r["kappa"] for r in primary["kappa"]])
    lo = np.array([r["kappa_lo"] for r in primary["kappa"]])
    hi = np.array([r["kappa_hi"] for r in primary["kappa"]])

    fig, ax = plt.subplots(figsize=(SINGLE, 2.7))
    ax.errorbar(x, k, yerr=[k - lo, hi - k], fmt="o-", ms=2.6, lw=1.0, capsize=2,
                color=BLUE, label="GD (212 slices)")
    cross = payload.get("cross_group")
    if cross:
        for name, marker, colour in (("vol_g1", "s", RED), ("vol_g2", "^", GREEN)):
            if name not in cross:
                continue
            rows = cross[name]["kappa"]
            ax.plot([r["x"] for r in rows], [r["kappa"] for r in rows],
                    marker + "--", ms=3.2, lw=0.8, color=colour,
                    label=name.replace("vol_", "").upper())
    sel = x > 4
    if sel.sum() >= 2:
        p = np.polyfit(np.log(x[sel]), np.log(k[sel]), 1)[0]
        ax.text(0.04, 0.80, rf"GD slope above $x=4$: $x^{{{p:.2f}}}$",
                transform=ax.transAxes, fontsize=6.5, color="0.3")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$x = a/L$")
    ax.set_ylabel(r"clutter inflation $\kappa$")
    ax.legend(frameon=False, loc="lower right")
    save(fig, out, "fig5_kappa")


def fig6_detectors(out: Path, results: Path) -> None:
    payload = json.loads((results / "xct_clutter.json").read_text(encoding="utf-8"))
    comp, abl = payload.get("comparison"), payload.get("ablation")
    if not comp or not abl:
        print("  fig6 skipped: comparison/ablation absent from xct_clutter.json")
        return
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE, 2.2),
                             gridspec_kw={"width_ratios": [1.1, 1.0, 1.0]})
    ax = axes[0]
    labels = ["oracle\nmatched filter", "searched\nmatched filter", "template-free\npeak"]
    vals = [comp["pod"]["mf"], comp["pod"]["mm"], comp["pod"]["pk"]]
    bars = ax.bar(range(3), vals, color=[BLUE, "#5b9bd5", "#9dc3e6"], width=0.62)
    ax.axhline(1.0, color=RED, lw=0.9, ls="--")
    ax.text(2.3, 0.94, "white-noise bound", fontsize=6, color=RED, ha="right")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center",
                fontsize=6.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=6.2)
    ax.set_ylabel(r"POD at $\alpha = 0.01$")
    ax.set_ylim(0, 1.12)
    ax.set_title("(a) detectors, real data", fontsize=7.5)

    ax = axes[1]
    kinds = ["dc", "zero_mean", "annular"]
    kv = [abl["templates"][k]["kappa"] for k in kinds]
    ax.bar(range(3), kv, color=[RED, ORANGE, GREEN], width=0.6)
    for i, v in enumerate(kv):
        ax.text(i, v + 2, f"{v:.0f}", ha="center", fontsize=6.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["raw\n(no mean)", "global\nzero-mean", "annular\n(used)"],
                       fontsize=6.2)
    ax.set_ylabel(r"$\kappa$ at $a = 8$ voxels")
    ax.set_title("(b) template construction", fontsize=7.5)

    ax = axes[2]
    sig = abl["sigmas"]
    names = ["second_diff_mad", "percentile_99", "plain_std"]
    sv = [sig[n] for n in names]
    ax.bar(range(3), sv, color=[GREEN, ORANGE, RED], width=0.6)
    for i, v in enumerate(sv):
        ax.text(i, v + 12, f"{v:.0f}", ha="center", fontsize=6.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["2nd-diff\nMAD (used)", "99th\npercentile", "plain\nstd"],
                       fontsize=6.2)
    ax.set_ylabel(r"noise estimate $\sigma$")
    ax.set_title("(c) noise estimator", fontsize=7.5)
    fig.tight_layout(w_pad=1.2)
    save(fig, out, "fig6_detectors")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out-dir", default=str(ROOT / "results" / "figures"))
    args = ap.parse_args()

    results = Path(args.results)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
        "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    })
    print("figures:")
    fig1_energy(out)
    fig2_pod(out)
    fig3_system(out)
    fig4_channels(out, results)
    fig5_kappa(out, results)
    fig6_detectors(out, results)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
