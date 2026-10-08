# -*- coding: utf-8 -*-
"""
多模态融合验证 - 统一卡尔曼框架仿真
调用口令：SCP111
运行: py -3.12 run_fusion_sim.py
"""
import numpy as np
import json
from pathlib import Path

OUTPUT_DIR = Path("data/fusion")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(42)

print("=" * 60)
print("多模态融合验证 - 统一卡尔曼框架")
print("=" * 60)

# ============================================================
# 1. 参数配置
# ============================================================
N_STEPS = 200             # 时间步数（模拟逐层监测）
TRUE_DEPTH = 2.5          # 真实缺陷深度 mm
TRUE_SIZE = 0.8           # 真实缺陷尺寸 mm

# 各模态观测噪声（标准差，基于真实模块的性能反推）
SIGMA_AE = 0.85           # 声学模块：分类精度85% → 深度估计误差较大
SIGMA_LU = 0.42           # 激光超声：定位精度较高
SIGMA_PC = 0.60           # 点云：表面测量，对深度估计中等

# 卡尔曼参数
Q = 0.01                  # 过程噪声
R_AE = SIGMA_AE ** 2
R_LU = SIGMA_LU ** 2
R_PC = SIGMA_PC ** 2

print(f"\n[配置]")
print(f"  真实缺陷深度: {TRUE_DEPTH} mm")
print(f"  真实缺陷尺寸: {TRUE_SIZE} mm")
print(f"  声学观测噪声 σ: {SIGMA_AE} mm")
print(f"  超声观测噪声 σ: {SIGMA_LU} mm")
print(f"  点云观测噪声 σ: {SIGMA_PC} mm")

# ============================================================
# 2. 生成模拟观测数据
# ============================================================
print(f"\n[1] 生成 {N_STEPS} 步模拟观测...")

# 真实状态（缺陷深度随时间缓慢变化，模拟逐层演化）
true_states = TRUE_DEPTH + 0.05 * np.sin(np.linspace(0, 4*np.pi, N_STEPS))

# 各模态观测
z_ae = true_states + np.random.normal(0, SIGMA_AE, N_STEPS)
z_lu = true_states + np.random.normal(0, SIGMA_LU, N_STEPS)
z_pc = true_states + np.random.normal(0, SIGMA_PC, N_STEPS)

# ============================================================
# 3. 单模态估计误差（基线）
# ============================================================
print(f"\n[2] 单模态估计误差...")

err_ae = np.abs(z_ae - true_states)
err_lu = np.abs(z_lu - true_states)
err_pc = np.abs(z_pc - true_states)

print(f"  声学单模态:   MAE={np.mean(err_ae):.4f} mm, RMSE={np.sqrt(np.mean(err_ae**2)):.4f} mm")
print(f"  超声单模态:   MAE={np.mean(err_lu):.4f} mm, RMSE={np.sqrt(np.mean(err_lu**2)):.4f} mm")
print(f"  点云单模态:   MAE={np.mean(err_pc):.4f} mm, RMSE={np.sqrt(np.mean(err_pc**2)):.4f} mm")

# ============================================================
# 4. 卡尔曼滤波融合
# ============================================================
print(f"\n[3] 卡尔曼滤波融合...")

def kalman_fusion(z_list, R_list, Q=0.01):
    """
    多模态卡尔曼融合
    z_list: 各模态观测序列列表
    R_list: 各模态观测噪声方差列表
    """
    n = len(z_list[0])
    x_est = np.zeros(n)
    P = np.zeros(n)
    
    # 初始化
    x_est[0] = np.mean([z[0] for z in z_list])
    P[0] = 1.0
    
    for k in range(1, n):
        # 预测
        x_pred = x_est[k-1]
        P_pred = P[k-1] + Q
        
        # 融合更新：多观测同时更新
        # 等价于序贯更新，每次更新一个观测
        x_upd = x_pred
        P_upd = P_pred
        for z, R in zip(z_list, R_list):
            K = P_upd / (P_upd + R)
            x_upd = x_upd + K * (z[k] - x_upd)
            P_upd = (1 - K) * P_upd
        
        x_est[k] = x_upd
        P[k] = P_upd
    
    return x_est

# 三模态融合
x_fused_3 = kalman_fusion([z_ae, z_lu, z_pc], [R_AE, R_LU, R_PC], Q)
# 双模态融合（声学+超声）
x_fused_2 = kalman_fusion([z_ae, z_lu], [R_AE, R_LU], Q)

err_fused_3 = np.abs(x_fused_3 - true_states)
err_fused_2 = np.abs(x_fused_2 - true_states)

print(f"  双模态融合 (AE+LU):  MAE={np.mean(err_fused_2):.4f} mm, RMSE={np.sqrt(np.mean(err_fused_2**2)):.4f} mm")
print(f"  三模态融合 (AE+LU+PC): MAE={np.mean(err_fused_3):.4f} mm, RMSE={np.sqrt(np.mean(err_fused_3**2)):.4f} mm")

# ============================================================
# 5. 融合提升对比
# ============================================================
print(f"\n[4] 融合提升对比:")

baseline_rmse = np.sqrt(np.mean(err_ae**2))  # 以最差的声学为基线
fused_rmse_3 = np.sqrt(np.mean(err_fused_3**2))
improvement = (baseline_rmse - fused_rmse_3) / baseline_rmse * 100

print(f"  基线（声学单模态）RMSE: {baseline_rmse:.4f} mm")
print(f"  三模态融合 RMSE:        {fused_rmse_3:.4f} mm")
print(f"  误差降低:               {improvement:.1f}%")

# ============================================================
# 6. 自适应卡尔曼增益验证
# ============================================================
print(f"\n[5] 自适应卡尔曼增益分析...")
print(f"  各模态理论权重（1/R归一化）:")
total_inv_R = 1/R_AE + 1/R_LU + 1/R_PC
print(f"    声学权重: {(1/R_AE)/total_inv_R*100:.1f}%")
print(f"    超声权重: {(1/R_LU)/total_inv_R*100:.1f}%")
print(f"    点云权重: {(1/R_PC)/total_inv_R*100:.1f}%")

# ============================================================
# 7. 保存结果
# ============================================================
results = {
    "n_steps": N_STEPS,
    "true_depth": TRUE_DEPTH,
    "sigmas": {"ae": SIGMA_AE, "lu": SIGMA_LU, "pc": SIGMA_PC},
    "single_modal_rmse": {
        "acoustic": float(np.sqrt(np.mean(err_ae**2))),
        "laser_ultrasound": float(np.sqrt(np.mean(err_lu**2))),
        "point_cloud": float(np.sqrt(np.mean(err_pc**2))),
    },
    "fusion_rmse": {
        "two_modal_ae_lu": float(np.sqrt(np.mean(err_fused_2**2))),
        "three_modal": float(np.sqrt(np.mean(err_fused_3**2))),
    },
    "improvement_percent": float(improvement),
    "weights": {
        "acoustic": float((1/R_AE)/total_inv_R),
        "laser_ultrasound": float((1/R_LU)/total_inv_R),
        "point_cloud": float((1/R_PC)/total_inv_R),
    }
}

with open(OUTPUT_DIR / "fusion_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

np.save(OUTPUT_DIR / "true_states.npy", true_states)
np.save(OUTPUT_DIR / "x_fused_3.npy", x_fused_3)
np.save(OUTPUT_DIR / "x_fused_2.npy", x_fused_2)

print(f"\n{'=' * 60}")
print(f"融合验证完成！")
print(f"结果已保存至: {OUTPUT_DIR}")
print(f"{'=' * 60}")