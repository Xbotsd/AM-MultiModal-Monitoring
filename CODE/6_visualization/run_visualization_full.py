# -*- coding: utf-8 -*-
"""
论文图表批量生成
调用口令：SCP111
运行: py -3.12 run_visualization_full.py
"""
# --- AUTO INJECTED PATH FIX ---
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT_DIR)
# ------------------------------

import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path

OUTPUT_DIR = Path("data/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 9
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['axes.linewidth'] = 0.8


def style_axes(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


# ============================================================
# 图1：多模态融合基线对比
# ============================================================
def fig_fusion_baseline():
    methods = ['AE\nonly', 'LU\nonly', 'PC\nonly', 'Simple\nAvg', 'Fixed\nWeight', 'Adaptive\nKalman']
    rmse = [0.790, 0.415, 0.597, 0.345, 0.308, 0.114]
    colors = ['#888888']*3 + ['#4472C4']*2 + ['#C00000']

    fig, ax = plt.subplots(figsize=(3.35, 2.5))
    bars = ax.bar(methods, rmse, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_ylabel('RMSE (mm)')
    ax.set_ylim(0, 0.9)
    for bar, val in zip(bars, rmse):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.02, f'{val:.3f}',
                ha='center', va='bottom', fontsize=7, fontweight='bold')
    style_axes(ax)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig1_fusion_baseline.png", dpi=600)
    plt.close()
    print("✅ 图1: fig1_fusion_baseline.png")


# ============================================================
# 图2：多模态组合对比
# ============================================================
def fig_fusion_combinations():
    methods = ['AE', 'LU', 'PC', 'AE+LU', 'AE+PC', 'LU+PC', 'AE+LU+PC']
    rmse = [0.1921, 0.1422, 0.1900, 0.1391, 0.1401, 0.1213, 0.1135]
    colors = ['#888888']*3 + ['#4472C4']*3 + ['#C00000']

    fig, ax = plt.subplots(figsize=(3.35, 2.5))
    bars = ax.bar(methods, rmse, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_ylabel('RMSE (mm)')
    ax.set_ylim(0, 0.22)
    for bar, val in zip(bars, rmse):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.005, f'{val:.4f}',
                ha='center', va='bottom', fontsize=6.5, fontweight='bold')
    style_axes(ax)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig2_fusion_combinations.png", dpi=600)
    plt.close()
    print("✅ 图2: fig2_fusion_combinations.png")


# ============================================================
# 图3：相位解缠基线对比
# ============================================================
def fig_unwrap_baseline():
    methods = ['Trad\nIntegration', 'DCT\nLS', 'Kalman\nResidual', 'Proposed']
    rmse = [0.0782, 0.0750, 0.0692, 0.0618]
    colors = ['#888888', '#888888', '#4472C4', '#C00000']

    fig, ax = plt.subplots(figsize=(3.35, 2.5))
    bars = ax.bar(methods, rmse, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_ylabel('Height RMSE (μm)')
    ax.set_ylim(0, 0.09)
    for bar, val in zip(bars, rmse):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.002, f'{val:.4f}',
                ha='center', va='bottom', fontsize=7, fontweight='bold')
    style_axes(ax)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig3_unwrap_baseline.png", dpi=600)
    plt.close()
    print("✅ 图3: fig3_unwrap_baseline.png")


# ============================================================
# 图4：闭环控制对比
# ============================================================
def fig_control_baseline():
    methods = ['No\nControl', 'PID', 'Fixed\nThreshold', 'Proposed']
    normal = [29, 35, 31, 37]
    severe = [9, 5, 5, 4]
    x = np.arange(len(methods))
    width = 0.35

    fig, ax = plt.subplots(figsize=(3.35, 2.5))
    ax.bar(x - width/2, normal, width, label='Normal', color='#4472C4',
           edgecolor='black', linewidth=0.5)
    ax.bar(x + width/2, severe, width, label='Severe', color='#C00000',
           edgecolor='black', linewidth=0.5)
    ax.set_ylabel('Layer Ratio (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.legend(frameon=False, fontsize=7)
    style_axes(ax)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig4_control_baseline.png", dpi=600)
    plt.close()
    print("✅ 图4: fig4_control_baseline.png")


# ============================================================
# 图5：声学消融
# ============================================================
def fig_acoustic_ablation():
    configs = ['Full\n(14-dim)', 'w/o\nband (6)', 'w/o\nspectral (8)', 'w/o\ntime (8)']
    knn = [85.21, 83.75, 84.58, 85.21]
    mlp = [87.92, 82.92, 86.25, 86.67]
    ens = [86.56, 83.33, 85.42, 85.94]
    x = np.arange(len(configs))
    width = 0.27

    fig, ax = plt.subplots(figsize=(3.35, 2.5))
    ax.bar(x - width, knn, width, label='KNN', color='#A6A6A6',
           edgecolor='black', linewidth=0.5)
    ax.bar(x, mlp, width, label='MLP', color='#4472C4',
           edgecolor='black', linewidth=0.5)
    ax.bar(x + width, ens, width, label='Ensemble', color='#C00000',
           edgecolor='black', linewidth=0.5)
    ax.set_ylabel('Accuracy (%)')
    ax.set_ylim(75, 92)
    ax.set_xticks(x)
    ax.set_xticklabels(configs)
    ax.legend(frameon=False, fontsize=7)
    style_axes(ax)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig5_acoustic_ablation.png", dpi=600)
    plt.close()
    print("✅ 图5: fig5_acoustic_ablation.png")


# ============================================================
# 图6：跨子集验证
# ============================================================
def fig_cross_subset():
    datasets = ['D1', 'D2', 'D3', 'D4']
    accs = [84.33, 92.67, 86.00, 87.33]

    fig, ax = plt.subplots(figsize=(3.35, 2.5))
    bars = ax.bar(datasets, accs, color='#4472C4', edgecolor='black', linewidth=0.5)
    ax.axhline(y=87.58, color='#C00000', linestyle='--', linewidth=1,
               label='Mean = 87.58%')
    ax.set_ylabel('Accuracy (%)')
    ax.set_ylim(75, 100)
    for bar, val in zip(bars, accs):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.8, f'{val:.2f}',
                ha='center', va='bottom', fontsize=7, fontweight='bold')
    ax.legend(frameon=False, fontsize=7)
    style_axes(ax)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig6_cross_subset.png", dpi=600)
    plt.close()
    print("✅ 图6: fig6_cross_subset.png")


# ============================================================
# 图7：噪声敏感性
# ============================================================
def fig_noise_sensitivity():
    scales = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]
    rmse = [0.0552, 0.0810, 0.1135, 0.1394, 0.1625, 0.2015]

    fig, ax = plt.subplots(figsize=(3.35, 2.5))
    ax.plot(scales, rmse, 'o-', color='#C00000', linewidth=1.5,
            markersize=5, markeredgecolor='black', markeredgewidth=0.5)
    ax.set_xlabel('Noise scaling factor')
    ax.set_ylabel('RMSE (mm)')
    ax.grid(True, alpha=0.3, linewidth=0.5)
    style_axes(ax)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig7_noise_sensitivity.png", dpi=600)
    plt.close()
    print("✅ 图7: fig7_noise_sensitivity.png")


# ============================================================
# 图8：AUC 条形图
# ============================================================
def fig_auc():
    methods = ['LU\n(binary)', 'LoF vs\nRest', 'Cond vs\nRest', 'Key vs\nRest']
    aucs = [0.9728, 0.9769, 0.9128, 0.9884]
    colors = ['#C00000', '#4472C4', '#4472C4', '#4472C4']

    fig, ax = plt.subplots(figsize=(3.35, 2.5))
    bars = ax.bar(methods, aucs, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_ylabel('AUC')
    ax.set_ylim(0.85, 1.0)
    for bar, val in zip(bars, aucs):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.003, f'{val:.4f}',
                ha='center', va='bottom', fontsize=7, fontweight='bold')
    style_axes(ax)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig8_auc.png", dpi=600)
    plt.close()
    print("✅ 图8: fig8_auc.png")


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("论文图表批量生成")
    print("=" * 60)
    print(f"输出目录: {OUTPUT_DIR}\n")

    fig_fusion_baseline()
    fig_fusion_combinations()
    fig_unwrap_baseline()
    fig_control_baseline()
    fig_acoustic_ablation()
    fig_cross_subset()
    fig_noise_sensitivity()
    fig_auc()

    print(f"\n所有图表已生成，分辨率 600 dpi，字体 Arial 9pt 加粗。")


if __name__ == "__main__":
    main()