# -*- coding: utf-8 -*-
"""
多模态融合基线对比实验
调用口令：SCP111
运行: py -3.12 run_fusion_baseline.py
"""
import numpy as np
import json
from pathlib import Path

OUTPUT_DIR = Path("data/fusion")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(42)

print("=" * 60)
print("多模态融合基线对比实验")
print("=" * 60)

# ============================================================
# 1. 数据配置
# ============================================================
N_STEPS = 200
TRUE_DEPTH = 2.5

# 各模态观测噪声（基于前序实验）
SIGMA_AE = 0.85
SIGMA_LU = 0.42
SIGMA_PC = 0.60

R_AE = SIGMA_AE ** 2
R_LU = SIGMA_LU ** 2
R_PC = SIGMA_PC ** 2

print(f"\n[配置]")
print(f"  时间步数: {N_STEPS}")
print(f"  真实缺陷深度: {TRUE_DEPTH} mm")
print(f"  声学噪声 σ: {SIGMA_AE} mm")
print(f"  超声噪声 σ: {SIGMA_LU} mm")
print(f"  点云噪声 σ: {SIGMA_PC} mm")

# ============================================================
# 2. 生成观测数据
# ============================================================
true_states = TRUE_DEPTH + 0.05 * np.sin(np.linspace(0, 4*np.pi, N_STEPS))

z_ae = true_states + np.random.normal(0, SIGMA_AE, N_STEPS)
z_lu = true_states + np.random.normal(0, SIGMA_LU, N_STEPS)
z_pc = true_states + np.random.normal(0, SIGMA_PC, N_STEPS)

print(f"\n[1] 观测数据生成完成")

# ============================================================
# 3. Baseline 1: 简单平均
# ============================================================
print(f"\n[Baseline 1] 简单平均...")
x_avg = (z_ae + z_lu + z_pc) / 3.0

# ============================================================
# 4. Baseline 2: 固定权重（基于先验精度）
# ============================================================
print(f"[Baseline 2] 固定权重 (0.2, 0.5, 0.3)...")
# 权重与噪声方差成反比
w_ae = 1/R_AE
w_lu = 1/R_LU
w_pc = 1/R_PC
w_total = w_ae + w_lu + w_pc
w_ae, w_lu, w_pc = w_ae/w_total, w_lu/w_total, w_pc/w_total
x_fixed = w_ae * z_ae + w_lu * z_lu + w_pc * z_pc
print(f"    实际权重: AE={w_ae:.3f}, LU={w_lu:.3f}, PC={w_pc:.3f}")

# ============================================================
# 5. Baseline 3: 单模态最优（仅激光超声）
# ============================================================
print(f"[Baseline 3] 单模态最优 (仅激光超声)...")
x_single = z_lu

# ============================================================
# 6. Baseline 4: 中值融合
# ============================================================
print(f"[Baseline 4] 中值融合...")
x_median = np.median(np.stack([z_ae, z_lu, z_pc], axis=0), axis=0)

# ============================================================
# 7. 你的方法：自适应卡尔曼滤波
# ============================================================
print(f"[方法5] 自适应卡尔曼滤波 (本项目方法)...")

def adaptive_kalman(z_list, R_list, Q=0.01):
    n = len(z_list[0])
    x_est = np.zeros(n)
    P = np.zeros(n)
    x_est[0] = np.mean([z[0] for z in z_list])
    P[0] = 1.0
    for k in range(1, n):
        x_pred = x_est[k-1]
        P_pred = P[k-1] + Q
        x_upd = x_pred
        P_upd = P_pred
        for z, R in zip(z_list, R_list):
            K = P_upd / (P_upd + R)
            x_upd = x_upd + K * (z[k] - x_upd)
            P_upd = (1 - K) * P_upd
        x_est[k] = x_upd
        P[k] = P_upd
    return x_est

x_kalman = adaptive_kalman([z_ae, z_lu, z_pc], [R_AE, R_LU, R_PC])

# ============================================================
# 8. 性能评估
# ============================================================
def rmse(est, true):
    return np.sqrt(np.mean((est - true) ** 2))

def mae(est, true):
    return np.mean(np.abs(est - true))

# 单模态基线
r_ae_only = rmse(z_ae, true_states)
r_lu_only = rmse(z_lu, true_states)
r_pc_only = rmse(z_pc, true_states)

results = {
    "AE only": (rmse(z_ae, true_states), mae(z_ae, true_states)),
    "LU only": (rmse(z_lu, true_states), mae(z_lu, true_states)),
    "PC only": (rmse(z_pc, true_states), mae(z_pc, true_states)),
    "Simple Average": (rmse(x_avg, true_states), mae(x_avg, true_states)),
    "Fixed Weight": (rmse(x_fixed, true_states), mae(x_fixed, true_states)),
    "Median Fusion": (rmse(x_median, true_states), mae(x_median, true_states)),
    "Adaptive Kalman": (rmse(x_kalman, true_states), mae(x_kalman, true_states)),
}

print(f"\n{'=' * 60}")
print(f"性能对比结果")
print(f"{'=' * 60}")
print(f"{'方法':<22s} {'RMSE (mm)':>12s} {'MAE (mm)':>12s} {'相比最优单模态':>16s}")
print("-" * 60)

best_single_rmse = min(r_ae_only, r_lu_only, r_pc_only)

for name, (r, m) in results.items():
    if name in ["AE only", "LU only", "PC only"]:
        improvement = "基线"
    else:
        imp = (best_single_rmse - r) / best_single_rmse * 100
        improvement = f"↓ {imp:.1f}%"
    print(f"{name:<22s} {r:>12.4f} {m:>12.4f} {improvement:>16s}")

# ============================================================
# 9. 保存
# ============================================================
output = {
    "config": {
        "N_STEPS": N_STEPS,
        "SIGMA_AE": SIGMA_AE,
        "SIGMA_LU": SIGMA_LU,
        "SIGMA_PC": SIGMA_PC,
    },
    "weights": {
        "AE": float(w_ae),
        "LU": float(w_lu),
        "PC": float(w_pc),
    },
    "results": {k: {"rmse": float(v[0]), "mae": float(v[1])} for k, v in results.items()},
    "best_single_rmse": float(best_single_rmse),
}

with open(OUTPUT_DIR / "fusion_baseline_results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

np.save(OUTPUT_DIR / "true_states_baseline.npy", true_states)
np.save(OUTPUT_DIR / "x_kalman_baseline.npy", x_kalman)

print(f"\n{'=' * 60}")
print(f"结果已保存: {OUTPUT_DIR / 'fusion_baseline_results.json'}")
print(f"{'=' * 60}")