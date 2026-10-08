# -*- coding: utf-8 -*-
"""
基于论文几何参数的物理标签生成（放宽版）
运行: py -3.12 prepare_lu_v3.py
"""
import numpy as np
import scipy.io as sio
from pathlib import Path

MAT_FILE = Path("data/laser_ultrasound/201120_Ti_FMC_128ave.mat")
OUTPUT_DIR = Path("data/laser_ultrasound")

# 加载
data = sio.loadmat(str(MAT_FILE))
signals = data['data'].T          # (4624, 1000)
time = data['time'].flatten()     # (1000,)

# 论文参数
N_ELEMENTS = 68
PITCH = 0.2e-3                    # 0.2 mm
C = 6100.0                        # m/s
DEFECT_DEPTH = 0.010              # 10 mm（论文最大成像深度）
DEFECT_X = 0.0                    # 假设缺陷在中心

# 阵元位置
pos = (np.arange(N_ELEMENTS) - (N_ELEMENTS - 1) / 2) * PITCH  # 中心为0

# 计算每条信号的几何 ToF
tof_geometric = np.zeros(4624)
k = 0
for i in range(N_ELEMENTS):
    for j in range(N_ELEMENTS):
        d1 = np.sqrt((pos[i] - DEFECT_X)**2 + DEFECT_DEPTH**2)
        d2 = np.sqrt((pos[j] - DEFECT_X)**2 + DEFECT_DEPTH**2)
        tof_geometric[k] = (d1 + d2) / C
        k += 1

# 对每条信号，找到最大绝对峰值对应的时间索引
peak_time = np.zeros(4624)
for k in range(4624):
    idx = np.argmax(np.abs(signals[k]))
    peak_time[k] = time[idx]

# 放宽容差：±1 ms（因为采样间隔50us，无法更精细）
tolerance = 1e-3
# 幅度阈值：峰值的70%分位数
amp = np.array([np.max(np.abs(signals[k])) for k in range(4624)])
amp_thresh = np.percentile(amp, 70)

# 标签：峰值时间接近几何 ToF 且幅度足够大 => 缺陷
labels = ((np.abs(peak_time - tof_geometric) < tolerance) &
          (amp > amp_thresh)).astype(int)

print(f"几何 ToF 范围: {tof_geometric.min()*1e6:.2f} ~ {tof_geometric.max()*1e6:.2f} μs")
print(f"实际峰值时间范围: {peak_time.min()*1e6:.2f} ~ {peak_time.max()*1e6:.2f} μs")
print(f"标签分布: 0={np.sum(labels==0)}, 1={np.sum(labels==1)}")

np.save(OUTPUT_DIR / "X_lu.npy", signals)
np.save(OUTPUT_DIR / "y_lu.npy", labels)
print("已保存 X_lu.npy, y_lu.npy")