# -*- coding: utf-8 -*-
"""
V12 - 集成学习 (KNN + MLP 软投票)
结合 V8 的加权KNN和 V10 的深层MLP，突破单模型瓶颈
运行: py -3.12 run_epfl_v12.py
"""
import numpy as np
import pywt
from pathlib import Path
from scipy.fft import rfft, rfftfreq
from scipy.stats import kurtosis as scipy_kurtosis, skew as scipy_skew
from collections import Counter

DATA_DIR = Path("data/epfl_acoustic/Deciphering AE")
DATASET = "D1"
MAX_PER_CLASS = 800

def extract_extended_features(signal, sr=200000):
    signal = np.asarray(signal, dtype=np.float64)
    if signal.ndim > 1:
        signal = signal.mean(axis=1)

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


# ============================================================
# 加权KNN（V8）
# ============================================================
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
        probs = np.zeros((len(X_test), 3))
        for i in range(len(X_test)):
            distances = np.sqrt(np.sum((self.X_train - X_test[i]) ** 2, axis=1))
            k_indices = np.argsort(distances)[:self.k]
            k_distances = distances[k_indices]
            k_labels = self.y_train[k_indices]
            weights = 1.0 / (k_distances + 1e-6)
            for label, w in zip(k_labels, weights):
                probs[i, label] += w
        probs = probs / (probs.sum(axis=1, keepdims=True) + 1e-10)
        return probs


# ============================================================
# 深层MLP（V10）
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
        exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)

    def forward(self, X):
        self.z1 = X @ self.W1 + self.b1
        self.a1 = self.relu(self.z1)
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = self.relu(self.z2)
        self.z3 = self.a2 @ self.W3 + self.b3
        self.a3 = self.softmax(self.z3)
        return self.a3

    def backward(self, X, y_onehot):
        m = X.shape[0]
        dz3 = self.a3 - y_onehot
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
        y_onehot = np.zeros((len(y), 3))
        for i, label in enumerate(y):
            y_onehot[i, label] = 1.0
        for epoch in range(epochs):
            pred = self.forward(X)
            loss = -np.mean(np.sum(y_onehot * np.log(pred + 1e-10), axis=1))
            self.backward(X, y_onehot)
            if (epoch + 1) % 500 == 0:
                acc = np.mean(np.argmax(pred, axis=1) == y)
                print(f"  Epoch {epoch+1:4d}: loss={loss:.4f}, train_acc={acc*100:.2f}%")
                self.lr *= 0.7

    def predict_proba(self, X):
        return self.forward(X)


# ============================================================
# 主流程：集成
# ============================================================
def main():
    print("=" * 60)
    print("V12 集成学习 (加权KNN + 深层MLP)")
    print("=" * 60)

    raw = np.load(DATA_DIR / f"{DATASET}_rawspace_5000.npy", mmap_mode='r')
    labels = np.load(DATA_DIR / f"{DATASET}_classspace_5000.npy")

    label_names = {0: "LoF", 1: "Conduction", 2: "Keyhole"}
    X, y = [], []

    for label_id in [0, 1, 2]:
        idx_all = np.where(labels == label_id)[0][:MAX_PER_CLASS]
        print(f"提取 {label_names[label_id]} 特征... ({len(idx_all)} 个)")
        for idx in idx_all:
            X.append(extract_extended_features(raw[idx]))
            y.append(label_id)

    X = np.array(X)
    y = np.array(y)

    np.random.seed(42)
    indices = np.random.permutation(len(X))
    split_idx = int(len(X) * 0.8)
    train_idx, test_idx = indices[:split_idx], indices[split_idx:]
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # ---- 模型1: 加权KNN ----
    print("\n[模型1] 加权KNN (k=9)")
    knn = WeightedKNN(k=9)
    knn.fit(X_train, y_train)
    knn_proba = knn.predict_proba(X_test)
    knn_acc = np.mean(np.argmax(knn_proba, axis=1) == y_test)
    print(f"  KNN 准确率: {knn_acc * 100:.2f}%")

    # ---- 模型2: 深层MLP ----
    print("\n[模型2] 深层MLP")
    X_mean = np.mean(X_train, axis=0)
    X_std = np.std(X_train, axis=0) + 1e-10
    X_train_norm = (X_train - X_mean) / X_std
    X_test_norm = (X_test - X_mean) / X_std
    mlp = DeepMLP(input_dim=14, h1=64, h2=32, output_dim=3, lr=0.02, l2=1e-4)
    mlp.fit(X_train_norm, y_train, epochs=2000)
    mlp_proba = mlp.predict_proba(X_test_norm)
    mlp_acc = np.mean(np.argmax(mlp_proba, axis=1) == y_test)
    print(f"  MLP 准确率: {mlp_acc * 100:.2f}%")

    # ---- 集成：软投票 ----
    print("\n[集成] KNN + MLP 软投票")
    ensemble_proba = 0.5 * knn_proba + 0.5 * mlp_proba
    ensemble_pred = np.argmax(ensemble_proba, axis=1)
    ensemble_acc = np.mean(ensemble_pred == y_test)

    print(f"\n{'=' * 60}")
    print(f"🎯 V12 集成准确率: {ensemble_acc * 100:.2f}%")
    print(f"    (KNN: {knn_acc*100:.2f}%, MLP: {mlp_acc*100:.2f}%)")
    print(f"{'=' * 60}")

    print("\n混淆矩阵:")
    cm = np.zeros((3, 3), dtype=int)
    for true, pred in zip(y_test, ensemble_pred):
        cm[true][pred] += 1

    print(f"{'':12s} {'LoF':>8s} {'Cond':>8s} {'Keyhole':>8s}")
    for i, name in enumerate(["LoF", "Conduction", "Keyhole"]):
        print(f"{name:12s} {cm[i][0]:>8d} {cm[i][1]:>8d} {cm[i][2]:>8d}")

    print("\n每类准确率:")
    for i, name in enumerate(["LoF", "Conduction", "Keyhole"]):
        total = np.sum(y_test == i)
        correct = cm[i][i]
        print(f"  {name:12s}: {correct}/{total} = {correct/total*100:.1f}%")


if __name__ == "__main__":
    main()