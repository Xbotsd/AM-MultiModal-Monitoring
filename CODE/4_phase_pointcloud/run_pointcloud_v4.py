# -*- coding: utf-8 -*-
"""
点云仿真与处理 v4 - 滑动窗口峰值检测
调用口令：SCP111
运行: py -3.12 run_pointcloud_v4.py
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
from collections import defaultdict

OUTPUT_DIR = Path("data/pointcloud")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(42)

print("=" * 60)
print("点云仿真与处理 v4 - 滑动窗口峰值检测")
print("=" * 60)

# ---------- 1. 生成基准平面 ----------
x = np.arange(0, 100, 0.5)
y = np.arange(0, 100, 0.5)
xx, yy = np.meshgrid(x, y)
points = np.stack([xx.ravel(), yy.ravel(), np.zeros_like(xx).ravel()], axis=1).astype(np.float64)
print(f"\n[1] 基准平面: {len(points)} 点")

# ---------- 2. 翘曲 ----------
center = np.array([50.0, 50.0])
sigma = 10.0
warp = 0.5 * np.exp(-np.sum((points[:, :2] - center)**2, axis=1) / (2 * sigma**2))
points[:, 2] += warp

# ---------- 3. 球化 ----------
n_balling = 20
balling_info = []
for _ in range(n_balling):
    cx, cy = np.random.uniform(10, 90, 2)
    r = np.random.uniform(2, 5)
    h = np.random.uniform(0.2, 0.5)
    balling_info.append((float(cx), float(cy), float(r), float(h)))
    dist = np.sqrt((points[:, 0] - cx)**2 + (points[:, 1] - cy)**2)
    mask = dist < r
    points[mask, 2] += h * np.cos(dist[mask] / r * np.pi / 2)
print(f"[2] 翘曲: 最大 {warp.max():.3f} mm")
print(f"[3] 球化: {n_balling} 个")

# ---------- 4. 噪声 ----------
points[:, 2] += np.random.normal(0, 0.02, len(points))

# ---------- 5. 离群点 ----------
n_outliers = int(0.05 * len(points))
outliers = np.column_stack([
    np.random.uniform(0, 100, (n_outliers, 2)),
    np.random.uniform(-0.5, 1.5, n_outliers)
])
points_with_outliers = np.vstack([points, outliers])

# ---------- 6. SOR去噪 + Z范围过滤 ----------
print(f"\n[6] SOR去噪 + Z范围过滤...")
def sor(points, k=20, std_ratio=1.0):
    cell_size = 2.0
    grid = defaultdict(list)
    for i, p in enumerate(points):
        grid[(int(p[0]//cell_size), int(p[1]//cell_size))].append(i)
    mean_dists = np.zeros(len(points))
    for i, p in enumerate(points):
        key = (int(p[0]//cell_size), int(p[1]//cell_size))
        neighbors = []
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                neighbors.extend(grid.get((key[0]+dx, key[1]+dy), []))
        if len(neighbors) < k+1:
            mean_dists[i] = 0
            continue
        dists = np.sqrt(np.sum((points[neighbors] - p)**2, axis=1))
        mean_dists[i] = np.mean(np.partition(dists, k)[:k])
    threshold = np.mean(mean_dists) + std_ratio * np.std(mean_dists)
    return mean_dists < threshold

mask = sor(points_with_outliers, k=20, std_ratio=1.0)
points_clean = points_with_outliers[mask]

# Z范围过滤：|Z| > 0.8mm 视为异常（保留翘曲0.5+球化0.5+噪声）
z_filter = np.abs(points_clean[:, 2]) < 0.8
points_clean = points_clean[z_filter]
print(f"    去噪+过滤后: {len(points_clean)}")

# ---------- 7. 滑动窗口峰值检测 ----------
print(f"\n[7] 滑动窗口峰值检测 (window=2.0mm, threshold=0.3mm)...")
def sliding_window_defect(points, window=2.0, threshold=0.3):
    """在每个空间窗口内找Z最大值，若超过阈值则标记为缺陷"""
    grid = defaultdict(list)
    for p in points:
        grid[(int(p[0]//window), int(p[1]//window))].append(p)
    
    defect_peaks = []
    all_peaks = []
    for key, pts in grid.items():
        pts_arr = np.array(pts)
        max_z_idx = np.argmax(pts_arr[:, 2])
        peak = pts_arr[max_z_idx]
        all_peaks.append(peak)
        if peak[2] > threshold:
            defect_peaks.append(peak)
    
    return np.array(defect_peaks), np.array(all_peaks)

defect_peaks, all_peaks = sliding_window_defect(points_clean, window=2.0, threshold=0.3)
print(f"    总窗口数: {len(all_peaks)}")
print(f"    缺陷窗口数: {len(defect_peaks)}")

# ---------- 8. 缺陷区域聚类 ----------
print(f"\n[8] 缺陷区域聚类...")
def cluster_defects(peaks, distance=5.0):
    """简单距离聚类"""
    if len(peaks) == 0:
        return []
    visited = [False] * len(peaks)
    clusters = []
    for i in range(len(peaks)):
        if visited[i]:
            continue
        cluster = [i]
        visited[i] = True
        queue = [i]
        while queue:
            j = queue.pop(0)
            for k in range(len(peaks)):
                if not visited[k]:
                    d = np.sqrt(np.sum((peaks[j][:2] - peaks[k][:2])**2))
                    if d < distance:
                        visited[k] = True
                        cluster.append(k)
                        queue.append(k)
        clusters.append(cluster)
    return clusters

clusters = cluster_defects(defect_peaks, distance=5.0)
print(f"    聚类后缺陷区域数: {len(clusters)}")

# 每个聚类取最高点
cluster_centers = []
for cluster in clusters:
    pts = defect_peaks[cluster]
    max_idx = np.argmax(pts[:, 2])
    center = pts[max_idx]
    cluster_centers.append(center)
    print(f"      区域: 中心({center[0]:.1f}, {center[1]:.1f}), 高度{center[2]:.3f} mm, {len(cluster)}个点")

# ---------- 9. 球化检出率评估 ----------
print(f"\n[9] 真实球化 vs 检测结果:")
detected_count = 0
for cx, cy, r, h in balling_info:
    is_detected = False
    for center in cluster_centers:
        d = np.sqrt((center[0]-cx)**2 + (center[1]-cy)**2)
        if d < r + 2.0:  # 容差2mm
            is_detected = True
            break
    status = "✅ 检出" if is_detected else "❌ 漏检"
    if is_detected:
        detected_count += 1
    print(f"    球化({cx:.1f}, {cy:.1f}), r={r:.1f}, h={h:.2f}: {status}")

print(f"\n    球化检出率: {detected_count}/{n_balling} = {detected_count/n_balling*100:.1f}%")

# ---------- 10. 保存 ----------
np.save(OUTPUT_DIR / "points_clean_v4.npy", points_clean)
np.save(OUTPUT_DIR / "defect_peaks_v4.npy", defect_peaks)
np.save(OUTPUT_DIR / "cluster_centers_v4.npy", np.array(cluster_centers))

config = {
    "window_size": 2.0,
    "defect_threshold": 0.3,
    "n_defect_windows": int(len(defect_peaks)),
    "n_clusters": int(len(clusters)),
    "balling_detection_rate": f"{detected_count}/{n_balling}",
}
with open(OUTPUT_DIR / "config_v4.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f"\n{'=' * 60}")
print(f"v4 完成！球化检出率: {detected_count/n_balling*100:.1f}%")
print(f"{'=' * 60}")