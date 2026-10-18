# -*- coding: utf-8 -*-
"""
相位解缠 v4 - 传统解缠 + 卡尔曼残差滤波
调用口令：SCP111
运行: py -3.12 run_phase_unwrap_v4.py
"""
# --- AUTO INJECTED PATH FIX ---
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT_DIR)
# ------------------------------

import numpy as np
import json
from pathlib import Path
from scipy.ndimage import gaussian_filter

OUTPUT_DIR = Path("data/phase_unwrap")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(42)

print("=" * 60)
print("相位解缠 v4 - 传统解缠 + 卡尔曼残差滤波")
print("=" * 60)

GRID = 128
WAVELENGTH = 0.532e-6
H_MAX = 1e-6

# ---------- 1. 生成真实形变场 ----------
x = np.linspace(-1, 1, GRID)
y = np.linspace(-1, 1, GRID)
xx, yy = np.meshgrid(x, y)

warp = 0.5e-6 * np.exp(-(xx**2 + yy**2) / 0.5)
balling = np.zeros_like(warp)
for cx, cy, h in [(-0.5, 0.5, 0.3e-6), (0.5, -0.3, 0.4e-6), (-0.3, -0.6, 0.2e-6)]:
    balling += h * np.exp(-((xx-cx)**2 + (yy-cy)**2) / 0.1)

h_true = warp + balling
k = 4 * np.pi / WAVELENGTH
phi_true = k * h_true
phi_wrapped = np.angle(np.exp(1j * phi_true))

# ---------- 2. 噪声 ----------
noise_gaussian = np.random.normal(0, 0.2, (GRID, GRID))
n_impulse = int(0.02 * GRID * GRID)
impulse_mask = np.zeros((GRID, GRID), dtype=bool)
impulse_mask.flat[np.random.choice(GRID*GRID, n_impulse, replace=False)] = True
noise_impulse = np.zeros_like(phi_wrapped)
noise_impulse[impulse_mask] = np.random.uniform(-np.pi, np.pi, n_impulse)
phi_noisy = phi_wrapped + noise_gaussian + noise_impulse

print(f"[1] 真实高度范围: [{h_true.min()*1e6:.4f}, {h_true.max()*1e6:.4f}] μm")
print(f"[2] 噪声: 高斯σ=0.2 rad, 脉冲{n_impulse}个")

# ---------- 3. 传统梯度积分解缠 ----------
def traditional_unwrap(phi_wrapped):
    dx = np.angle(np.exp(1j * np.diff(phi_wrapped, axis=1)))
    dy = np.angle(np.exp(1j * np.diff(phi_wrapped, axis=0)))
    phi_rows = np.cumsum(np.hstack([np.zeros((GRID, 1)), dx]), axis=1)
    phi_cols = np.cumsum(np.vstack([np.zeros((1, GRID)), dy]), axis=0)
    return (phi_rows + phi_cols) / 2

phi_trad = traditional_unwrap(phi_noisy)

# ---------- 4. 卡尔曼残差滤波（真正的卡尔曼） ----------
def kalman_residual_filter(phi_trad, phi_noisy, Q=1e-4, R=0.04, iterations=3):
    """
    对传统解缠结果做卡尔曼平滑滤波：
    - 状态：phi_trad 的残差
    - 观测：phi_noisy - phi_trad 的缠绕残差
    - 迭代扫描：行列交替
    """
    residual = np.zeros_like(phi_trad)
    P = np.ones_like(phi_trad)
    
    for it in range(iterations):
        # 行扫描
        for i in range(GRID):
            for j in range(1, GRID):
                pred = residual[i, j-1]
                P_pred = P[i, j-1] + Q
                # 观测：噪声 - 当前估计
                obs_raw = phi_noisy[i, j] - phi_trad[i, j]
                # 缠绕到[-π, π]
                obs = np.angle(np.exp(1j * obs_raw))
                K = P_pred / (P_pred + R)
                residual[i, j] = pred + K * (obs - pred)
                P[i, j] = (1 - K) * P_pred
        # 列扫描
        for j in range(GRID):
            for i in range(1, GRID):
                pred = residual[i-1, j]
                P_pred = P[i-1, j] + Q
                obs_raw = phi_noisy[i, j] - phi_trad[i, j]
                obs = np.angle(np.exp(1j * obs_raw))
                K = P_pred / (P_pred + R)
                residual[i, j] = pred + K * (obs - pred)
                P[i, j] = (1 - K) * P_pred
    
    phi_filtered = phi_trad + residual
    return phi_filtered

phi_kalman_filtered = kalman_residual_filter(phi_trad, phi_noisy)

# ---------- 5. 自学习残差校正（无监督，仅平滑） ----------
def self_learning_smooth(phi, iterations=30):
    phi_c = phi.copy()
    lr = 0.02
    for it in range(iterations):
        smooth = gaussian_filter(phi_c, sigma=0.5) - phi_c
        phi_c = phi_c + lr * smooth
    return phi_c

phi_corrected = self_learning_smooth(phi_kalman_filtered)

# ---------- 6. 性能评估 ----------
def rmse(est, true):
    return np.sqrt(np.mean((est - true) ** 2))

h_trad = rmse(phi_trad / k, h_true) * 1e6
h_filtered = rmse(phi_kalman_filtered / k, h_true) * 1e6
h_corrected = rmse(phi_corrected / k, h_true) * 1e6

print(f"\n[7] 性能评估:")
print(f"  传统解缠:            高度RMSE={h_trad:.4f} μm")
print(f"  传统+卡尔曼滤波:      高度RMSE={h_filtered:.4f} μm")
print(f"  传统+卡尔曼+自学习:   高度RMSE={h_corrected:.4f} μm")

imp1 = (h_trad - h_filtered) / h_trad * 100
imp2 = (h_filtered - h_corrected) / h_filtered * 100

print(f"\n  卡尔曼滤波 vs 传统:    误差降低 {imp1:.2f}%")
print(f"  自学习 vs 卡尔曼滤波:  误差降低 {imp2:.2f}%")

# 保存
results = {
    "grid": GRID,
    "h_max_um": H_MAX * 1e6,
    "rmse_height_um": {
        "traditional": float(h_trad),
        "kalman_filtered": float(h_filtered),
        "kalman_self_learning": float(h_corrected),
    },
    "improvement_percent": {
        "kalman_vs_traditional": float(imp1),
        "self_learning_vs_kalman": float(imp2),
    }
}
with open(OUTPUT_DIR / "phase_unwrap_v4_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n{'=' * 60}")
print(f"v4 完成！")
print(f"{'=' * 60}")