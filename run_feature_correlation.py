# -*- coding: utf-8 -*-
"""
特征相关性矩阵
调用口令：SCP111
运行: py -3.12 run_feature_correlation.py
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.fft import rfft, rfftfreq
from scipy.stats import kurtosis as scipy_kurtosis, skew as scipy_skew

DATA_DIR_EPFL = Path("data/epfl_acoustic/Deciphering AE")
DATA_DIR_LU = Path("data/laser_ultrasound")
OUTPUT_DIR = Path("data/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 9
plt.rcParams['font.weight'] = 'bold'

SR_EPFL = 200000.0
SR_LU = 20000.0

FEATURE_NAMES = [
    "kurtosis", "skewness", "crest",
    "centroid", "bandwidth", "entropy",
    "FFT1", "FFT2", "FFT3", "FFT4",
    "FFT5", "FFT6", "FFT7", "FFT8"
]


def fft_band_energies(signal, sr, n_bands=8):
    fft_vals = np.abs(rfft(signal))
    freqs = rfftfreq(len(signal), 1.0 / sr)
    psd = fft_vals ** 2
    total = np.sum(psd) + 1e-10
    band_edges = np.linspace(0, sr / 2, n_bands + 1)
    return [float(np.sum(psd[(freqs >= band_edges[i]) & (freqs < band_edges[i+1])]) / total)
            for i in range(n_bands)]


def extract_features(signal, sr):
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
    return [kurt, skew_val, crest, centroid, bandwidth, spectral_entropy] + fft_band_energies(signal, sr)


def correlation_matrix(X):
    """计算 Pearson 相关系数矩阵"""
    X = np.asarray(X, dtype=np.float64)
    X_centered = X - np.mean(X, axis=0, keepdims=True)
    X_std = np.std(X, axis=0, keepdims=True) + 1e-10
    X_norm = X_centered / X_std
    n = X.shape[0]
    C = (X_norm.T @ X_norm) / (n - 1)
    return C


def plot_correlation(C, names, title, save_path):
    fig, ax = plt.subplots(figsize=(4.0, 3.6))
    im = ax.imshow(C, cmap='RdBu_r', vmin=-1, vmax=1, aspect='equal')
    # 刻度
    ax.set_xticks(np.arange(len(names)))
    ax.set_yticks(np.arange(len(names)))
    ax.set_xticklabels(names, rotation=45, ha='right', fontsize=7)
    ax.set_yticklabels(names, fontsize=7)
    # 数值标注
    for i in range(len(names)):
        for j in range(len(names)):
            val = C[i, j]
            color = 'white' if abs(val) > 0.6 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=5, fontweight='bold', color=color)
    # 色条
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=7)
    cbar.set_label('Pearson r', fontsize=8, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=600, bbox_inches='tight')
    plt.close()
    print(f"  ✅ {save_path.name}")


def report_high_correlation(C, names, threshold=0.8):
    """报告高相关特征对"""
    print(f"\n  高相关特征对 (|r| > {threshold}):")
    count = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if abs(C[i, j]) > threshold:
                print(f"    {names[i]} ↔ {names[j]}: r = {C[i, j]:.3f}")
                count += 1
    if count == 0:
        print(f"    无（所有特征对 |r| ≤ {threshold}）")
    return count


def main():
    print("=" * 60)
    print("特征相关性矩阵")
    print("=" * 60)

    # ---------- 声学模块 ----------
    print("\n[声学模块] 加载数据...")
    raw = np.load(DATA_DIR_EPFL / "D1_rawspace_5000.npy", mmap_mode='r')
    labels = np.load(DATA_DIR_EPFL / "D1_classspace_5000.npy")

    X = []
    for label in range(3):
        idx = np.where(labels == label)[0][:500]
        for i in idx:
            X.append(extract_features(raw[i], SR_EPFL))
    X = np.array(X)
    print(f"  特征矩阵: {X.shape}")

    C = correlation_matrix(X)
    print(f"  相关系数范围: [{C.min():.3f}, {C.max():.3f}]")
    high = report_high_correlation(C, FEATURE_NAMES, threshold=0.8)

    plot_correlation(C, FEATURE_NAMES, "Acoustic",
                     OUTPUT_DIR / "fig_corr_acoustic.png")

    # ---------- 激光超声模块 ----------
    print("\n[激光超声模块] 加载数据...")
    X_raw = np.load(DATA_DIR_LU / "X_lu.npy")
    y_raw = np.load(DATA_DIR_LU / "y_lu.npy")

    X = []
    for label in [0, 1]:
        idx = np.where(y_raw == label)[0][:500]
        for i in idx:
            X.append(extract_features(X_raw[i], SR_LU))
    X = np.array(X)
    print(f"  特征矩阵: {X.shape}")

    C = correlation_matrix(X)
    print(f"  相关系数范围: [{C.min():.3f}, {C.max():.3f}]")
    high = report_high_correlation(C, FEATURE_NAMES, threshold=0.8)

    plot_correlation(C, FEATURE_NAMES, "Laser Ultrasound",
                     OUTPUT_DIR / "fig_corr_lu.png")

    print(f"\n{'=' * 60}")
    print(f"相关性矩阵已生成至: {OUTPUT_DIR}")
    print(f"  - fig_corr_acoustic.png")
    print(f"  - fig_corr_lu.png")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()