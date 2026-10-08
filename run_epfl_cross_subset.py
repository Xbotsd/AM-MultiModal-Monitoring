# -*- coding: utf-8 -*-
"""
EPFL 跨子集验证 D1-D4
调用口令：SCP111
运行: py -3.12 run_epfl_cross_subset.py
"""
import numpy as np
from pathlib import Path
from scipy.fft import rfft, rfftfreq
from scipy.stats import kurtosis as scipy_kurtosis, skew as scipy_skew
import json

DATA_DIR = Path("data/epfl_acoustic/Deciphering AE")
OUTPUT_DIR = Path("data/statistics")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
N_CLASSES = 3
MAX_PER_CLASS = 500
SR = 200000.0
DATASETS = ["D1", "D2", "D3", "D4"]


def fft_band_energies(signal, sr, n_bands=8):
    fft_vals = np.abs(rfft(signal))
    freqs = rfftfreq(len(signal), 1.0 / sr)
    psd = fft_vals ** 2
    total = np.sum(psd) + 1e-10
    band_edges = np.linspace(0, sr / 2, n_bands + 1)
    return [float(np.sum(psd[(freqs >= band_edges[i]) & (freqs < band_edges[i+1])]) / total)
            for i in range(n_bands)]


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
    band_energies = fft_band_energies(signal, sr, n_bands=8)
    return [kurt, skew_val, crest, centroid, bandwidth, spectral_entropy] + band_energies


class WeightedKNN:
    def __init__(self, k=9): self.k = k
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
            votes = np.zeros(N_CLASSES)
            for label, w in zip(self.y_train[k_idx], weights):
                votes[label] += w
            preds.append(np.argmax(votes))
        return np.array(preds)


class DeepMLP:
    def __init__(self, input_dim=14, h1=64, h2=32, lr=0.02, l2=1e-4):
        np.random.seed(42)
        self.W1 = np.random.randn(input_dim, h1) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, h1))
        self.W2 = np.random.randn(h1, h2) * np.sqrt(2.0 / h1)
        self.b2 = np.zeros((1, h2))
        self.W3 = np.random.randn(h2, N_CLASSES) * np.sqrt(2.0 / h2)
        self.b3 = np.zeros((1, N_CLASSES))
        self.lr = lr; self.l2 = l2
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
        self.W3 -= self.lr * dW3; self.b3 -= self.lr * db3
        self.W2 -= self.lr * dW2; self.b2 -= self.lr * db2
        self.W1 -= self.lr * dW1; self.b1 -= self.lr * db1
    def fit(self, X, y, epochs=2000):
        y_oh = np.zeros((len(y), N_CLASSES))
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


def load_dataset(name):
    raw_path = DATA_DIR / f"{name}_rawspace_5000.npy"
    cls_path = DATA_DIR / f"{name}_classspace_5000.npy"
    if not raw_path.exists():
        print(f"  [{name}] 文件不存在，跳过")
        return None, None
    raw = np.load(raw_path, mmap_mode='r')
    labels = np.load(cls_path)
    X, y = [], []
    for label in range(N_CLASSES):
        idx = np.where(labels == label)[0][:MAX_PER_CLASS]
        for i in idx:
            X.append(extract_features(raw[i]))
            y.append(label)
    return np.array(X), np.array(y)


def main():
    print("=" * 60)
    print("EPFL 跨子集验证 D1-D4")
    print("=" * 60)

    results = {}
    for dataset in DATASETS:
        print(f"\n[{dataset}] 加载数据...")
        X, y = load_dataset(dataset)
        if X is None:
            continue
        print(f"  特征矩阵: {X.shape}")

        np.random.seed(42)
        idx = np.random.permutation(len(X))
        split = int(len(X) * 0.8)
        tr, te = idx[:split], idx[split:]
        X_tr, X_te = X[tr], X[te]
        y_tr, y_te = y[tr], y[te]

        knn = WeightedKNN(k=9)
        knn.fit(X_tr, y_tr)
        knn_pred = knn.predict(X_te)

        X_mean = np.mean(X_tr, axis=0)
        X_std = np.std(X_tr, axis=0) + 1e-10
        X_tr_n = (X_tr - X_mean) / X_std
        X_te_n = (X_te - X_mean) / X_std
        mlp = DeepMLP(input_dim=14)
        mlp.fit(X_tr_n, y_tr, epochs=2000)
        mlp_proba = mlp.predict_proba(X_te_n)

        knn_proba = np.zeros((len(X_te), N_CLASSES))
        for i, p in enumerate(knn_pred):
            knn_proba[i, p] = 1.0
        ens_pred = np.argmax(0.3 * knn_proba + 0.7 * mlp_proba, axis=1)
        acc = np.mean(ens_pred == y_te)

        results[dataset] = {
            "accuracy": float(acc),
            "n_samples": len(X),
        }
        print(f"  准确率: {acc*100:.2f}%")

    print(f"\n{'=' * 60}")
    print(f"跨子集验证汇总")
    print(f"{'=' * 60}")
    print(f"{'数据集':<10s} {'样本数':>10s} {'准确率':>12s}")
    print("-" * 40)
    for d, r in results.items():
        print(f"{d:<10s} {r['n_samples']:>10d} {r['accuracy']*100:>11.2f}%")

    with open(OUTPUT_DIR / "cross_subset_epfl.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'cross_subset_epfl.json'}")


if __name__ == "__main__":
    main()