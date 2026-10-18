# -*- coding: utf-8 -*-
"""
闭环控制基线对比实验 v4 - 折中参数
调用口令：SCP111
运行: py -3.12 run_control_baseline_v4.py
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

OUTPUT_DIR = Path("data/closed_loop")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_LAYERS = 100
BASE_LASER_POWER = 200.0
BASE_SCAN_SPEED = 800.0

# 折中参数：介于v2和v3之间
BASE_DEFECT = 0.12
EVENT_PROB = 0.20
EVENT_MAGNITUDE = 0.45
RECOVERY_RATE = 0.12
CONTROL_EFFECT = 0.60

THRESHOLD_NORMAL = 0.3
THRESHOLD_MILD = 0.5
THRESHOLD_MODERATE = 0.8


def generate_base_sequence(seed=42):
    np.random.seed(seed)
    probs = []
    current = BASE_DEFECT
    for layer in range(N_LAYERS):
        current = current * (1 - RECOVERY_RATE)
        if np.random.rand() < EVENT_PROB:
            current += np.random.uniform(0.10, EVENT_MAGNITUDE)
        current += np.random.normal(0, 0.02)
        current = np.clip(current, 0.0, 1.0)
        probs.append(current)
    return np.array(probs)


def get_level(p):
    if p < THRESHOLD_NORMAL: return "正常"
    elif p < THRESHOLD_MILD: return "轻度"
    elif p < THRESHOLD_MODERATE: return "中度"
    else: return "重度"


def control_none(base_probs):
    return [{"layer": i, "prob": float(base_probs[i]),
             "level": get_level(base_probs[i]), "action": "无",
             "laser_power": BASE_LASER_POWER} for i in range(N_LAYERS)], 0


def control_pid(base_probs):
    probs = base_probs.copy()
    laser_power = BASE_LASER_POWER
    integral = 0.0
    prev_error = 0.0
    Kp, Ki, Kd = 80.0, 2.0, 10.0
    records = []
    adjust_count = 0
    
    for layer in range(N_LAYERS):
        p = probs[layer]
        error = max(0, p - THRESHOLD_NORMAL)
        integral += error
        derivative = error - prev_error
        correction = Kp * error + Ki * integral + Kd * derivative
        new_power = np.clip(BASE_LASER_POWER - correction, 100, 400)
        if abs(new_power - laser_power) > 1:
            adjust_count += 1
        laser_power = new_power
        
        if layer < N_LAYERS - 1:
            power_drop = (BASE_LASER_POWER - laser_power) / BASE_LASER_POWER
            effect = CONTROL_EFFECT * power_drop
            probs[layer + 1] = max(0.02, probs[layer + 1] - effect * 0.5)
        
        prev_error = error
        records.append({"layer": layer, "prob": float(p),
                        "level": get_level(p), "action": "PID",
                        "laser_power": float(laser_power)})
    return records, adjust_count


def control_fixed_threshold(base_probs):
    probs = base_probs.copy()
    laser_power = BASE_LASER_POWER
    records = []
    adjust_count = 0
    
    for layer in range(N_LAYERS):
        p = probs[layer]
        if p > THRESHOLD_MILD:
            laser_power *= 0.95
            laser_power = np.clip(laser_power, 100, 400)
            adjust_count += 1
            if layer < N_LAYERS - 1:
                probs[layer + 1] = max(0.02, probs[layer + 1] - 0.15)
        
        records.append({"layer": layer, "prob": float(p),
                        "level": get_level(p), "action": "固定阈值",
                        "laser_power": float(laser_power)})
    return records, adjust_count


def control_proposed(base_probs):
    probs = base_probs.copy()
    laser_power = BASE_LASER_POWER
    scan_speed = BASE_SCAN_SPEED
    records = []
    adjust_count = 0
    oscillation_flag = False
    
    for layer in range(N_LAYERS):
        p = probs[layer]
        level = get_level(p)
        
        if level == "正常":
            action = "记录"
        elif level == "轻度":
            action = "标记"
        elif level == "中度":
            if not oscillation_flag:
                action = "调整参数"
                laser_power *= 0.93
                scan_speed *= 1.12
                laser_power = np.clip(laser_power, 100, 400)
                scan_speed = np.clip(scan_speed, 200, 2000)
                adjust_count += 1
                if layer < N_LAYERS - 1:
                    effect = CONTROL_EFFECT * (1 - laser_power / BASE_LASER_POWER)
                    probs[layer + 1] = max(0.02, probs[layer + 1] - effect)
            else:
                action = "振荡保护"
        else:
            action = "暂停打印"
            if layer < N_LAYERS - 1:
                probs[layer + 1] = max(0.02, probs[layer + 1] - 0.35)
        
        records.append({"layer": layer, "prob": float(p),
                        "level": level, "action": action,
                        "laser_power": float(laser_power)})
    return records, adjust_count


def summarize(records, name):
    from collections import Counter
    levels = Counter(r["level"] for r in records)
    total = len(records)
    print(f"\n[{name}]")
    for level in ["正常", "轻度", "中度", "重度"]:
        count = levels.get(level, 0)
        print(f"    {level}: {count}层 ({count/total*100:.1f}%)")
    return {level: levels.get(level, 0) / total for level in ["正常", "轻度", "中度", "重度"]}


def main():
    print("=" * 60)
    print("闭环控制基线对比实验 v4")
    print("=" * 60)
    
    base_probs = generate_base_sequence(42)
    print(f"\n基础缺陷序列: 均值={base_probs.mean():.3f}, 最大={base_probs.max():.3f}, 最小={base_probs.min():.3f}")
    
    rec_none, adj_none = control_none(base_probs)
    rec_pid, adj_pid = control_pid(base_probs)
    rec_fixed, adj_fixed = control_fixed_threshold(base_probs)
    rec_prop, adj_prop = control_proposed(base_probs)
    
    print(f"\n{'=' * 60}")
    print(f"闭环控制性能对比")
    print(f"{'=' * 60}")
    
    res_none = summarize(rec_none, "Baseline 1: 无控制")
    res_pid = summarize(rec_pid, "Baseline 2: PID控制")
    res_fixed = summarize(rec_fixed, "Baseline 3: 固定阈值控制")
    res_prop = summarize(rec_prop, "Proposed: 分级自适应 + 防振荡")
    
    print(f"\n参数调整次数:")
    print(f"    PID控制: {adj_pid}")
    print(f"    固定阈值: {adj_fixed}")
    print(f"    提出的方法: {adj_prop}")
    
    results = {
        "no_control": res_none,
        "pid": {**res_pid, "adjust_count": adj_pid},
        "fixed_threshold": {**res_fixed, "adjust_count": adj_fixed},
        "proposed": {**res_prop, "adjust_count": adj_prop},
    }
    with open(OUTPUT_DIR / "control_baseline_v4_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {OUTPUT_DIR / 'control_baseline_v4_results.json'}")


if __name__ == "__main__":
    main()