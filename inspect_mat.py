# -*- coding: utf-8 -*-
"""
查看 .mat 文件内部结构
运行: py -3.12 inspect_mat.py
"""
import scipy.io as sio
from pathlib import Path
import numpy as np

# 文件路径
MAT_FILE = Path("data/laser_ultrasound/201120_Ti_FMC_128ave.mat")

if not MAT_FILE.exists():
    print(f"[错误] 文件不存在: {MAT_FILE}")
    print("请确认文件已放到 data/laser_ultrasound/ 目录下")
    exit()

# 加载
print(f"加载: {MAT_FILE.name}")
data = sio.loadmat(str(MAT_FILE))

# 打印所有变量
print("\n" + "=" * 60)
print("文件内所有变量")
print("=" * 60)

for key, value in data.items():
    if key.startswith("__"):
        continue
    if isinstance(value, np.ndarray):
        print(f"\n变量名: {key}")
        print(f"  形状: {value.shape}")
        print(f"  类型: {value.dtype}")
        if value.size > 0:
            print(f"  前5个值: {value.flatten()[:5]}")
    else:
        print(f"\n变量名: {key}")
        print(f"  类型: {type(value)}")
        print(f"  值: {value}")