# -*- coding: utf-8 -*-
"""
激光超声分类 - 仿照声学V12框架
运行: py -3.12 run_lu_v2.py
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

DATA_DIR = Path("data/laser_ultrasound")
N_CLASSES = 2
MAX_SAMPLES = 800
SR = 20000.0

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

class WeightedKNN:
    def __init__(self, k=9):
        self.k = k
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
    def __init__(self, input_dim=14, h1=64, h2=32, output_dim=N_CLASSES, lr=0.02, l2=1e-4):
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
        y_oh = np.zeros((len(y), N_CLASSES))
        for i, l in enumerate(y):
            y_oh[i, l] = 1.0
        for ep in range(epochs):
            pred = self.forward(X)
            loss = -np.mean(np.sum(y_oh * np.log(pred + 1e-10), axis=1))
            self.backward(X, y_oh)
            if (ep + 1) % 500 == 0:
                acc = np.mean(np.argmax(pred, axis=1) == y)
                print(f"  Epoch {ep+1:4d}: loss={loss:.4f}, train_acc={acc*100:.2f}%")
                self.lr *= 0.7
    def predict_proba(self, X):
        return self.forward(X)

def main():
    print("=" * 60)
    print("激光超声分类 - 仿照声学V12框架")
    print("=" * 60)
    X_raw = np.load(DATA_DIR / "X_lu.npy")
    y_raw = np.load(DATA_DIR / "y_lu.npy")
    print(f"加载数据: X={X_raw.shape}, y={y_raw.shape}")

    X, y = [], []
    for label in range(N_CLASSES):
        idx = np.where(y_raw == label)[0][:MAX_SAMPLES]
        print(f"  类别 {label}: {len(idx)} 个样本")
        for i in idx:
            X.append(extract_features(X_raw[i]))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    print(f"特征矩阵: {X.shape}")

    np.random.seed(42)
    idx = np.random.permutation(len(X))
    split = int(len(X) * 0.8)
    tr, te = idx[:split], idx[split:]
    X_tr, X_te = X[tr], X[te]
    y_tr, y_te = y[tr], y[te]

    print("\n[模型1] 加权KNN (k=9)")
    knn = WeightedKNN(k=9)
    knn.fit(X_tr, y_tr)
    knn_proba = knn.predict_proba(X_te)
    knn_acc = np.mean(np.argmax(knn_proba, axis=1) == y_te)
    print(f"  KNN 准确率: {knn_acc*100:.2f}%")

    print("\n[模型2] 深层MLP")
    X_mean = np.mean(X_tr, axis=0)
    X_std = np.std(X_tr, axis=0) + 1e-10
    X_tr_n = (X_tr - X_mean) / X_std
    X_te_n = (X_te - X_mean) / X_std
    mlp = DeepMLP(input_dim=14, output_dim=N_CLASSES)
    mlp.fit(X_tr_n, y_tr, epochs=2000)
    mlp_proba = mlp.predict_proba(X_te_n)
    mlp_acc = np.mean(np.argmax(mlp_proba, axis=1) == y_te)
    print(f"  MLP 准确率: {mlp_acc*100:.2f}%")

    print("\n[集成] KNN + MLP 软投票")
    ens_proba = 0.5 * knn_proba + 0.5 * mlp_proba
    ens_pred = np.argmax(ens_proba, axis=1)
    ens_acc = np.mean(ens_pred == y_te)
    print(f"\n{'=' * 60}")
    print(f"🎯 激光超声集成准确率: {ens_acc*100:.2f}%")
    print(f"{'=' * 60}")

    cm = np.zeros((N_CLASSES, N_CLASSES), dtype=int)
    for t, p in zip(y_te, ens_pred):
        cm[t][p] += 1
    print("\n混淆矩阵:")
    print(f"{'':>6s}" + "".join([f"{i:>8d}" for i in range(N_CLASSES)]))
    for i in range(N_CLASSES):
        print(f"{i:>5d} " + "".join([f"{cm[i][j]:>8d}" for j in range(N_CLASSES)]))

if __name__ == "__main__":
    main()