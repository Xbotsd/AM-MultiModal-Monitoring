# -*- coding: utf-8 -*-
"""
自动创建 .gitignore 文件
运行: py -3.12 create_gitignore.py
"""
from pathlib import Path

# .gitignore 内容
gitignore_content = """# 数据集和第三方仓库
data/
repos/

# Python 缓存
__pycache__/
*.pyc
*.pyo
*.pyd

# Jupyter 缓存
.ipynb_checkpoints/

# 期刊模板和论文文档
ijem模板.doc
IJEM项目论文.docx
References_IJEM.docx
EPFL记录.txt

# 系统文件
.DS_Store
Thumbs.db

# 编辑器配置
.vscode/
.idea/
"""

# 目标路径
target = Path(__file__).parent / ".gitignore"

# 写入文件
target.write_text(gitignore_content, encoding="utf-8")
print(f"✅ .gitignore 已创建: {target}")
print("\n文件内容:")
print("-" * 40)
print(gitignore_content)