# -*- coding: utf-8 -*-
"""
混淆矩阵热力图
调用口令：SCP111
运行: py -3.12 run_confusion_matrix.py
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
N_CLASSES = 3


# ============================================================
# 特征提取（FFT频带版）
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
# KNN 分类器
# ============================================================
class WeightedKNN:
    def __init__(self, k=9, n_classes=3):
        self.k = k
        self.n_classes = n_classes
    def fit(self, X, y):
        self.X_mean = np.mean(X, axis=0)
        self.X_std = np.std(X, axis=0) + 1e-10
        self.X_train = (X - self.X_mean) / self.X_std
        self.y_train = np.array(y)
    def predict(self, X):
        X_test = (X - self.X_mean) / self.X_std
        preds = []
        for i in range(len(X_test)):
            d = np.sqrt(np.sum((self.X_train - X_test[i]) ** 2, axis=1))
            k_idx = np.argsort(d)[:self.k]
            weights = 1.0 / (d[k_idx] + 1e-6)
            votes = np.zeros(self.n_classes)
            for label, w in zip(self.y_train[k_idx], weights):
                votes[label] += w
            preds.append(np.argmax(votes))
        return np.array(preds)


# ============================================================
# MLP 分类器
# ============================================================
class DeepMLP:
    def __init__(self, input_dim=14, h1=64, h2=32, output_dim=3, lr=0.02, l2=1e-4):
        np.random.seed(42)
        self.W1 = np.random.randn(input_dim, h1) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, h1))
        self.W2 = np.random.randn(h1, h2) * np.sqrt(2.0 / h1)
        self.b2 = np.zeros((1, h2))
        self.W3 = np.random.randn(h2, output_dim) * np.sqrt(2.0 / h2)
        self.b3 = np.zeros((1, output_dim))
        self.lr = lr
        self.l2 = l2
    def relu(self, x): return np.maximum(0, x)
    def relu_deriv(self, x): return (x > 0).astype(float)
    def softmax(self, x):
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)
    def forward(self, X):
        self.z1 = X @ self.W1 + self.b1
        self.a1 = self.relu(self.z1)
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = self.relu(self.z2)
        self.z3 = self.a2 @ self.W3 + self.b3
        self.a3 = self.softmax(self.z3)
        return self.a3
    def backward(self, X, y_oh):
        m = X.shape[0]
        dz3 = self.a3 - y_oh
        dW3 = self.a2.T @ dz3 / m + self.l2 * self.W3
        db3 = np.sum(dz3, axis=0, keepdims=True) / m
        da2 = dz3 @ self.W3.T
        dz2 = da2 * self.relu_deriv(self.z2)
        dW2 = self.a1.T @ dz2 / m + self.l2 * self.W2
        db2 = np.sum(dz2, axis=0, keepdims=True) / m
        da1 = dz2 @ self.W2.T
        dz1 = da1 * self.relu_deriv(self.z1)
        dW1 = X.T @ dz1 / m + self.l2 * self.W1
        db1 = np.sum(dz1, axis=0, keepdims=True) / m
        self.W3 -= self.lr * dW3
        self.b3 -= self.lr * db3
        self.W2 -= self.lr * dW2
        self.b2 -= self.lr * db2
        self.W1 -= self.lr * dW1
        self.b1 -= self.lr * db1
    def fit(self, X, y, epochs=2000):
        y_oh = np.zeros((len(y), self.W3.shape[1]))
        for i, l in enumerate(y):
            y_oh[i, l] = 1.0
        for ep in range(epochs):
            pred = self.forward(X)
            loss = -np.mean(np.sum(y_oh * np.log(pred + 1e-10), axis=1))
            self.backward(X, y_oh)
            if (ep + 1) % 500 == 0:
                self.lr *= 0.7
    def predict_proba(self, X):
        return self.forward(X)


# ============================================================
# 混淆矩阵
# ============================================================
def confusion_matrix(y_true, y_pred, n_classes):
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm


def normalize_cm(cm):
    return cm / (cm.sum(axis=1, keepdims=True) + 1e-10)


def plot_cm(cm_norm, class_names, title, save_path):
    fig, ax = plt.subplots(figsize=(3.35, 2.8))
    im = ax.imshow(cm_norm, cmap='Blues', vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(class_names)))
    ax.set_yticks(np.arange(len(class_names)))
    ax.set_xticklabels(class_names)
    ax.set_yticklabels(class_names)
    ax.set_xlabel('Predicted', fontweight='bold')
    ax.set_ylabel('True', fontweight='bold')
    # 数值标注
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            val = cm_norm[i, j]
            color = 'white' if val > 0.5 else 'black'
            ax.text(j, i, f'{val:.3f}', ha='center', va='center',
                    fontsize=8, fontweight='bold', color=color)
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=7)
    plt.tight_layout()
    plt.savefig(save_path, dpi=600, bbox_inches='tight')
    plt.close()
    print(f"✅ {save_path.name}")


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("混淆矩阵热力图生成")
    print("=" * 60)

    # ---------- 声学模块 ----------
    print("\n[声学模块] 加载数据...")
    raw = np.load(DATA_DIR_EPFL / "D1_rawspace_5000.npy", mmap_mode='r')
    labels = np.load(DATA_DIR_EPFL / "D1_classspace_5000.npy")

    X, y = [], []
    for label in range(3):
        idx = np.where(labels == label)[0][:800]
        for i in idx:
            X.append(extract_features(raw[i], SR_EPFL))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    print(f"  特征矩阵: {X.shape}")

    np.random.seed(42)
    idx = np.random.permutation(len(X))
    split = int(len(X) * 0.8)
    tr, te = idx[:split], idx[split:]
    X_tr, X_te = X[tr], X[te]
    y_tr, y_te = y[tr], y[te]

    # KNN
    knn = WeightedKNN(k=9, n_classes=3)
    knn.fit(X_tr, y_tr)
    knn_pred = knn.predict(X_te)

    # MLP
    X_mean = np.mean(X_tr, axis=0)
    X_std = np.std(X_tr, axis=0) + 1e-10
    X_tr_n = (X_tr - X_mean) / X_std
    X_te_n = (X_te - X_mean) / X_std
    mlp = DeepMLP(input_dim=14, output_dim=3)
    mlp.fit(X_tr_n, y_tr, epochs=2000)
    mlp_proba = mlp.predict_proba(X_te_n)
    mlp_pred = np.argmax(mlp_proba, axis=1)

    # 加权集成
    knn_proba = np.zeros((len(X_te), 3))
    for i, p in enumerate(knn_pred):
        knn_proba[i, p] = 1.0
    ensemble_proba = 0.3 * knn_proba + 0.7 * mlp_proba
    ensemble_pred = np.argmax(ensemble_proba, axis=1)

    acc = np.mean(ensemble_pred == y_te)
    print(f"  集成准确率: {acc*100:.2f}%")

    # 混淆矩阵
    cm = confusion_matrix(y_te, ensemble_pred, 3)
    cm_norm = normalize_cm(cm)
    print(f"  混淆矩阵:\n{cm}")
    plot_cm(cm_norm, ["LoF", "Conduction", "Keyhole"],
            "Acoustic Module",
            OUTPUT_DIR / "fig_confusion_acoustic.png")

    # ---------- 激光超声模块 ----------
    print("\n[激光超声模块] 加载数据...")
    X_raw = np.load(DATA_DIR_LU / "X_lu.npy")
    y_raw = np.load(DATA_DIR_LU / "y_lu.npy")

    X, y = [], []
    for label in [0, 1]:
        idx = np.where(y_raw == label)[0][:800]
        for i in idx:
            X.append(extract_features(X_raw[i], SR_LU))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    print(f"  特征矩阵: {X.shape}")

    np.random.seed(42)
    idx = np.random.permutation(len(X))
    split = int(len(X) * 0.8)
    tr, te = idx[:split], idx[split:]
    X_tr, X_te = X[tr], X[te]
    y_tr, y_te = y[tr], y[te]

    knn = WeightedKNN(k=9, n_classes=2)
    knn.fit(X_tr, y_tr)
    knn_pred = knn.predict(X_te)

    X_mean = np.mean(X_tr, axis=0)
    X_std = np.std(X_tr, axis=0) + 1e-10
    X_tr_n = (X_tr - X_mean) / X_std
    X_te_n = (X_te - X_mean) / X_std
    mlp = DeepMLP(input_dim=14, output_dim=2)
    mlp.fit(X_tr_n, y_tr, epochs=2000)
    mlp_proba = mlp.predict_proba(X_te_n)
    mlp_pred = np.argmax(mlp_proba, axis=1)

    knn_proba = np.zeros((len(X_te), 2))
    for i, p in enumerate(knn_pred):
        knn_proba[i, p] = 1.0
    ensemble_proba = 0.3 * knn_proba + 0.7 * mlp_proba
    ensemble_pred = np.argmax(ensemble_proba, axis=1)

    acc = np.mean(ensemble_pred == y_te)
    print(f"  集成准确率: {acc*100:.2f}%")

    cm = confusion_matrix(y_te, ensemble_pred, 2)
    cm_norm = normalize_cm(cm)
    print(f"  混淆矩阵:\n{cm}")
    plot_cm(cm_norm, ["Normal", "Defect"],
            "Laser Ultrasound Module",
            OUTPUT_DIR / "fig_confusion_lu.png")

    print(f"\n{'=' * 60}")
    print(f"混淆矩阵已生成至: {OUTPUT_DIR}")
    print(f"  - fig_confusion_acoustic.png")
    print(f"  - fig_confusion_lu.png")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()