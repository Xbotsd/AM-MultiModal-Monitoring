# -*- coding: utf-8 -*-
"""
t-SNE 特征可视化（纯 numpy 实现）
调用口令：SCP111
运行: py -3.12 run_tsne.py
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


# ============================================================
# 特征提取
# ============================================================
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


# ============================================================
# 纯 numpy t-SNE
# ============================================================
def compute_pairwise_distances(X):
    """计算成对欧氏距离的平方"""
    sum_sq = np.sum(X ** 2, axis=1)
    D = sum_sq[:, None] + sum_sq[None, :] - 2 * X @ X.T
    return np.maximum(D, 0)


def compute_P(X, perplexity=30, tol=1e-4, max_iter=50):
    """计算高维空间的条件概率矩阵 P（对称化）"""
    (n, _) = X.shape
    D = compute_pairwise_distances(X)
    P = np.zeros((n, n))
    target_entropy = np.log(perplexity)

    for i in range(n):
        # 二分搜索找 sigma
        beta_min, beta_max = 1e-20, 1e20
        beta = 1.0
        Di = D[i].copy()
        Di[i] = np.inf

        for _ in range(max_iter):
            # 用当前 beta 计算 P_j|i
            P_i = np.exp(-Di * beta)
            sum_P = np.sum(P_i)
            if sum_P == 0:
                P_i = np.ones(n) / (n - 1)
            else:
                P_i = P_i / sum_P
            # 计算熵
            entropy = -np.sum(P_i * np.log(P_i + 1e-10))
            diff = entropy - target_entropy
            if abs(diff) < tol:
                break
            if diff > 0:
                beta_min = beta
                beta = (beta + beta_max) / 2 if beta_max < 1e19 else beta * 2
            else:
                beta_max = beta
                beta = (beta + beta_min) / 2 if beta_min > 1e-19 else beta / 2
        P[i] = P_i

    # 对称化
    P = (P + P.T) / (2 * n)
    P = np.maximum(P, 1e-12)
    return P


def tsne(X, n_components=2, perplexity=30, learning_rate=200, n_iter=500, momentum=0.8):
    """纯 numpy t-SNE"""
    n = X.shape[0]
    print(f"    计算 P 矩阵 (n={n}, perplexity={perplexity})...")
    P = compute_P(X, perplexity=perplexity)

    # 初始化 Y（小随机）
    np.random.seed(42)
    Y = np.random.randn(n, n_components) * 1e-4
    Y_prev = Y.copy()

    # 梯度下降
    print(f"    梯度下降 ({n_iter} iters)...")
    for it in range(n_iter):
        # 计算 Q
        sum_sq = np.sum(Y ** 2, axis=1)
        D_low = sum_sq[:, None] + sum_sq[None, :] - 2 * Y @ Y.T
        D_low = np.maximum(D_low, 0)
        inv_D = 1.0 / (1.0 + D_low)
        np.fill_diagonal(inv_D, 0)
        Q = inv_D / (np.sum(inv_D) + 1e-10)
        Q = np.maximum(Q, 1e-12)

        # 梯度
        PQ = (P - Q) * inv_D
        grad = np.zeros_like(Y)
        for i in range(n):
            grad[i] = 4 * np.sum(PQ[i][:, None] * (Y[i] - Y), axis=0)

        # 动量更新
        Y_new = Y - learning_rate * grad + momentum * (Y - Y_prev)
        Y_prev = Y.copy()
        Y = Y_new

        # 中心化，防止漂移
        Y = Y - np.mean(Y, axis=0)

        if (it + 1) % 100 == 0:
            kl = np.sum(P * np.log((P + 1e-10) / (Q + 1e-10)))
            print(f"      Iter {it+1}: KL = {kl:.4f}")

    return Y


# ============================================================
# 可视化
# ============================================================
def plot_tsne(Y, labels, class_names, colors, title, save_path):
    fig, ax = plt.subplots(figsize=(3.35, 2.8))
    for i, name in enumerate(class_names):
        mask = labels == i
        ax.scatter(Y[mask, 0], Y[mask, 1], c=colors[i], label=name,
                   s=6, alpha=0.7, edgecolors='none')
    ax.set_xlabel('t-SNE 1')
    ax.set_ylabel('t-SNE 2')
    ax.legend(frameon=False, fontsize=7, loc='best')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.tight_layout()
    plt.savefig(save_path, dpi=600, bbox_inches='tight')
    plt.close()
    print(f"  ✅ {save_path.name}")


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("t-SNE 特征可视化")
    print("=" * 60)

    # ---------- 声学模块 ----------
    print("\n[声学模块] 加载数据...")
    raw = np.load(DATA_DIR_EPFL / "D1_rawspace_5000.npy", mmap_mode='r')
    labels = np.load(DATA_DIR_EPFL / "D1_classspace_5000.npy")

    X, y = [], []
    for label in range(3):
        idx = np.where(labels == label)[0][:300]  # 每类取 300 个，共 900 个
        for i in idx:
            X.append(extract_features(raw[i], SR_EPFL))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    print(f"  特征矩阵: {X.shape}")

    # 标准化
    X_mean = np.mean(X, axis=0)
    X_std = np.std(X, axis=0) + 1e-10
    X_norm = (X - X_mean) / X_std

    print("\n  运行 t-SNE...")
    Y = tsne(X_norm, n_components=2, perplexity=30, learning_rate=200, n_iter=500)
    plot_tsne(Y, y, ["LoF", "Conduction", "Keyhole"],
              ['#888888', '#4472C4', '#C00000'],
              "Acoustic Module",
              OUTPUT_DIR / "fig_tsne_acoustic.png")

    # ---------- 激光超声模块 ----------
    print("\n[激光超声模块] 加载数据...")
    X_raw = np.load(DATA_DIR_LU / "X_lu.npy")
    y_raw = np.load(DATA_DIR_LU / "y_lu.npy")

    X, y = [], []
    for label in [0, 1]:
        idx = np.where(y_raw == label)[0][:500]  # 每类取 500 个，共 1000 个
        for i in idx:
            X.append(extract_features(X_raw[i], SR_LU))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    print(f"  特征矩阵: {X.shape}")

    X_mean = np.mean(X, axis=0)
    X_std = np.std(X, axis=0) + 1e-10
    X_norm = (X - X_mean) / X_std

    print("\n  运行 t-SNE...")
    Y = tsne(X_norm, n_components=2, perplexity=30, learning_rate=200, n_iter=500)
    plot_tsne(Y, y, ["Normal", "Defect"],
              ['#4472C4', '#C00000'],
              "Laser Ultrasound Module",
              OUTPUT_DIR / "fig_tsne_lu.png")

    print(f"\n{'=' * 60}")
    print(f"t-SNE 图已生成至: {OUTPUT_DIR}")
    print(f"  - fig_tsne_acoustic.png")
    print(f"  - fig_tsne_lu.png")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()