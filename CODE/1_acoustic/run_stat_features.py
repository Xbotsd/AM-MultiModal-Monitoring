# -*- coding: utf-8 -*-
"""
声学特征显著性检验 (ANOVA + Kruskal-Wallis)
调用口令：SCP111
运行: py -3.12 run_stat_features.py
"""
# --- AUTO INJECTED PATH FIX ---
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT_DIR)
# ------------------------------

import numpy as np
import pywt
from pathlib import Path
from scipy.fft import rfft, rfftfreq
from scipy.stats import kurtosis as scipy_kurtosis, skew as scipy_skew
from scipy.stats import f_oneway, kruskal
import json

DATA_DIR = Path("data/epfl_acoustic/Deciphering AE")
OUTPUT_DIR = Path("data/statistics")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATASET = "D1"
N_CLASSES = 3
MAX_PER_CLASS = 500
SR = 200000.0


def extract_features(signal, sr=SR):
    signal = np.asarray(signal, dtype=np.float64).flatten()
    if len(signal) < 16:
        return [0.0] * 14
    kurt = float(scipy_kurtosis(signal))
    skew_val = float(scipy_skew(signal))
    rms = float(np.sqrt(np.mean(signal ** 2)))
    peak = float(np.max(np.abs(signal)))
    crest = peak / (rms + 1e-10)
    fft_vals = np.abs(rfft(signal))
    freqs = rfftfreq(len(signal), 1.0 / sr)
    psd = fft_vals ** 2
    total_energy = np.sum(psd) + 1e-10
    centroid = float(np.sum(freqs * psd) / total_energy)
    bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * psd) / total_energy))
    psd_norm = psd / total_energy
    psd_norm = psd_norm[psd_norm > 0]
    spectral_entropy = float(-np.sum(psd_norm * np.log2(psd_norm + 1e-10)))
    wp = pywt.WaveletPacket(data=signal, wavelet='db4', maxlevel=3)
    wp_energies = [np.sum(np.array(node.data) ** 2) for node in wp.get_level(3, 'natural')]
    wp_total = sum(wp_energies) + 1e-10
    wp_norm = [e / wp_total for e in wp_energies]
    return [kurt, skew_val, crest, centroid, bandwidth, spectral_entropy] + wp_norm


FEATURE_NAMES = ["kurtosis", "skewness", "crest", "centroid", "bandwidth",
                 "spectral_entropy", "wp_band_0", "wp_band_1", "wp_band_2", "wp_band_3",
                 "wp_band_4", "wp_band_5", "wp_band_6", "wp_band_7"]


def main():
    print("=" * 60)
    print("声学特征显著性检验")
    print("=" * 60)

    raw = np.load(DATA_DIR / f"{DATASET}_rawspace_5000.npy", mmap_mode='r')
    labels = np.load(DATA_DIR / f"{DATASET}_classspace_5000.npy")

    X, y = [], []
    for label in range(N_CLASSES):
        idx = np.where(labels == label)[0][:MAX_PER_CLASS]
        for i in idx:
            X.append(extract_features(raw[i]))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    print(f"特征矩阵: {X.shape}")

    print(f"\n{'特征':<20s} {'ANOVA F':>12s} {'ANOVA p':>12s} {'KW p':>12s} {'显著性':>8s}")
    print("-" * 70)
    results = {}
    for j, name in enumerate(FEATURE_NAMES):
        groups = [X[y == c, j] for c in range(N_CLASSES)]
        f_stat, p_anova = f_oneway(*groups)
        kw_stat, p_kw = kruskal(*groups)
        sig = "***" if p_anova < 0.001 else "**" if p_anova < 0.01 else "*" if p_anova < 0.05 else "ns"
        print(f"{name:<20s} {f_stat:>12.3f} {p_anova:>12.2e} {p_kw:>12.2e} {sig:>8s}")
        results[name] = {
            "anova_f": float(f_stat),
            "anova_p": float(p_anova),
            "kruskal_p": float(p_kw),
            "significant": sig,
        }

    with open(OUTPUT_DIR / "feature_significance.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'feature_significance.json'}")
    print("\n显著性标记: *** p<0.001, ** p<0.01, * p<0.05, ns 不显著")


if __name__ == "__main__":
    main()