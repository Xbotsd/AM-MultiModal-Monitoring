# -*- coding: utf-8 -*-
"""
闭环控制与追溯验证 v3 - 参数调优版
调用口令：SCP111
运行: py -3.12 run_closed_loop_v3.py
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
from datetime import datetime, timedelta

OUTPUT_DIR = Path("data/closed_loop")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(42)

print("=" * 60)
print("闭环控制与追溯验证 v3")
print("=" * 60)

# ============================================================
# 参数配置（v3调优）
# ============================================================
N_LAYERS = 100
BASE_LASER_POWER = 200.0
BASE_SCAN_SPEED = 800.0
BASE_HATCH_SPACING = 100.0

# 缺陷演化参数（v3调整后）
BASE_DEFECT = 0.20          # 从0.15提到0.20
EVENT_PROB = 0.25           # 从0.10提到0.25
EVENT_MAGNITUDE = 0.50      # 从0.35提到0.50
RECOVERY_RATE = 0.05        # 从0.30降到0.05
CONTROL_EFFECT = 0.60       # 从0.50提到0.60

THRESHOLD_NORMAL = 0.3
THRESHOLD_MILD = 0.5
THRESHOLD_MODERATE = 0.8

OSCILLATION_WINDOW = 5
OSCILLATION_MAX_FAIL = 3

print(f"\n[配置]")
print(f"  层数: {N_LAYERS}")
print(f"  基础缺陷概率: {BASE_DEFECT}")
print(f"  异常事件概率: {EVENT_PROB}")
print(f"  异常事件强度: {EVENT_MAGNITUDE}")
print(f"  自然恢复率: {RECOVERY_RATE}")
print(f"  控制效果: {CONTROL_EFFECT}")

# ============================================================
# 状态初始化
# ============================================================
records = []
laser_power = BASE_LASER_POWER
scan_speed = BASE_SCAN_SPEED
hatch_spacing = BASE_HATCH_SPACING

current_prob = BASE_DEFECT
adjust_history = []
oscillation_flag = False
start_time = datetime.now()
control_applied = False

print(f"\n[1] 执行 {N_LAYERS} 层闭环控制...")

for layer in range(N_LAYERS):
    # ---------- 缺陷演化 ----------
    current_prob = current_prob * (1 - RECOVERY_RATE)

    if np.random.rand() < EVENT_PROB:
        current_prob += np.random.uniform(0.1, EVENT_MAGNITUDE)

    if control_applied:
        current_prob = current_prob * (1 - CONTROL_EFFECT)
        control_applied = False

    current_prob += np.random.normal(0, 0.02)
    current_prob = np.clip(current_prob, 0.0, 1.0)

    # ---------- 缺陷类型 ----------
    if current_prob >= THRESHOLD_MODERATE:
        defect_type = "keyhole_porosity"
    elif current_prob >= THRESHOLD_MILD:
        defect_type = "cracking"
    elif current_prob >= THRESHOLD_NORMAL:
        defect_type = "lack_of_fusion"
    else:
        defect_type = "normal"

    # ---------- 分级响应 ----------
    timestamp = (start_time + timedelta(seconds=layer * 1.5)).isoformat()

    if current_prob < THRESHOLD_NORMAL:
        level = "正常"
        action = "记录"
        command = {}
    elif current_prob < THRESHOLD_MILD:
        level = "轻度"
        action = "标记"
        command = {}
    elif current_prob < THRESHOLD_MODERATE:
        level = "中度"
        if not oscillation_flag:
            action = "调整参数"
            if defect_type == "keyhole_porosity":
                laser_power *= np.random.uniform(0.90, 0.95)
                scan_speed *= np.random.uniform(1.10, 1.15)
            elif defect_type == "cracking":
                laser_power *= np.random.uniform(0.95, 0.98)
                hatch_spacing *= np.random.uniform(0.95, 0.98)
            else:
                laser_power *= np.random.uniform(1.05, 1.10)
                scan_speed *= np.random.uniform(0.90, 0.95)

            laser_power = np.clip(laser_power, 100, 400)
            scan_speed = np.clip(scan_speed, 200, 2000)
            hatch_spacing = np.clip(hatch_spacing, 50, 150)

            command = {
                "laser_power": round(laser_power, 1),
                "scan_speed": round(scan_speed, 1),
                "hatch_spacing": round(hatch_spacing, 1)
            }
            control_applied = True

            adjust_history.append({
                "layer": layer,
                "effect": CONTROL_EFFECT * np.random.uniform(0.7, 1.3)
            })
            if len(adjust_history) > OSCILLATION_WINDOW:
                adjust_history.pop(0)

            recent = [h["effect"] for h in adjust_history[-OSCILLATION_MAX_FAIL:]]
            if len(recent) >= OSCILLATION_MAX_FAIL and all(e < 0.3 for e in recent):
                oscillation_flag = True
        else:
            action = "振荡保护"
            command = {"flag": "oscillation_guard"}
    else:
        level = "重度"
        action = "暂停打印"
        command = {"command": "PAUSE"}

    # ---------- 记录 ----------
    records.append({
        "layer": layer,
        "timestamp": timestamp,
        "defect_probability": round(float(current_prob), 4),
        "defect_type": defect_type,
        "severity_level": level,
        "action": action,
        "laser_power": round(laser_power, 1),
        "scan_speed": round(scan_speed, 1),
        "hatch_spacing": round(hatch_spacing, 1),
        "command": command,
        "oscillation_flag": oscillation_flag
    })

print(f"  记录层数: {len(records)}")

# ============================================================
# 统计
# ============================================================
print(f"\n[2] 统计汇总:")
level_counts = {}
for r in records:
    level_counts[r["severity_level"]] = level_counts.get(r["severity_level"], 0) + 1

print(f"  严重程度分布:")
for level in ["正常", "轻度", "中度", "重度"]:
    count = level_counts.get(level, 0)
    print(f"    {level}: {count} 层 ({count/N_LAYERS*100:.1f}%)")

adjust_count = sum(1 for r in records if r["action"] == "调整参数")
pause_count = sum(1 for r in records if r["action"] == "暂停打印")
oscillation_count = sum(1 for r in records if r["oscillation_flag"])

print(f"  参数调整次数: {adjust_count}")
print(f"  暂停次数: {pause_count}")
print(f"  振荡保护触发: {'是' if oscillation_count > 0 else '否'}")

# ============================================================
# 追溯报告
# ============================================================
print(f"\n[3] 生成追溯报告...")

report = {
    "build_id": "LPBF-2026-09-29-003",
    "material": "316L",
    "process": "LPBF",
    "total_layers": N_LAYERS,
    "start_time": start_time.isoformat(),
    "end_time": (start_time + timedelta(seconds=N_LAYERS * 1.5)).isoformat(),
    "final_status": "completed" if pause_count == 0 else "paused",
    "summary": {
        "normal_layers": level_counts.get("正常", 0),
        "mild_layers": level_counts.get("轻度", 0),
        "moderate_layers": level_counts.get("中度", 0),
        "severe_layers": level_counts.get("重度", 0),
        "adjustments": adjust_count,
        "pauses": pause_count,
        "oscillation_guard_triggered": oscillation_count > 0
    },
    "final_parameters": {
        "laser_power": round(laser_power, 1),
        "scan_speed": round(scan_speed, 1),
        "hatch_spacing": round(hatch_spacing, 1)
    },
    "traceability": {
        "forward": "零件→缺陷→传感器数据",
        "reverse": "异常信号→缺陷类型→影响区域",
        "standard": "ASTM E3353 / NASA-STD-6016A"
    },
    "layer_records": records
}

with open(OUTPUT_DIR / "traceability_report_v3.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

key_records = [r for r in records if r["severity_level"] in ("中度", "重度")]
with open(OUTPUT_DIR / "key_events_v3.json", "w", encoding="utf-8") as f:
    json.dump(key_records, f, indent=2, ensure_ascii=False)

print(f"  完整报告: {OUTPUT_DIR / 'traceability_report_v3.json'}")
print(f"  关键事件: {OUTPUT_DIR / 'key_events_v3.json'}")

# ============================================================
# 论文指标
# ============================================================
print(f"\n[4] 论文指标:")
detection_rate = (adjust_count + pause_count) / N_LAYERS * 100
print(f"  异常响应率: {detection_rate:.1f}%")
print(f"  参数调整占比: {adjust_count/N_LAYERS*100:.1f}%")
print(f"  暂停占比: {pause_count/N_LAYERS*100:.1f}%")
print(f"  最终激光功率: {laser_power:.1f} W (初始 {BASE_LASER_POWER} W)")
print(f"  最终扫描速度: {scan_speed:.1f} mm/s (初始 {BASE_SCAN_SPEED} mm/s)")

print(f"\n{'=' * 60}")
print(f"v3 完成！")
print(f"{'=' * 60}")