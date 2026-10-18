# -*- coding: utf-8 -*-
import os
import shutil
import sys
from pathlib import Path

# 获取当前目录
ROOT = Path(__file__).resolve().parent

# 你的代码所在的文件夹名称（根据你的截图，是 CODE）
CODE_DIR = ROOT / "CODE"

# 文件分类字典
FILE_MAP = {
    "1_acoustic": [
        "run_acoustic_ablation.py", "run_acoustic_baseline_v2.py",
        "run_eplf_cross_subset.py", "run_eplf_v12.py",
        "run_stat_cv_acoustic.py", "run_stat_features.py"
    ],
    "2_laser_ultrasound": [
        "prepare_lu_v3.py", "run_lu_v2.py", "run_stat_cv_lu.py"
    ],
    "3_fusion": [
        "run_fusion_baseline.py", "run_fusion_combinations.py",
        "run_fusion_sim.py", "run_sensitivity_full.py"
    ],
    "4_phase_pointcloud": [
        "run_phase_unwrap_v4.py", "run_unwrap_baseline.py",
        "run_pointcloud_v4.py"
    ],
    "5_control": [
        "run_closed_loop_v3.py", "run_control_baseline_v4.py",
        "offline_diagnosis.py"
    ],
    "6_visualization": [
        "run_complexity.py", "run_confusion_matrix.py",
        "run_feature_correlation.py", "run_figure_pipeline.py",
        "run_roc_auc.py", "run_tsne.py",
        "run_stat_repeat.py", "run_visualization_full.py"
    ]
}

def create_configs():
    print("正在生成配置文件...")
    # 1. requirements.txt
    req_content = """numpy>=1.26
scipy>=1.11
matplotlib>=3.8
scikit-learn>=1.4
PyWavelets>=1.5
sounddevice>=0.4.6
opencv-python>=4.8.0
"""
    (ROOT / "requirements.txt").write_text(req_content, encoding="utf-8")

    # 2. .gitignore
    ignore_content = """# Data files
data/
*.npy
*.mat
*.rar

# Outputs
outputs/
data_output/
*.png
*.tif

# Python cache
__pycache__/
*.pyc
.DS_Store
"""
    (ROOT / ".gitignore").write_text(ignore_content, encoding="utf-8")

    # 3. README.md (去除了导致报错的 Markdown 语法)
    readme_content = """# AM-MultiModal-Monitoring
**Laser Powder Bed Fusion (LPBF) In-Situ Monitoring System**

This repository contains the official code for the paper: "A Unified Kalman Filter Framework with Offline Edge Intelligence for Multi-Modal In-Situ Monitoring in LPBF and DED".

## Project Structure
- 1_acoustic: Acoustic emission classification (EPFL dataset)
- 2_laser_ultrasound: Laser ultrasound classification (Cranfield dataset)
- 3_fusion: Unified Kalman filter multi-modal fusion
- 4_phase_pointcloud: Phase unwrapping and point cloud defect detection
- 5_control: Closed-loop control and offline edge diagnosis
- 6_visualization: Statistical analysis and figure generation

## Quick Start
1. Install dependencies:
   pip install -r requirements.txt

2. Run a specific module (e.g., acoustic experiment):
   python CODE/1_acoustic/run_eplf_v12.py

## Datasets
- EPFL Acoustic Dataset: https://zenodo.org/records/10449883
- Cranfield LUT Dataset: https://doi.org/10.17862/cranfield.rd.15190191
"""
    (ROOT / "README.md").write_text(readme_content, encoding="utf-8")
    print("配置文件生成完毕！")

def fix_python_paths(file_path):
    """自动修改代码中的相对路径"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 如果已经修改过，就跳过
    if "os.chdir(ROOT_DIR)" in content:
        return

    # 动态插入环境变量代码
    injection = """# --- AUTO INJECTED PATH FIX ---
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT_DIR)
# ------------------------------
"""
    # 插在 import 语句后面（找第一个 import）
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i
            break
    
    lines.insert(insert_idx, injection)
    new_content = '\n'.join(lines)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    print("开始整理项目结构...")
    
    if not CODE_DIR.exists():
        print(f"找不到 {CODE_DIR} 文件夹，请确保脚本放在 am_monitoring 目录下，且里面有 CODE 文件夹！")
        return

    create_configs()

    for folder, files in FILE_MAP.items():
        target_dir = CODE_DIR / folder
        target_dir.mkdir(exist_ok=True)
        
        for py_file in files:
            src = CODE_DIR / py_file
            dst = target_dir / py_file
            
            if src.exists():
                # 1. 移动文件
                shutil.move(str(src), str(dst))
                # 2. 自动修复该文件的路径
                fix_python_paths(dst)
                print(f"已移动并修复: {folder}/{py_file}")
            else:
                print(f"找不到文件: {py_file}")

    print("\n整理完成！现在你可以直接把整个文件夹提交到 GitHub 了！")

# 就是这里！注意这行和下一行的缩进！
if __name__ == "__main__":
    main()