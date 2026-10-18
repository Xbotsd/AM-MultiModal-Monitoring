# -*- coding: utf-8 -*-
"""
全面敏感性分析
调用口令：SCP111
运行: py -3.12 run_sensitivity_full.py
"""
# --- AUTO INJECTED PATH FIX ---
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT_DIR)
# ------------------------------

import numpy as np
from pathlib import Path
import json

OUTPUT_DIR = Path("data/sensitivity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def kalman_fusion(z_list, R_list, Q=0.01):
    n = len(z_list[0])
    x_est = np.zeros(n); P = np.zeros(n)
    x_est[0] = np.mean([z[0] for z in z_list]); P[0] = 1.0
    for k in range(1, n):
        x_pred = x_est[k-1]; P_pred = P[k-1] + Q
        x_upd = x_pred; P_upd = P_pred
        for z, R in zip(z_list, R_list):
            K = P_upd / (P_upd + R)
            x_upd = x_upd + K * (z[k] - x_upd)
            P_upd = (1 - K) * P_upd
        x_est[k] = x_upd; P[k] = P_upd
    return x_est


# ============================================================
# 1. 噪声水平敏感性
# ============================================================
def noise_sensitivity():
    print("\n[1] 噪声水平敏感性")
    print(f"{'σ scale':>10s} {'RMSE (mm)':>12s}")
    print("-" * 25)
    results = {}
    for scale in [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]:
        np.random.seed(42)
        N = 200
        true = 2.5 + 0.05 * np.sin(np.linspace(0, 4*np.pi, N))
        z_ae = true + np.random.normal(0, 0.85*scale, N)
        z_lu = true + np.random.normal(0, 0.42*scale, N)
        z_pc = true + np.random.normal(0, 0.60*scale, N)
        R_list = [(0.85*scale)**2, (0.42*scale)**2, (0.60*scale)**2]
        x_est = kalman_fusion([z_ae, z_lu, z_pc], R_list)
        rmse = np.sqrt(np.mean((x_est - true)**2))
        results[scale] = float(rmse)
        print(f"{scale:>10.2f} {rmse:>12.4f}")
    return results


# ============================================================
# 2. Q值敏感性
# ============================================================
def q_sensitivity():
    print("\n[2] 过程噪声 Q 敏感性")
    print(f"{'Q':>10s} {'RMSE (mm)':>12s}")
    print("-" * 25)
    results = {}
    np.random.seed(42)
    N = 200
    true = 2.5 + 0.05 * np.sin(np.linspace(0, 4*np.pi, N))
    z_ae = true + np.random.normal(0, 0.85, N)
    z_lu = true + np.random.normal(0, 0.42, N)
    z_pc = true + np.random.normal(0, 0.60, N)
    R_list = [0.85**2, 0.42**2, 0.60**2]
    for Q in [0.0001, 0.001, 0.01, 0.05, 0.1, 0.5]:
        x_est = kalman_fusion([z_ae, z_lu, z_pc], R_list, Q=Q)
        rmse = np.sqrt(np.mean((x_est - true)**2))
        results[Q] = float(rmse)
        print(f"{Q:>10.4f} {rmse:>12.4f}")
    return results


# ============================================================
# 3. 伪标签阈值敏感性（激光超声）
# ============================================================
def pseudolabel_sensitivity():
    print("\n[3] 激光超声伪标签阈值敏感性")
    print(f"{'percentile':>12s} {'class balance':>15s}")
    print("-" * 30)
    data_path = Path("data/laser_ultrasound/X_lu.npy")
    if not data_path.exists():
        print("  X_lu.npy 不存在，跳过")
        return {}
    X = np.load(data_path)
    energies = np.sum(X**2, axis=1)
    results = {}
    for pct in [60, 70, 80, 90]:
        threshold = np.percentile(energies, pct)
        n_defect = int(np.sum(energies > threshold))
        n_normal = len(energies) - n_defect
        results[pct] = {"n_defect": n_defect, "n_normal": n_normal}
        print(f"{pct:>12d} {n_defect:>6d} / {n_normal:>6d}")
    return results


# ============================================================
# 4. 点云体素尺寸敏感性
# ============================================================
def voxel_sensitivity():
    print("\n[4] 点云体素尺寸敏感性（理论分析）")
    print(f"{'voxel_size (mm)':>16s} {'理论压缩率':>12s} {'缺陷保持':>10s}")
    print("-" * 42)
    # 100x100 mm平面，0.5mm步长 = 200x200 = 40000点
    base_points = 40000
    results = {}
    for vs in [0.5, 1.0, 1.5, 2.0, 3.0]:
        # 体素数 = (100/vs)^2
        n_voxels = int((100/vs)**2)
        compression = n_voxels / base_points
        # 小缺陷(2mm半径)是否能被体素保持
        keep = "✅" if vs <= 2.0 else "⚠️"
        results[vs] = {"compression": compression, "defect_keep": keep}
        print(f"{vs:>16.1f} {compression:>11.1%} {keep:>10s}")
    return results


def main():
    print("=" * 60)
    print("全面敏感性分析")
    print("=" * 60)

    results = {
        "noise_sensitivity": noise_sensitivity(),
        "q_sensitivity": q_sensitivity(),
        "pseudolabel_sensitivity": pseudolabel_sensitivity(),
        "voxel_sensitivity": voxel_sensitivity(),
    }

    with open(OUTPUT_DIR / "sensitivity_full.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n结果已保存: {OUTPUT_DIR / 'sensitivity_full.json'}")


if __name__ == "__main__":
    main()