import numpy as np

# 加载标签文件
labels = np.load('data/epfl_acoustic/Deciphering AE/D1_classspace_5000.npy')

# 分别打印每个类别对应的前10个原始标签值
for class_id, class_name in enumerate(['LoF', 'Conduction', 'Keyhole']):
    indices = np.where(labels == class_id)[0][:10]
    print(f"类别 {class_name} (标签值 {class_id}): 前10个索引位置 {indices}")