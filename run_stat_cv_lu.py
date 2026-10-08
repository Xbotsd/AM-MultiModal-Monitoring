# -*- coding: utf-8 -*-
"""
激光超声 K折交叉验证 - 去除pywt依赖版
调用口令：SCP111
运行: py -3.12 run_stat_cv_lu.py
"""
import numpy as np
from pathlib import Path
from scipy.fft import rfft, rfftfreq
from scipy.stats import kurtosis as scipy_kurtosis, skew as scipy_skew
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import precision_recall_fscore_support
import json

DATA_DIR = Path("data/laser_ultrasound")
OUTPUT_DIR = Path("data/statistics")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
N_CLASSES = 2
MAX_SAMPLES = 800
SR = 20000.0
N_FOLDS = 5


def fft_band_energies(signal, sr, n_bands=8):
    fft_vals = np.abs(rfft(signal))
    freqs = rfftfreq(len(signal), 1.0 / sr)
    psd = fft_vals ** 2
    total = np.sum(psd) + 1e-10
    band_edges = np.linspace(0, sr / 2, n_bands + 1)
    band_energies = []
    for i in range(n_bands):
        mask = (freqs >= band_edges[i]) & (freqs < band_edges[i+1])
        band_energies.append(np.sum(psd[mask]) / total)
    return band_energies


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


def main():
    print("=" * 60)
    print(f"激光超声 {N_FOLDS}折交叉验证 (FFT频带版)")
    print("=" * 60)

    X_raw = np.load(DATA_DIR / "X_lu.npy")
    y_raw = np.load(DATA_DIR / "y_lu.npy")

    X, y = [], []
    for label in range(N_CLASSES):
        idx = np.where(y_raw == label)[0][:MAX_SAMPLES]
        for i in idx:
            X.append(extract_features(X_raw[i]))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    print(f"特征矩阵: {X.shape}")

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
    fold_accs = []
    all_y_true, all_y_pred = [], []

    for fold, (tr, te) in enumerate(skf.split(X, y)):
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
        fold_accs.append(acc)
        all_y_true.extend(y_te)
        all_y_pred.extend(ens_pred)
        print(f"  Fold {fold+1}: 准确率 = {acc*100:.2f}%")

    fold_accs = np.array(fold_accs)
    mean_acc = np.mean(fold_accs)
    std_acc = np.std(fold_accs, ddof=1)
    print(f"\n{'=' * 60}")
    print(f"K折交叉验证结果: {mean_acc*100:.2f}% ± {std_acc*100:.2f}%")
    print(f"{'=' * 60}")

    p, r, f1, _ = precision_recall_fscore_support(
        all_y_true, all_y_pred, labels=[0, 1], average=None
    )
    print("\n每类精确率/召回率/F1:")
    names = ["Normal", "Defect"]
    for i, name in enumerate(names):
        print(f"  {name}: P={p[i]*100:.2f}%, R={r[i]*100:.2f}%, F1={f1[i]*100:.2f}%")

    results = {
        "k_folds": N_FOLDS,
        "fold_accuracies": [float(a) for a in fold_accs],
        "mean_accuracy": float(mean_acc),
        "std_accuracy": float(std_acc),
        "per_class": {
            names[i]: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f1[i])}
            for i in range(N_CLASSES)
        },
    }
    with open(OUTPUT_DIR / "cv_laser_ultrasound.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'cv_laser_ultrasound.json'}")


if __name__ == "__main__":
    main()