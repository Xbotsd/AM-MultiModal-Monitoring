# -*- coding: utf-8 -*-
"""
相位解缠基线对比实验
调用口令：SCP111
运行: py -3.12 run_unwrap_baseline.py
"""
import numpy as np
import json
from pathlib import Path

OUTPUT_DIR = Path("data/phase_unwrap")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(42)

print("=" * 60)
print("相位解缠基线对比实验")
print("=" * 60)

# ============================================================
# 1. 数据配置
# ============================================================
GRID = 128
WAVELENGTH = 0.532e-6
H_MAX = 1e-6

print(f"\n[配置]")
print(f"  网格: {GRID}×{GRID}")
print(f"  波长: {WAVELENGTH*1e9:.0f} nm")
print(f"  最大高度: {H_MAX*1e6:.2f} μm")

# ============================================================
# 2. 生成真实相位和缠绕相位
# ============================================================
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

# 检查Nyquist条件
dx_phase = np.max(np.abs(np.diff(phi_true, axis=1)))
dy_phase = np.max(np.abs(np.diff(phi_true, axis=0)))
print(f"\n[1] Nyquist检查: dx={dx_phase:.3f}, dy={dy_phase:.3f}")
print(f"    条件满足: {'✅' if max(dx_phase, dy_phase) < np.pi else '❌'}")

# ============================================================
# 3. 注入噪声
# ============================================================
noise_gaussian = np.random.normal(0, 0.2, (GRID, GRID))
n_impulse = int(0.02 * GRID * GRID)
impulse_mask = np.zeros((GRID, GRID), dtype=bool)
impulse_mask.flat[np.random.choice(GRID*GRID, n_impulse, replace=False)] = True
noise_impulse = np.zeros_like(phi_wrapped)
noise_impulse[impulse_mask] = np.random.uniform(-np.pi, np.pi, n_impulse)
phi_noisy = phi_wrapped + noise_gaussian + noise_impulse

print(f"[2] 噪声: 高斯σ=0.2 rad, 脉冲{n_impulse}个")

# ============================================================
# 4. Baseline 1: 最小二乘法（无权）
# ============================================================
print(f"\n[Baseline 1] 最小二乘法（无权）...")

def unwrap_ls_unweighted(phi_wrapped):
    """基于行列梯度平均的最简解缠"""
    dx = np.angle(np.exp(1j * np.diff(phi_wrapped, axis=1)))
    dy = np.angle(np.exp(1j * np.diff(phi_wrapped, axis=0)))
    phi_rows = np.cumsum(np.hstack([np.zeros((GRID, 1)), dx]), axis=1)
    phi_cols = np.cumsum(np.vstack([np.zeros((1, GRID)), dy]), axis=0)
    return (phi_rows + phi_cols) / 2

phi_ls = unwrap_ls_unweighted(phi_noisy)

# ============================================================
# 5. Baseline 2: 加权最小二乘（基于相位质量）
# ============================================================
print(f"[Baseline 2] 加权最小二乘法...")

def unwrap_ls_weighted(phi_wrapped):
    """加权最小二乘：用局部相位方差的倒数作为权重"""
    dx = np.angle(np.exp(1j * np.diff(phi_wrapped, axis=1)))
    dy = np.angle(np.exp(1j * np.diff(phi_wrapped, axis=0)))
    
    # 权重：邻域方差小的地方权重高（更可靠）
    from scipy.ndimage import uniform_filter
    variance = uniform_filter(phi_wrapped**2, size=3) - uniform_filter(phi_wrapped, size=3)**2
    weight = 1.0 / (variance + 1e-6)
    weight = weight / np.max(weight)
    
    # 加权行积分
    phi_rows = np.zeros_like(phi_wrapped)
    for i in range(GRID):
        for j in range(1, GRID):
            phi_rows[i, j] = phi_rows[i, j-1] + dx[i, j-1] * weight[i, j]
    
    # 加权列积分
    phi_cols = np.zeros_like(phi_wrapped)
    for j in range(GRID):
        for i in range(1, GRID):
            phi_cols[i, j] = phi_cols[i-1, j] + dy[i-1, j] * weight[i, j]
    
    return (phi_rows + phi_cols) / 2

phi_ls_w = unwrap_ls_weighted(phi_noisy)

# ============================================================
# 6. Baseline 3: 质量引导法
# ============================================================
print(f"[Baseline 3] 质量引导法...")

def unwrap_quality_guided(phi_wrapped):
    """质量引导法：从高质量区域向低质量区域积分"""
    from scipy.ndimage import uniform_filter
    variance = uniform_filter(phi_wrapped**2, size=3) - uniform_filter(phi_wrapped, size=3)**2
    quality = 1.0 / (variance + 1e-6)
    
    # 按质量降序处理像素
    phi_result = np.zeros_like(phi_wrapped)
    processed = np.zeros_like(phi_wrapped, dtype=bool)
    
    # 从最高质量的像素开始
    sorted_indices = np.argsort(-quality.flatten())
    
    for idx in sorted_indices:
        i, j = idx // GRID, idx % GRID
        if processed[i, j]:
            continue
        # 找已处理的邻居
        neighbors = []
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < GRID and 0 <= nj < GRID and processed[ni, nj]:
                # 计算相位差
                diff = phi_wrapped[i, j] - phi_wrapped[ni, nj]
                diff_wrapped = np.angle(np.exp(1j * diff))
                neighbors.append((phi_result[ni, nj] + diff_wrapped, quality[ni, nj]))
        if neighbors:
            total_w = sum(w for _, w in neighbors)
            phi_result[i, j] = sum(v * w for v, w in neighbors) / total_w
        else:
            phi_result[i, j] = phi_wrapped[i, j]
        processed[i, j] = True
    
    return phi_result

phi_qg = unwrap_quality_guided(phi_noisy)

# ============================================================
# 7. 你的方法：传统积分 + 卡尔曼残差 + 自学习
# ============================================================
print(f"[方法4] 传统积分 + 卡尔曼残差 + 自学习（本项目）...")

def traditional_unwrap(phi_wrapped):
    dx = np.angle(np.exp(1j * np.diff(phi_wrapped, axis=1)))
    dy = np.angle(np.exp(1j * np.diff(phi_wrapped, axis=0)))
    phi_rows = np.cumsum(np.hstack([np.zeros((GRID, 1)), dx]), axis=1)
    phi_cols = np.cumsum(np.vstack([np.zeros((1, GRID)), dy]), axis=0)
    return (phi_rows + phi_cols) / 2

def kalman_residual_filter(phi_trad, phi_noisy, Q=1e-4, R=0.04, iterations=3):
    residual = np.zeros_like(phi_trad)
    P = np.ones_like(phi_trad)
    for it in range(iterations):
        for i in range(GRID):
            for j in range(1, GRID):
                pred = residual[i, j-1]
                P_pred = P[i, j-1] + Q
                obs_raw = phi_noisy[i, j] - phi_trad[i, j]
                obs = np.angle(np.exp(1j * obs_raw))
                K = P_pred / (P_pred + R)
                residual[i, j] = pred + K * (obs - pred)
                P[i, j] = (1 - K) * P_pred
        for j in range(GRID):
            for i in range(1, GRID):
                pred = residual[i-1, j]
                P_pred = P[i-1, j] + Q
                obs_raw = phi_noisy[i, j] - phi_trad[i, j]
                obs = np.angle(np.exp(1j * obs_raw))
                K = P_pred / (P_pred + R)
                residual[i, j] = pred + K * (obs - pred)
                P[i, j] = (1 - K) * P_pred
    return phi_trad + residual

def self_learning_smooth(phi, iterations=30):
    try:
        from scipy.ndimage import gaussian_filter
    except ImportError:
        return phi
    phi_c = phi.copy()
    lr = 0.02
    for it in range(iterations):
        smooth = gaussian_filter(phi_c, sigma=0.5) - phi_c
        phi_c = phi_c + lr * smooth
    return phi_c

phi_trad = traditional_unwrap(phi_noisy)
phi_kalman = kalman_residual_filter(phi_trad, phi_noisy)
phi_proposed = self_learning_smooth(phi_kalman)

# ============================================================
# 8. 性能评估
# ============================================================
def rmse(est, true):
    return np.sqrt(np.mean((est - true) ** 2))

def mae(est, true):
    return np.mean(np.abs(est - true))

methods = {
    "Least Squares (unweighted)": phi_ls,
    "Weighted Least Squares": phi_ls_w,
    "Quality-Guided": phi_qg,
    "Traditional Integration": phi_trad,
    "Kalman Residual Filtering": phi_kalman,
    "Proposed (Trad + KF + SL)": phi_proposed,
}

results = {}
for name, phi_est in methods.items():
    h_est = phi_est / k
    r_phase = rmse(phi_est, phi_true)
    r_h = rmse(h_est, h_true) * 1e6
    m_h = mae(h_est, h_true) * 1e6
    results[name] = {"rmse_phase": float(r_phase), "rmse_height_um": float(r_h), "mae_height_um": float(m_h)}

print(f"\n{'=' * 60}")
print(f"性能对比结果")
print(f"{'=' * 60}")
print(f"{'方法':<32s} {'相位RMSE':>10s} {'高度RMSE':>10s} {'高度MAE':>10s}")
print("-" * 70)

baseline_rmse = None
for name, (r_dict) in results.items():
    r_p = r_dict["rmse_phase"]
    r_h = r_dict["rmse_height_um"]
    m_h = r_dict["mae_height_um"]
    print(f"{name:<32s} {r_p:>10.3f} {r_h:>10.4f} {m_h:>10.4f}")

# 提升对比（以最优基线为基准）
baseline_best = min(v["rmse_height_um"] for k_name, v in results.items() 
                    if k_name not in ["Proposed (Trad + KF + SL)"])
proposed = results["Proposed (Trad + KF + SL)"]["rmse_height_um"]
improvement = (baseline_best - proposed) / baseline_best * 100

print(f"\n最优基线 RMSE: {baseline_best:.4f} μm")
print(f"本项目方法 RMSE: {proposed:.4f} μm")
print(f"提升: {improvement:.1f}%")

# ============================================================
# 9. 保存
# ============================================================
output = {
    "config": {
        "GRID": GRID,
        "WAVELENGTH_nm": WAVELENGTH * 1e9,
        "H_MAX_um": H_MAX * 1e6,
        "noise_sigma_rad": 0.2,
    },
    "results": results,
    "baseline_best_rmse": float(baseline_best),
    "proposed_rmse": float(proposed),
    "improvement_percent": float(improvement),
}

with open(OUTPUT_DIR / "unwrap_baseline_results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

np.save(OUTPUT_DIR / "phi_true_baseline.npy", phi_true)
np.save(OUTPUT_DIR / "phi_noisy_baseline.npy", phi_noisy)
for name, phi_est in methods.items():
    safe_name = name.replace(" ", "_").replace("(", "").replace(")", "").replace("+", "plus")
    np.save(OUTPUT_DIR / f"phi_{safe_name}.npy", phi_est)

print(f"\n{'=' * 60}")
print(f"结果已保存: {OUTPUT_DIR / 'unwrap_baseline_results.json'}")
print(f"{'=' * 60}")