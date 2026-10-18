# -*- coding: utf-8 -*-
"""
离线边缘智能诊断模块
完全本地化，无需API，替代云端诊断
调用口令：SCP111
运行: py -3.12 offline_diagnosis.py
"""
# --- AUTO INJECTED PATH FIX ---
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT_DIR)
# ------------------------------

import json
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger("offline_diagnosis")


# ============================================================
# 本地结构化知识库
# ============================================================
class LocalKnowledgeBase:
    def __init__(self):
        self.defect_rules = {
            "keyhole_porosity": {
                "cause": "激光能量密度过高，匙孔不稳定导致气泡被卷入熔池",
                "actions": [
                    {"param": "laser_power", "delta": "-5~10%", "reason": "降低能量密度"},
                    {"param": "scan_speed", "delta": "+10~15%", "reason": "缩短熔池停留时间"},
                    {"param": "defocus", "delta": "+0.2mm", "reason": "扩大光斑，降低峰值温度"},
                ],
                "severity": "medium",
                "reference": "King et al., J. Mater. Process. Technol., 2014",
            },
            "cracking": {
                "cause": "热应力超过材料抗拉强度，残余应力集中导致裂纹",
                "actions": [
                    {"param": "laser_power", "delta": "-5%", "reason": "降低热输入"},
                    {"param": "preheat_temp", "delta": "+50~100°C", "reason": "降低温度梯度"},
                    {"param": "scan_strategy", "delta": "改用岛状扫描", "reason": "分散热应力"},
                ],
                "severity": "high",
                "reference": "Mercelis & Kruth, Rapid Prototyp. J., 2006",
            },
            "lack_of_fusion": {
                "cause": "激光能量密度不足，粉末未完全熔化导致层间未结合",
                "actions": [
                    {"param": "laser_power", "delta": "+10~15%", "reason": "提高能量密度"},
                    {"param": "scan_speed", "delta": "-10%", "reason": "延长熔池停留时间"},
                    {"param": "layer_thickness", "delta": "-20%", "reason": "降低层厚保证熔透"},
                ],
                "severity": "high",
                "reference": "Tang et al., Addit. Manuf., 2017",
            },
            "balling": {
                "cause": "熔池表面张力过大，液态金属未能润湿基底形成球化",
                "actions": [
                    {"param": "laser_power", "delta": "+5~10%", "reason": "提高润湿性"},
                    {"param": "scan_speed", "delta": "-10~15%", "reason": "降低冷却速率"},
                    {"param": "oxygen_content", "delta": "<100ppm", "reason": "控制氧含量"},
                ],
                "severity": "medium",
                "reference": "Gu & Shen, J. Manuf. Process., 2008",
            },
            "high_porosity": {
                "cause": "多种因素耦合，需要综合分析",
                "actions": [
                    {"param": "laser_power", "delta": "±5%", "reason": "微调能量密度"},
                    {"param": "hatch_spacing", "delta": "-10%", "reason": "增加搭接率"},
                    {"param": "inspect_powder", "delta": "筛分/干燥", "reason": "排除粉末因素"},
                ],
                "severity": "medium",
                "reference": "Cunningham et al., Addit. Manuf., 2019",
            },
            "normal": {
                "cause": "工艺状态正常",
                "actions": [
                    {"param": "continue", "delta": "无调整", "reason": "继续监测"},
                ],
                "severity": "low",
                "reference": "N/A",
            },
        }
        self.param_limits = {
            "laser_power": {"min": 100, "max": 400, "unit": "W"},
            "scan_speed": {"min": 200, "max": 2000, "unit": "mm/s"},
            "layer_thickness": {"min": 20, "max": 60, "unit": "μm"},
            "hatch_spacing": {"min": 50, "max": 150, "unit": "μm"},
            "preheat_temp": {"min": 20, "max": 400, "unit": "°C"},
        }
        self.severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}

    def query(self, defect_type):
        return self.defect_rules.get(defect_type, self.defect_rules["normal"])

    def validate_param(self, param, value):
        if param not in self.param_limits:
            return True, value
        limits = self.param_limits[param]
        if value < limits["min"]:
            return False, limits["min"]
        if value > limits["max"]:
            return False, limits["max"]
        return True, value


# ============================================================
# 规则引擎
# ============================================================
class RuleEngine:
    def __init__(self, knowledge_base):
        self.kb = knowledge_base

    def diagnose(self, acoustic_defect=None, porosity=0.0,
                 printwatch_defect=None, extra_context=None):
        log.info("[离线诊断] 开始多源综合诊断")
        candidates = []

        if acoustic_defect and acoustic_defect != "normal":
            candidates.append({
                "type": acoustic_defect,
                "source": "声学分析",
                "confidence": 0.85,
            })
        if porosity > 0.10:
            candidates.append({
                "type": "high_porosity",
                "source": "图像分析",
                "confidence": 0.92,
                "value": f"{porosity:.1%}",
            })
        elif porosity > 0.05:
            candidates.append({
                "type": "high_porosity",
                "source": "图像分析",
                "confidence": 0.75,
                "value": f"{porosity:.1%}",
            })
        if printwatch_defect and printwatch_defect not in ("none", "unknown", None):
            candidates.append({
                "type": printwatch_defect,
                "source": "实时监控",
                "confidence": 0.70,
            })

        if not candidates:
            rule = self.kb.query("normal")
            return {
                "status": "ok",
                "mode": "offline_rule_engine",
                "overall_status": "正常",
                "defect_type": "normal",
                "confidence": 1.0,
                "cause": rule["cause"],
                "severity": rule["severity"],
                "actions": rule["actions"],
                "recommendations": ["继续监测，无需调整"],
                "timestamp": datetime.now().isoformat(),
            }

        primary = max(candidates, key=lambda x: x["confidence"])
        rule = self.kb.query(primary["type"])
        recommendations = []
        for action in rule["actions"]:
            if action["param"] == "continue":
                recommendations.append(action["reason"])
            else:
                recommendations.append(
                    f"{action['param']} {action['delta']} ({action['reason']})"
                )

        result = {
            "status": "ok",
            "mode": "offline_rule_engine",
            "overall_status": "异常",
            "defect_type": primary["type"],
            "confidence": primary["confidence"],
            "cause": rule["cause"],
            "severity": rule["severity"],
            "severity_level": self.kb.severity_map.get(rule["severity"], 0),
            "actions": rule["actions"],
            "recommendations": recommendations,
            "all_candidates": candidates,
            "reference": rule["reference"],
            "timestamp": datetime.now().isoformat(),
        }
        log.info(f"[离线诊断] 缺陷={primary['type']}, 严重程度={rule['severity']}")
        log.info(f"[离线诊断] 建议: {'; '.join(recommendations)}")
        return result


# ============================================================
# 闭环控制指令生成器
# ============================================================
class ClosedLoopController:
    def __init__(self, knowledge_base, current_params=None):
        self.kb = knowledge_base
        self.current_params = current_params or {
            "laser_power": 200,
            "scan_speed": 800,
            "layer_thickness": 30,
            "hatch_spacing": 100,
            "preheat_temp": 20,
        }

    def generate_commands(self, diagnosis_result):
        log.info("[闭环控制] 生成参数调整指令")
        if diagnosis_result["overall_status"] == "正常":
            return {"action": "continue", "commands": [], "message": "无需调整"}

        severity_level = diagnosis_result.get("severity_level", 0)
        if severity_level >= 4 or diagnosis_result["defect_type"] == "cracking":
            return {
                "action": "pause",
                "commands": [],
                "message": f"检测到{diagnosis_result['defect_type']}，立即停机",
            }

        commands = []
        for action in diagnosis_result["actions"]:
            param = action["param"]
            delta_str = action["delta"]
            if param not in self.current_params:
                continue
            current = self.current_params[param]
            new_value = self._parse_delta(current, delta_str)
            valid, new_value = self.kb.validate_param(param, new_value)
            commands.append({
                "param": param,
                "old_value": current,
                "new_value": round(new_value, 2),
                "valid": valid,
                "reason": action["reason"],
            })
            if valid:
                self.current_params[param] = new_value

        return {
            "action": "adjust",
            "commands": commands,
            "message": f"调整 {len(commands)} 个参数以抑制 {diagnosis_result['defect_type']}",
        }

    def _parse_delta(self, current, delta_str):
        if "~" in delta_str:
            parts = delta_str.replace("%", "").split("~")
            avg_delta = sum(float(p) for p in parts) / 2
        elif "%" in delta_str:
            avg_delta = float(delta_str.replace("%", ""))
        elif "±" in delta_str:
            avg_delta = float(delta_str.replace("±", "").replace("%", ""))
        else:
            num = float("".join(c for c in delta_str if c.isdigit() or c in ".-"))
            return current + num
        return current * (1 + avg_delta / 100)


# ============================================================
# 主入口：离线诊断管道
# ============================================================
def offline_diagnosis_pipeline(acoustic_result, image_result, realtime_result):
    log.info("=" * 60)
    log.info("[Node 4] 离线智能诊断管道")
    log.info("=" * 60)

    kb = LocalKnowledgeBase()
    engine = RuleEngine(kb)
    controller = ClosedLoopController(kb)

    ae = acoustic_result.get("audio_ml", {})
    acoustic_defect = ae.get("defect_type") if ae.get("status") == "ok" else None

    pm = image_result.get("porme", {})
    porosity = pm.get("porosity", 0.0) if pm.get("status") == "ok" else 0.0

    pw = realtime_result.get("printwatch", {})
    printwatch_defect = pw.get("defect_type") if pw.get("defect_detected") else None

    diagnosis = engine.diagnose(
        acoustic_defect=acoustic_defect,
        porosity=porosity,
        printwatch_defect=printwatch_defect,
    )
    control = controller.generate_commands(diagnosis)

    return {
        "m3dp_uip": {
            "status": "ok",
            "mode": "offline_rule_engine",
            "diagnosis": diagnosis["cause"],
            "confidence": diagnosis["confidence"],
            "recommendations": diagnosis["recommendations"],
            "defect_type": diagnosis["defect_type"],
            "severity": diagnosis["severity"],
        },
        "closed_loop": control,
        "diagnosis_detail": diagnosis,
    }


# ============================================================
# 独立测试
# ============================================================
if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("\n" + "=" * 60)
    print("测试场景1：正常状态")
    print("=" * 60)
    result = offline_diagnosis_pipeline(
        acoustic_result={"audio_ml": {"status": "ok", "defect_type": "normal"}},
        image_result={"porme": {"status": "ok", "porosity": 0.02}},
        realtime_result={"printwatch": {"defect_detected": False}},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("测试场景2：匙孔孔隙")
    print("=" * 60)
    result = offline_diagnosis_pipeline(
        acoustic_result={"audio_ml": {"status": "ok", "defect_type": "keyhole_porosity"}},
        image_result={"porme": {"status": "ok", "porosity": 0.03}},
        realtime_result={"printwatch": {"defect_detected": False}},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("测试场景3：裂纹（立即停机）")
    print("=" * 60)
    result = offline_diagnosis_pipeline(
        acoustic_result={"audio_ml": {"status": "ok", "defect_type": "cracking"}},
        image_result={"porme": {"status": "ok", "porosity": 0.05}},
        realtime_result={"printwatch": {"defect_detected": False}},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))