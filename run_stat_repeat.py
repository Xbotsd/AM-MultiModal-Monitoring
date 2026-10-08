# -*- coding: utf-8 -*-
"""
重复实验 + t检验 (10次不同随机种子)
调用口令：SCP111
运行: py -3.12 run_stat_repeat.py
"""
import numpy as np
from pathlib import Path
from scipy import stats
import json

OUTPUT_DIR = Path("data/statistics")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fusion_rmse(seed):
    np.random.seed(seed)
    N = 200
    TRUE = 2.5
    true_states = TRUE + 0.05 * np.sin(np.linspace(0, 4*np.pi, N))
    z_ae = true_states + np.random.normal(0, 0.85, N)
    z_lu = true_states + np.random.normal(0, 0.42, N)
    z_pc = true_states + np.random.normal(0, 0.60, N)
    x_avg = (z_ae + z_lu + z_pc) / 3.0

    def kalman(z_list, R_list, Q=0.01):
        x_est = np.zeros(N); P = np.zeros(N)
        x_est[0] = np.mean([z[0] for z in z_list]); P[0] = 1.0
        for k in range(1, N):
            x_pred = x_est[k-1]; P_pred = P[k-1] + Q
            x_upd = x_pred; P_upd = P_pred
            for z, R in zip(z_list, R_list):
                K = P_upd / (P_upd + R)
                x_upd = x_upd + K * (z[k] - x_upd)
                P_upd = (1 - K) * P_upd
            x_est[k] = x_upd; P[k] = P_upd
        return x_est

    x_kalman = kalman([z_ae, z_lu, z_pc], [0.85**2, 0.42**2, 0.60**2])
    return (
        np.sqrt(np.mean((x_avg - true_states)**2)),
        np.sqrt(np.mean((x_kalman - true_states)**2)),
    )


def report_stat(name, data):
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    ci_low, ci_high = stats.t.interval(0.95, len(data)-1, loc=mean, scale=std/np.sqrt(len(data)))
    print(f"  {name}: {mean:.4f} ± {std:.4f} (95% CI: [{ci_low:.4f}, {ci_high:.4f}])")
    return {"mean": float(mean), "std": float(std), "ci_low": float(ci_low), "ci_high": float(ci_high)}


def main():
    print("=" * 60)
    print("重复实验 + t检验 (10次不同随机种子)")
    print("=" * 60)

    seeds = list(range(10))
    rmses_avg, rmses_kalman = [], []
    for s in seeds:
        r_avg, r_kalman = fusion_rmse(s)
        rmses_avg.append(r_avg)
        rmses_kalman.append(r_kalman)

    rmses_avg = np.array(rmses_avg)
    rmses_kalman = np.array(rmses_kalman)

    print("\n统计结果:")
    stat_avg = report_stat("简单平均", rmses_avg)
    stat_kalman = report_stat("自适应卡尔曼", rmses_kalman)

    t_stat, p_value = stats.ttest_rel(rmses_avg, rmses_kalman)
    print(f"\n配对t检验: t={t_stat:.3f}, p={p_value:.2e}")
    print(f"显著性: {'✅ p<0.05，差异显著' if p_value < 0.05 else '❌ 差异不显著'}")

    improvement = (np.mean(rmses_avg) - np.mean(rmses_kalman)) / np.mean(rmses_avg) * 100
    print(f"误差降低: {improvement:.1f}%")

    output = {
        "simple_average": stat_avg,
        "adaptive_kalman": stat_kalman,
        "improvement_percent": float(improvement),
        "t_statistic": float(t_stat),
        "p_value": float(p_value),
        "n_runs": 10,
    }
    with open(OUTPUT_DIR / "repeat_experiment.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'repeat_experiment.json'}")


if __name__ == "__main__":
    main()