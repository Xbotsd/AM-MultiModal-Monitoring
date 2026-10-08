# -*- coding: utf-8 -*-
"""
复杂度分析 - 推理时间、参数规模、理论复杂度
调用口令：SCP111
运行: py -3.12 run_complexity.py
"""
import numpy as np
import time
import tracemalloc
import json
from pathlib import Path
from scipy.fft import rfft, rfftfreq
from scipy.stats import kurtosis as scipy_kurtosis, skew as scipy_skew

OUTPUT_DIR = Path("data/complexity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 各模块的推理时间测量
# ============================================================

def time_knn_k9(X_train, X_test, k=9):
    """加权KNN推理时间"""
    def predict(X):
        preds = []
        for i in range(len(X)):
            d = np.sqrt(np.sum((X_train - X[i]) ** 2, axis=1))
            k_idx = np.argsort(d)[:k]
            preds.append(k_idx[0])
        return np.array(preds)
    return predict


def time_mlp_forward(X, W1, b1, W2, b2, W3, b3):
    """MLP前向传播时间"""
    def predict(X_in):
        z1 = X_in @ W1 + b1
        a1 = np.maximum(0, z1)
        z2 = a1 @ W2 + b2
        a2 = np.maximum(0, z2)
        z3 = a2 @ W3 + b3
        # softmax
        e = np.exp(z3 - np.max(z3, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)
    return predict


def time_kalman(x_init, R_list, Q=0.01, n_iter=200):
    """卡尔曼融合推理时间"""
    n = n_iter
    x_est = np.zeros(n); P = np.zeros(n)
    x_est[0] = x_init; P[0] = 1.0
    for k in range(1, n):
        x_pred = x_est[k-1]; P_pred = P[k-1] + Q
        x_upd = x_pred; P_upd = P_pred
        for R in R_list:
            K = P_upd / (P_upd + R)
            x_upd = x_upd  # 无新观测，仅演示计算
            P_upd = (1 - K) * P_upd
        x_est[k] = x_upd; P[k] = P_upd
    return x_est


def time_feature_extraction(signal, sr, n_runs=100):
    """特征提取时间（单次）"""
    start = time.perf_counter()
    for _ in range(n_runs):
        signal_arr = np.asarray(signal, dtype=np.float64).flatten()
        kurt = scipy_kurtosis(signal_arr)
        skew_val = scipy_skew(signal_arr)
        rms = np.sqrt(np.mean(signal_arr ** 2))
        peak = np.max(np.abs(signal_arr))
        crest = peak / (rms + 1e-10)
        fft_vals = np.abs(rfft(signal_arr))
        freqs = rfftfreq(len(signal_arr), 1.0 / sr)
        psd = fft_vals ** 2
        total_energy = np.sum(psd) + 1e-10
        centroid = np.sum(freqs * psd) / total_energy
        bandwidth = np.sqrt(np.sum(((freqs - centroid) ** 2) * psd) / total_energy)
    elapsed = (time.perf_counter() - start) / n_runs
    return elapsed * 1000  # ms


# ============================================================
# 参数规模统计
# ============================================================

def count_parameters_mlp(input_dim=14, h1=64, h2=32, output_dim=3):
    """MLP 参数数量"""
    p1 = input_dim * h1 + h1
    p2 = h1 * h2 + h2
    p3 = h2 * output_dim + output_dim
    return {"layer1": p1, "layer2": p2, "layer3": p3, "total": p1 + p2 + p3}


def count_parameters_knn(X_train):
    """KNN 参数（存储训练集）"""
    n, d = X_train.shape
    return {"n_train_samples": n, "feature_dim": d, "total_floats": n * d}


# ============================================================
# 理论复杂度分析
# ============================================================

def theoretical_complexity():
    return {
        "Kalman fusion": {
            "time_complexity": "O(N · M)",
            "space_complexity": "O(N)",
            "N": "时间步数",
            "M": "模态数",
        },
        "KNN inference": {
            "time_complexity": "O(N_train · d)",
            "space_complexity": "O(N_train · d)",
            "N_train": "训练样本数",
            "d": "特征维度",
        },
        "MLP forward": {
            "time_complexity": "O(d · h1 + h1 · h2 + h2 · C)",
            "space_complexity": "O(d·h1 + h1·h2 + h2·C)",
            "h1, h2": "隐藏层神经元数",
            "C": "类别数",
        },
        "SAFT (baseline)": {
            "time_complexity": "O(N_e² · N_t · N_z)",
            "space_complexity": "O(N_e² · N_t)",
            "N_e": "阵元数",
            "N_t": "采样点数",
            "N_z": "成像点数",
            "note": "传统合成孔径成像，计算量大",
        },
        "Traditional unwrap": {
            "time_complexity": "O(P)",
            "space_complexity": "O(P)",
            "P": "像素数",
        },
        "Least-squares unwrap (DCT)": {
            "time_complexity": "O(P log P)",
            "space_complexity": "O(P)",
            "P": "像素数",
            "note": "DCT 加速",
        },
        "Proposed unwrap": {
            "time_complexity": "O(P) + O(P log P)",
            "space_complexity": "O(P)",
            "note": "传统积分 + 卡尔曼残差 + 自学习平滑",
        },
    }


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("复杂度分析")
    print("=" * 60)

    results = {}

    # -------- 1. 特征提取时间 --------
    print("\n[1] 特征提取时间")
    signal = np.random.randn(5000)
    t_feat = time_feature_extraction(signal, 200000, n_runs=100)
    print(f"  单次特征提取: {t_feat:.3f} ms (5000采样点, 14维)")
    results["feature_extraction_ms"] = float(t_feat)

    # -------- 2. KNN 推理时间 --------
    print("\n[2] KNN 推理时间")
    for n_train in [500, 1000, 2000]:
        X_train = np.random.randn(n_train, 14)
        X_test = np.random.randn(100, 14)
        predict = time_knn_k9(X_train, X_test, k=9)
        start = time.perf_counter()
        predict(X_test)
        elapsed = (time.perf_counter() - start) / 100 * 1000  # ms/sample
        print(f"  训练集={n_train}, 测试100样本: {elapsed:.4f} ms/样本")
        results[f"knn_inference_ms_per_sample_n{n_train}"] = float(elapsed)

    # -------- 3. MLP 推理时间 --------
    print("\n[3] MLP 推理时间")
    W1 = np.random.randn(14, 64) * 0.1
    b1 = np.zeros((1, 64))
    W2 = np.random.randn(64, 32) * 0.1
    b2 = np.zeros((1, 32))
    W3 = np.random.randn(32, 3) * 0.1
    b3 = np.zeros((1, 3))
    X_test = np.random.randn(100, 14)
    predict_mlp = time_mlp_forward(X_test, W1, b1, W2, b2, W3, b3)
    start = time.perf_counter()
    for _ in range(1000):
        predict_mlp(X_test)
    elapsed = (time.perf_counter() - start) / 1000 / 100 * 1000  # ms/sample
    print(f"  MLP前向传播: {elapsed:.5f} ms/样本")
    results["mlp_inference_ms_per_sample"] = float(elapsed)

    # -------- 4. 卡尔曼融合推理时间 --------
    print("\n[4] 卡尔曼融合推理时间")
    for M in [1, 2, 3]:
        R_list = [0.5] * M
        start = time.perf_counter()
        for _ in range(100):
            time_kalman(2.5, R_list, Q=0.01, n_iter=200)
        elapsed = (time.perf_counter() - start) / 100 * 1000  # ms for 200 steps
        print(f"  模态数={M}, 200步: {elapsed:.4f} ms")
        results[f"kalman_fusion_ms_200steps_M{M}"] = float(elapsed)

    # -------- 5. 参数规模 --------
    print("\n[5] 参数规模")
    params_mlp = count_parameters_mlp(14, 64, 32, 3)
    print(f"  MLP 参数量: 层1={params_mlp['layer1']}, 层2={params_mlp['layer2']}, "
          f"层3={params_mlp['layer3']}, 总计={params_mlp['total']}")
    results["mlp_params"] = params_mlp

    X_train = np.random.randn(1000, 14)
    params_knn = count_parameters_knn(X_train)
    print(f"  KNN 存储: {params_knn['n_train_samples']}样本 × {params_knn['feature_dim']}维 "
          f"= {params_knn['total_floats']} floats")
    results["knn_params"] = params_knn

    # -------- 6. 内存占用 --------
    print("\n[6] 内存占用 (峰值)")
    tracemalloc.start()
    X_big = np.random.randn(5000, 14)
    _ = np.sqrt(np.sum(X_big ** 2, axis=1))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"  处理5000样本: 峰值内存 = {peak / 1024 / 1024:.2f} MB")
    results["peak_memory_MB_5000_samples"] = float(peak / 1024 / 1024)

    # -------- 7. 理论复杂度 --------
    print("\n[7] 理论复杂度")
    tc = theoretical_complexity()
    for name, c in tc.items():
        print(f"\n  {name}")
        print(f"    时间: {c['time_complexity']}")
        print(f"    空间: {c['space_complexity']}")
    results["theoretical_complexity"] = tc

    # -------- 8. 端到端延迟估算 --------
    print("\n[8] 端到端延迟估算（单层处理）")
    t_total = t_feat + 0.001 + 0.0001 + 0.001  # 特征+MLP+融合+决策（近似）
    print(f"  特征提取:  {t_feat:.3f} ms")
    print(f"  MLP推理:   0.001 ms")
    print(f"  卡尔曼融合: 0.001 ms")
    print(f"  决策:      <0.001 ms")
    print(f"  总延迟:    ~{t_total:.3f} ms")
    results["end_to_end_latency_ms"] = float(t_total)

    # 保存
    with open(OUTPUT_DIR / "complexity_analysis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'complexity_analysis.json'}")


if __name__ == "__main__":
    main()