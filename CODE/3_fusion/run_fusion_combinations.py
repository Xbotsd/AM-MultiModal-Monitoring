# -*- coding: utf-8 -*-
"""
多模态组合对比：AE+LU / AE+PC / LU+PC / 三模态
调用口令：SCP111
运行: py -3.12 run_fusion_combinations.py
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

OUTPUT_DIR = Path("data/fusion")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(42)

N_STEPS = 200
TRUE_DEPTH = 2.5

SIGMA_AE = 0.85
SIGMA_LU = 0.42
SIGMA_PC = 0.60
R_AE, R_LU, R_PC = SIGMA_AE**2, SIGMA_LU**2, SIGMA_PC**2


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


def main():
    print("=" * 60)
    print("多模态组合对比")
    print("=" * 60)

    # 生成观测
    true_states = TRUE_DEPTH + 0.05 * np.sin(np.linspace(0, 4*np.pi, N_STEPS))
    z_ae = true_states + np.random.normal(0, SIGMA_AE, N_STEPS)
    z_lu = true_states + np.random.normal(0, SIGMA_LU, N_STEPS)
    z_pc = true_states + np.random.normal(0, SIGMA_PC, N_STEPS)

    combinations = {
        "AE only": ([z_ae], [R_AE]),
        "LU only": ([z_lu], [R_LU]),
        "PC only": ([z_pc], [R_PC]),
        "AE + LU": ([z_ae, z_lu], [R_AE, R_LU]),
        "AE + PC": ([z_ae, z_pc], [R_AE, R_PC]),
        "LU + PC": ([z_lu, z_pc], [R_LU, R_PC]),
        "AE + LU + PC": ([z_ae, z_lu, z_pc], [R_AE, R_LU, R_PC]),
    }

    results = {}
    print(f"\n{'组合':<16s} {'RMSE (mm)':>12s} {'MAE (mm)':>12s}")
    print("-" * 42)

    for name, (z_list, R_list) in combinations.items():
        x_est = kalman_fusion(z_list, R_list)
        rmse = np.sqrt(np.mean((x_est - true_states)**2))
        mae = np.mean(np.abs(x_est - true_states))
        results[name] = {"rmse": float(rmse), "mae": float(mae)}
        print(f"{name:<16s} {rmse:>12.4f} {mae:>12.4f}")

    # 最优单模态
    best_single = min(results["AE only"]["rmse"], results["LU only"]["rmse"], results["PC only"]["rmse"])
    print(f"\n最优单模态 RMSE: {best_single:.4f} mm")
    for name in ["AE + LU", "AE + PC", "LU + PC", "AE + LU + PC"]:
        imp = (best_single - results[name]["rmse"]) / best_single * 100
        print(f"  {name}: 相比最优单模态 ↓{imp:.1f}%")

    with open(OUTPUT_DIR / "fusion_combinations.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'fusion_combinations.json'}")


if __name__ == "__main__":
    main()