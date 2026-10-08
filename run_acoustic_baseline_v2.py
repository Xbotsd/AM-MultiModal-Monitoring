# -*- coding: utf-8 -*-
"""
声学分类基线对比实验（修复版）
调用口令：SCP111
运行: py -3.12 run_acoustic_baseline.py
"""
import numpy as np
import pywt
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


class SoftmaxRegression:
    def __init__(self, lr=0.1, epochs=1000, l2=1e-3):
        self.lr = lr
        self.epochs = epochs
        self.l2 = l2

    def fit(self, X, y):
        X_mean = np.mean(X, axis=0)
        X_std = np.std(X, axis=0) + 1e-10
        X = (X - X_mean) / X_std
        self.X_mean = X_mean
        self.X_std = X_std
        n, d = X.shape
        self.W = np.random.randn(d, N_CLASSES) * 0.01
        self.b = np.zeros(N_CLASSES)
        y_oh = np.zeros((n, N_CLASSES))
        for i, l in enumerate(y):
            y_oh[i, l] = 1.0
        for ep in range(self.epochs):
            z = X @ self.W + self.b
            z = z - np.max(z, axis=1, keepdims=True)
            p = np.exp(z) / np.sum(np.exp(z), axis=1, keepdims=True)
            grad_W = X.T @ (p - y_oh) / n + self.l2 * self.W
            grad_b = np.sum(p - y_oh, axis=0) / n
            self.W -= self.lr * grad_W
            self.b -= self.lr * grad_b

    def predict(self, X):
        X = (X - self.X_mean) / self.X_std
        z = X @ self.W + self.b
        return np.argmax(z, axis=1)


class GaussianNB:
    def fit(self, X, y):
        self.classes = np.unique(y)
        self.means = {}
        self.vars = {}
        self.priors = {}
        for c in self.classes:
            Xc = X[y == c]
            self.means[c] = np.mean(Xc, axis=0)
            self.vars[c] = np.var(Xc, axis=0) + 1e-6
            self.priors[c] = len(Xc) / len(X)

    def predict(self, X):
        n = X.shape[0]
        log_probs = np.zeros((n, len(self.classes)))
        for i, c in enumerate(self.classes):
            mean = self.means[c]
            var = self.vars[c]
            log_likelihood = -0.5 * np.sum(np.log(2 * np.pi * var), axis=0) \
                             - 0.5 * np.sum((X - mean) ** 2 / var, axis=1)
            log_probs[:, i] = log_likelihood + np.log(self.priors[c])
        return self.classes[np.argmax(log_probs, axis=1)]


class DecisionStumpEnsemble:
    def __init__(self, n_stumps=50):
        self.n_stumps = n_stumps
        self.stumps = []

    def fit(self, X, y):
        n, d = X.shape
        np.random.seed(42)
        for _ in range(self.n_stumps):
            feat = np.random.randint(0, d)
            thresh = np.random.uniform(X[:, feat].min(), X[:, feat].max())
            left_mask = X[:, feat] < thresh
            if np.sum(left_mask) == 0 or np.sum(~left_mask) == 0:
                continue
            left_label = np.bincount(y[left_mask], minlength=N_CLASSES).argmax()
            right_label = np.bincount(y[~left_mask], minlength=N_CLASSES).argmax()
            self.stumps.append((feat, thresh, left_label, right_label))

    def predict(self, X):
        n = X.shape[0]
        votes = np.zeros((n, N_CLASSES))
        for feat, thresh, left_label, right_label in self.stumps:
            left_mask = X[:, feat] < thresh
            votes[left_mask, left_label] += 1
            votes[~left_mask, right_label] += 1
        return np.argmax(votes, axis=1)


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
    def __init__(self, input_dim=14, h1=64, h2=32, lr=0.02, l2=1e-4):
        np.random.seed(42)
        self.W1 = np.random.randn(input_dim, h1) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, h1))
        self.W2 = np.random.randn(h1, h2) * np.sqrt(2.0 / h1)
        self.b2 = np.zeros((1, h2))
        self.W3 = np.random.randn(h2, N_CLASSES) * np.sqrt(2.0 / h2)
        self.b3 = np.zeros((1, N_CLASSES))
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
                self.lr *= 0.7
    def predict_proba(self, X):
        return self.forward(X)


def main():
    print("=" * 60)
    print("声学分类基线对比实验（修复版）")
    print("=" * 60)

    raw = np.load(DATA_DIR / f"{DATASET}_rawspace_5000.npy", mmap_mode='r')
    labels = np.load(DATA_DIR / f"{DATASET}_classspace_5000.npy")

    print("\n提取特征...")
    X, y = [], []
    for label in range(N_CLASSES):
        idx = np.where(labels == label)[0][:MAX_PER_CLASS]
        for i in idx:
            X.append(extract_features(raw[i]))
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

    results = {}

    print("\n[Baseline 1] Softmax回归...")
    lr = SoftmaxRegression(lr=0.1, epochs=1000)
    lr.fit(X_tr, y_tr)
    acc_lr = np.mean(lr.predict(X_te) == y_te)
    print(f"    准确率: {acc_lr*100:.2f}%")
    results["Softmax Regression"] = float(acc_lr)

    print("[Baseline 2] 高斯朴素贝叶斯...")
    nb = GaussianNB()
    nb.fit(X_tr, y_tr)
    acc_nb = np.mean(nb.predict(X_te) == y_te)
    print(f"    准确率: {acc_nb*100:.2f}%")
    results["Gaussian Naive Bayes"] = float(acc_nb)

    print("[Baseline 3] 决策树桩集成 (50 stumps)...")
    ds = DecisionStumpEnsemble(n_stumps=50)
    ds.fit(X_tr, y_tr)
    acc_ds = np.mean(ds.predict(X_te) == y_te)
    print(f"    准确率: {acc_ds*100:.2f}%")
    results["Decision Stump Ensemble"] = float(acc_ds)

    print("[Proposed] KNN + MLP 集成（加权投票）...")
    knn = WeightedKNN(k=9)
    knn.fit(X_tr, y_tr)
    knn_proba = knn.predict_proba(X_te)
    knn_pred = np.argmax(knn_proba, axis=1)
    knn_acc = np.mean(knn_pred == y_te)

    X_mean = np.mean(X_tr, axis=0)
    X_std = np.std(X_tr, axis=0) + 1e-10
    X_tr_n = (X_tr - X_mean) / X_std
    X_te_n = (X_te - X_mean) / X_std
    mlp = DeepMLP(input_dim=14)
    mlp.fit(X_tr_n, y_tr, epochs=2000)
    mlp_proba = mlp.predict_proba(X_te_n)
    mlp_pred = np.argmax(mlp_proba, axis=1)
    mlp_acc = np.mean(mlp_pred == y_te)

    # 加权投票：MLP 权重 0.7，KNN 权重 0.3
    ensemble_proba = 0.3 * knn_proba + 0.7 * mlp_proba
    ensemble_pred = np.argmax(ensemble_proba, axis=1)
    acc_proposed = np.mean(ensemble_pred == y_te)

    print(f"    KNN: {knn_acc*100:.2f}%, MLP: {mlp_acc*100:.2f}%, Ensemble: {acc_proposed*100:.2f}%")
    results["KNN only"] = float(knn_acc)
    results["MLP only"] = float(mlp_acc)
    results["Proposed (KNN + MLP, weighted)"] = float(acc_proposed)

    print(f"\n{'=' * 60}")
    print(f"性能对比结果")
    print(f"{'=' * 60}")
    print(f"{'方法':<36s} {'准确率':>12s}")
    print("-" * 50)
    for name, acc in results.items():
        print(f"{name:<36s} {acc*100:>11.2f}%")

    with open(OUTPUT_DIR / "acoustic_baseline_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'acoustic_baseline_results.json'}")


if __name__ == "__main__":
    main()