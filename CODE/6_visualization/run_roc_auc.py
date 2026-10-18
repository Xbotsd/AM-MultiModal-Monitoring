# -*- coding: utf-8 -*-
"""
ROC/AUC 计算 - NumPy 2.0 兼容版
调用口令：SCP111
运行: py -3.12 run_roc_auc.py
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

DATA_DIR_EPFL = Path("data/epfl_acoustic/Deciphering AE")
DATA_DIR_LU = Path("data/laser_ultrasound")
OUTPUT_DIR = Path("data/statistics")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SR_EPFL = 200000.0
SR_LU = 20000.0


def trapezoid(y, x):
    """兼容 NumPy 1.x (trapz) 和 2.x (trapezoid)"""
    if hasattr(np, "trapezoid"):
        return np.trapezoid(y, x)
    else:
        return np.trapz(y, x)


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


def compute_roc(y_true, y_score):
    """纯numpy实现ROC/AUC"""
    thresholds = np.sort(np.unique(y_score))[::-1]
    tpr_list, fpr_list = [], []
    P = np.sum(y_true == 1)
    N = np.sum(y_true == 0)
    for t in thresholds:
        y_pred = (y_score >= t).astype(int)
        tp = np.sum((y_pred == 1) & (y_true == 1))
        fp = np.sum((y_pred == 1) & (y_true == 0))
        tpr = tp / (P + 1e-10)
        fpr = fp / (N + 1e-10)
        tpr_list.append(tpr)
        fpr_list.append(fpr)
    fpr_arr = np.array(fpr_list)
    tpr_arr = np.array(tpr_list)
    order = np.argsort(fpr_arr)
    fpr_arr = fpr_arr[order]
    tpr_arr = tpr_arr[order]
    auc = trapezoid(tpr_arr, fpr_arr)
    return fpr_arr, tpr_arr, float(auc)


class SimpleMLP:
    def __init__(self, input_dim=14, h1=64, h2=32, output_dim=2, lr=0.02, l2=1e-4):
        np.random.seed(42)
        self.W1 = np.random.randn(input_dim, h1) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, h1))
        self.W2 = np.random.randn(h1, h2) * np.sqrt(2.0 / h1)
        self.b2 = np.zeros((1, h2))
        self.W3 = np.random.randn(h2, output_dim) * np.sqrt(2.0 / h2)
        self.b3 = np.zeros((1, output_dim))
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
        y_oh = np.zeros((len(y), 2))
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


def main():
    print("=" * 60)
    print("ROC / AUC 计算")
    print("=" * 60)

    # ---- 激光超声（二分类）----
    print("\n[激光超声] 加载数据...")
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

    X_mean = np.mean(X_tr, axis=0)
    X_std = np.std(X_tr, axis=0) + 1e-10
    X_tr_n = (X_tr - X_mean) / X_std
    X_te_n = (X_te - X_mean) / X_std

    mlp = SimpleMLP(input_dim=14)
    mlp.fit(X_tr_n, y_tr, epochs=2000)
    proba = mlp.predict_proba(X_te_n)
    y_score = proba[:, 1]

    fpr, tpr, auc = compute_roc(y_te, y_score)
    print(f"  激光超声 AUC = {auc:.4f}")

    # ---- 声学（三分类，One-vs-Rest）----
    print("\n[声学] 加载数据...")
    X_raw_e = np.load(DATA_DIR_EPFL / "D1_rawspace_5000.npy", mmap_mode='r')
    y_raw_e = np.load(DATA_DIR_EPFL / "D1_classspace_5000.npy")
    X_e, y_e = [], []
    for label in range(3):
        idx = np.where(y_raw_e == label)[0][:500]
        for i in idx:
            X_e.append(extract_features(X_raw_e[i], SR_EPFL))
            y_e.append(label)
    X_e = np.array(X_e)
    y_e = np.array(y_e)
    print(f"  特征矩阵: {X_e.shape}")

    np.random.seed(42)
    idx = np.random.permutation(len(X_e))
    split = int(len(X_e) * 0.8)
    tr, te = idx[:split], idx[split:]
    X_tr_e, X_te_e = X_e[tr], X_e[te]
    y_tr_e, y_te_e = y_e[tr], y_e[te]

    X_mean_e = np.mean(X_tr_e, axis=0)
    X_std_e = np.std(X_tr_e, axis=0) + 1e-10
    X_tr_en = (X_tr_e - X_mean_e) / X_std_e
    X_te_en = (X_te_e - X_mean_e) / X_std_e

    auc_results = {}
    names = ["LoF", "Conduction", "Keyhole"]
    for i, name in enumerate(names):
        y_bin = (y_tr_e == i).astype(int)
        mlp_i = SimpleMLP(input_dim=14, output_dim=2)
        mlp_i.fit(X_tr_en, y_bin, epochs=2000)
        proba_i = mlp_i.predict_proba(X_te_en)[:, 1]
        _, _, auc_i = compute_roc((y_te_e == i).astype(int), proba_i)
        auc_results[name] = float(auc_i)
        print(f"  {name} vs Rest: AUC = {auc_i:.4f}")

    macro_auc = np.mean(list(auc_results.values()))
    print(f"\n  宏平均 AUC = {macro_auc:.4f}")

    results = {
        "laser_ultrasound": {
            "auc": float(auc),
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
        },
        "acoustic": {
            "per_class": auc_results,
            "macro_auc": float(macro_auc),
        },
    }
    with open(OUTPUT_DIR / "roc_auc.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'roc_auc.json'}")


if __name__ == "__main__":
    main()