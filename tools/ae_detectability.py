"""Transient-channel detectability on the EPFL acoustic dataset.

The volumetric bound asks how large a flaw must be to be seen; the transient bound
asks how much signal an event must carry.  This tool measures the second on real
acoustic-emission waveforms: it takes a class mean as the expected waveform, the
residual spread as the noise the detector actually faces, and reports the
deflection, the attainable POD, and the noise level at which the event would still
be detected with 90% probability.

    python tools/ae_detectability.py --data-root "C:/.../am_monitoring/data" --set D1
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from ammonitor import decision  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--set", default="D1")
    ap.add_argument("--max-per-class", type=int, default=300)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    root = pathlib.Path(a.data_root) / "epfl_acoustic" / "Deciphering AE"
    raw = np.load(root / f"{a.set}_rawspace_5000.npy", mmap_mode="r")
    lab = np.load(root / f"{a.set}_classspace_5000.npy", mmap_mode="r")
    labels = np.asarray(lab).ravel()
    x = np.asarray(raw)
    print(f"{a.set}: {x.shape}, labels {np.unique(labels)[:6]} ...")

    rows = []
    for cls in np.unique(labels):
        idx = np.flatnonzero(labels == cls)[: a.max_per_class]
        if idx.size < 20:
            continue
        w = x[idx].astype(np.float64)
        template = w.mean(axis=0)
        residual = w - template
        sigma_resid = float(residual.std())
        energy = decision.transient_energy(template)
        d_measured = float(np.sqrt(energy) / sigma_resid)
        pod = decision.pod(1.0, sigma_resid, energy, alpha=0.01)
        # noise level at which this event would still reach POD = 0.9
        sigma_max = float(np.sqrt(energy) / (decision.z_from_p(0.9)
                                             + decision.z_from_p(0.99)))
        rows.append({"class": int(cls), "n": int(idx.size),
                     "n_samples": int(template.size),
                     "energy": energy, "sigma_residual": sigma_resid,
                     "d_prime": d_measured, "pod_at_alpha_0.01": pod,
                     "sigma_max_for_pod_0.9": sigma_max})

    rows.sort(key=lambda r: r["d_prime"])
    print(f"\n{'class':>6} {'n':>5} {'dprime':>8} {'POD':>7} {'sigma_max':>10}")
    for r in rows:
        print(f"{r['class']:6d} {r['n']:5d} {r['d_prime']:8.1f} "
              f"{r['pod_at_alpha_0.01']:7.3f} {r['sigma_max_for_pod_0.9']:10.1f}")

    out = {"set": a.set, "shape": list(x.shape), "classes": rows}
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
