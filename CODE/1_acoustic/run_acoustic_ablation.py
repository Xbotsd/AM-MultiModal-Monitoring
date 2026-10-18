# -*- coding: utf-8 -*-
"""
声学模块消融实验 - FFT频带版（无pywt依赖）
调用口令：SCP111
运行: py -3.12 run_acoustic_ablation.py
"""
# --- AUTO INJECTED PATH FIX ---
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT_DIR)
# ------------------------------

import numpy as np
from pathlib import Path
from scipy.fft import rfft, rfftfreq
from scipy.stats import kurtosis as scipy_kurtosis, skew as scipy_skew
import json

DATA_DIR = Path("data/epfl_acoustic/Deciphering AE")
OUTPUT_DIR = Path("data/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATASET = "D1"
N_CLASSES = 3
MAX_PER_CLASS = 800
SR = 200000.0


def fft_band_energies(signal, sr, n_bands=8):
    """FFT频谱等分频段能量，替代小波包"""
    fft_vals = np.abs(rfft(signal))
    freqs = rfftfreq(len(signal), 1.0 / sr)
    psd = fft_vals ** 2
    total = np.sum(psd) + 1e-10
    band_edges = np.linspace(0, sr / 2, n_bands + 1)
    band_energies = []
    for i in range(n_bands):
        mask = (freqs >= band_edges[i]) & (freqs < band_edges[i+1])
        band_energies.append(float(np.sum(psd[mask]) / total))
    return band_energies


def extract_features(signal, sr=SR, feature_set="full"):
    """可配置特征提取（14维）"""
    signal = np.asarray(signal, dtype=np.float64).flatten()
    if len(signal) < 16:
        return [0.0] * 14

    # 时域特征
    kurt = float(scipy_kurtosis(signal))
    skew_val = float(scipy_skew(signal))
    rms = float(np.sqrt(np.mean(signal ** 2)))
    peak = float(np.max(np.abs(signal)))
    crest = peak / (rms + 1e-10)

    # 频域特征
    fft_vals = np.abs(rfft(signal))
    freqs = rfftfreq(len(signal), 1.0 / sr)
    psd = fft_vals ** 2
    total_energy = np.sum(psd) + 1e-10
    centroid = float(np.sum(freqs * psd) / total_energy)
    bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * psd) / total_energy))
    psd_norm = psd / total_energy
    psd_norm = psd_norm[psd_norm > 0]
    spectral_entropy = float(-np.sum(psd_norm * np.log2(psd_norm + 1e-10)))

    # 频带能量
    band_energies = fft_band_energies(signal, sr, n_bands=8)

    if feature_set == "full":
        return [kurt, skew_val, crest, centroid, bandwidth, spectral_entropy] + band_energies
    elif feature_set == "no_band":
        return [kurt, skew_val, crest, centroid, bandwidth, spectral_entropy]
    elif feature_set == "no_spectral":
        return [kurt, skew_val, crest] + band_energies
    elif feature_set == "no_time":
        return [centroid, bandwidth, spectral_entropy] + band_energies
    else:
        return [kurt, skew_val, crest, centroid, bandwidth, spectral_entropy] + band_energies


class WeightedKNN:
    def __init__(self, k=9): self.k = k
    def fit(self, X, y):
        self.X_mean = np.mean(X, axis=0)
        self.X_std = np.std(X, axis=0) + 1e-10
        self.X_train = (X - self.X_mean) / self.X_std
        self.y_train = np.array(y)
    def predict_proba(self, X):
        X_test = (X - self.X_mean) / self.X_std
        probs = np.zeros((len(X_test), N_CLASSES))
        for i in range(len(X_test)):
            d = np.sqrt(np.sum((self.X_train - X_test[i]) ** 2, axis=1))
            k_idx = np.argsort(d)[:self.k]
            weights = 1.0 / (d[k_idx] + 1e-6)
            for label, w in zip(self.y_train[k_idx], weights):
                probs[i, label] += w
        probs = probs / (probs.sum(axis=1, keepdims=True) + 1e-10)
        return probs


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


def run_experiment(feature_set, classifier_type, X_raw, y_raw):
    X, y = [], []
    for label in range(N_CLASSES):
        idx = np.where(y_raw == label)[0][:MAX_PER_CLASS]
        for i in idx:
            X.append(extract_features(X_raw[i], feature_set=feature_set))
            y.append(label)
    X = np.array(X)
    y = np.array(y)

    np.random.seed(42)
    idx = np.random.permutation(len(X))
    split = int(len(X) * 0.8)
    tr, te = idx[:split], idx[split:]
    X_tr, X_te = X[tr], X[te]
    y_tr, y_te = y[tr], y[te]

    results = {}
    if classifier_type in ("knn", "both"):
        knn = WeightedKNN(k=9)
        knn.fit(X_tr, y_tr)
        knn_proba = knn.predict_proba(X_te)
        results["knn"] = np.mean(np.argmax(knn_proba, axis=1) == y_te)
    if classifier_type in ("mlp", "both"):
        X_mean = np.mean(X_tr, axis=0)
        X_std = np.std(X_tr, axis=0) + 1e-10
        X_tr_n = (X_tr - X_mean) / X_std
        X_te_n = (X_te - X_mean) / X_std
        mlp = DeepMLP(input_dim=X.shape[1])
        mlp.fit(X_tr_n, y_tr, epochs=2000)
        mlp_proba = mlp.predict_proba(X_te_n)
        results["mlp"] = np.mean(np.argmax(mlp_proba, axis=1) == y_te)
    if classifier_type == "both":
        results["ensemble"] = (results.get("knn", 0) + results.get("mlp", 0)) / 2
    return results


def main():
    print("=" * 60)
    print("声学模块消融实验 - FFT频带版")
    print("=" * 60)

    raw = np.load(DATA_DIR / f"{DATASET}_rawspace_5000.npy", mmap_mode='r')
    labels = np.load(DATA_DIR / f"{DATASET}_classspace_5000.npy")

    experiments = [
        ("完整系统 (14维)", "full", "both"),
        ("去掉频带特征 (6维)", "no_band", "both"),
        ("去掉频域特征 (8维)", "no_spectral", "both"),
        ("去掉时域特征 (8维)", "no_time", "both"),
        ("只用KNN (14维)", "full", "knn"),
        ("只用MLP (14维)", "full", "mlp"),
    ]

    print(f"\n{'配置':<25s} {'KNN':>10s} {'MLP':>10s} {'集成':>10s}")
    print("-" * 60)

    results_all = {}
    for name, feat, clf in experiments:
        r = run_experiment(feat, clf, raw, labels)
        knn_s = f"{r['knn']*100:.2f}%" if 'knn' in r else "—"
        mlp_s = f"{r['mlp']*100:.2f}%" if 'mlp' in r else "—"
        ens_s = f"{r['ensemble']*100:.2f}%" if 'ensemble' in r else "—"
        print(f"{name:<25s} {knn_s:>10s} {mlp_s:>10s} {ens_s:>10s}")
        results_all[name] = {
            "knn": float(r.get("knn", 0)),
            "mlp": float(r.get("mlp", 0)),
            "ensemble": float(r.get("ensemble", 0)),
        }

    with open(OUTPUT_DIR / "acoustic_ablation.json", "w", encoding="utf-8") as f:
        json.dump(results_all, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'acoustic_ablation.json'}")


if __name__ == "__main__":
    main()