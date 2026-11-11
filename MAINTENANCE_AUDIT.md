# 维护审计 · AM-MultiModal-Monitoring

审计时间：2026-11-11 19:55（Asia/Shanghai）
审计对象：本工作区 `C:\Users\lei'shen\Desktop\am_monitoring`
GitHub：https://github.com/Xbotsd/AM-MultiModal-Monitoring
Zenodo：https://zenodo.org/records/24128938（doi:10.5281/zenodo.24128938，concept 24128937）
上游理论库：https://github.com/Xbotsd/detectability-bound（Zenodo 24080213，v0.1.0）

---

## 一、三处对象的当前状态

| 对象 | 状态 | 核验方式 |
|---|---|---|
| 本地工作区 | `main` 在 `e6ca07d` 之上有本地提交（v1.1.0 修订），**尚未推送** | `git log` / `git status` |
| GitHub `main` | `e6ca07d`，tag `v1.0.0`，CI 最新 run 成功 | GitHub API |
| GitHub Release | `v1.0.0`（2026-11-11 07:42 UTC） | API `/releases` |
| Zenodo 记录 | v1.0.0，61 文件，133 703 B，md5 `e70bf94b…`；与 tag 逐字节一致 | Zenodo REST + 下载校验 |
| 论文（整合稿） | `NDTE_manuscript.docx/.pdf`，19:51 重建：35 阶段 / 14-9-12 / 20 测试 / v1.1.0 | 文本抽取核验 |

结论：**v1.0.0 的仓、Release、DOI 仍然自洽；v1.1.0 的修订已在本地完成，等待推送与 Zenodo New version。**

---

## 二、本轮修掉的问题（v1.1.0 主体）

### P0 — 论文的实测数字在仓库里复现不出来（已修）

v1.0.0 包里的 `3_fusion`、`4_phase_pointcloud`、`5_control` 全是仿真脚本，注册表也如实标
`simulated`；而论文表 4/5/6/7/8/9 的实测数字对应的真实脚本只在 `D:\new_project\_meas\`。
现在这些分析全部进仓库，且逐条实跑复现：

| 新阶段 | 输入（DOI） | 复现的论文数字（本机实跑） |
|---|---|---|
| `7_measured_real:run_fusion_real` | Peregrine 10.5281/zenodo.23727492 | RMSE 38.20 / 37.43 / 36.03 MPa；build-held-out 302.30 / 512.67 |
| `7_measured_real:run_decision_real` | 同上 | AUC 0.751；per-build 0.54–0.93；enrichment 2.25 |
| `7_measured_real:run_unwrap_real` | fringe 10.5281/zenodo.22125908 | 0.532 mm / 6.2 mm；四种改进均未更好（+5.3 / +1.6 / +1.2 / +0.4 %） |
| `7_measured_real:run_pointcloud_real` | WLI 10.5281/zenodo.21285367 | 稳健 s.d. 4.52 / 2.96 / 4.98 / 2.88 µm；10 µm 窗口命中 0 |
| `7_measured_real:run_xct_clutter` | XCT 10.5281/zenodo.17602110 | κ 31.2→125.2；跨重建 22.1/28.8/26.7 与 51.6/59.4/59.2；消融 115.1/105.9/49.5；POD 0.530/0.117/0.023 |
| `7_measured_real:run_lu_echo` | Cranfield 10.17862/cranfield.rd.15190191 | d′ 16.4/6.0；κ 0.99/0.98；POD 0.838/0.427；hold-out 88.2 % / AUC 0.947 |
| `1_acoustic:run_ae_spectral` | EPFL 10.5281/zenodo.10449883 | 64 band CV 88.88 % ± 0.35 %；d′ 2.83 / 3.02 / 3.12 |

每个脚本都：首行 docstring 写模块与数据来源 DOI；用仓库相对 `data/...` 路径并支持
`--data-root`；结果写 `results/*.json`；除 `--save-arrays` 外不落大数组。

### P0b — 图 1–6 的绘图脚本（已修）

新增 `6_visualization:run_ndte_figures`（derived）：六张图全部从 `results/*.json` 和
`dbound` 计算得到，不手抄任何数字；系统图里的阶段计数直接从注册表读，因此不可能再与
注册表脱节。输出 `results/figures/fig{1..6}*.pdf/.png`。

### P2 — 空壳阶段（已修）

`CODE/make_refs.py`（0 字节）已删除。注册表由 28 → **35 阶段**（原 28 − 1 空壳 + 7 实测
+ 1 绘图），provenance 由 7/9/12 → **14 measured / 9 simulated / 12 derived**。

### P3 — `data/README.md` 只写两个数据集（已修）

补齐六个公开源：EPFL、Cranfield、Peregrine、fringe、WLI、XCT，含 DOI、许可、体量、放置
路径、对应阶段，以及各阶段写出的工作目录。新增两条护栏测试，防止再出现"代码读了数据、
文档没写"：

* `test_data_readme_covers_every_measured_stage`
* `test_data_readme_covers_all_six_public_sources`

### P4 — `src/dbound` 落后上游（已修）

同步到上游 `81d99a2`：`cli.py` 增加 `math` / `bound` 子命令，补 `__main__.py`；`VENDORED.md`
的 commit 与说明已更新。其余模块与上游逐字节一致。

### P5 — 版本与计数文档（已修）

README、GUIDE、使用说明、PROVENANCE、ARCHITECTURE、`.zenodo.json`、NDTE 稿与系统图
全部改为 35 阶段 / 14-9-12 / 20 测试；`.zenodo.json` 版本 1.1.0，补四个数据 DOI 的
related identifier。

### 测试

`pytest -q`：**18 passed + 2 deselected**（`tmp_path` 两条在 DSH 沙箱下因临时目录 ACL 报
PermissionError，非代码问题；两条逻辑已用等价脚本单独验证：缺失数据检测返回 1 条缺项，
runner 返回 exit code 2）。CI（Ubuntu）上应为 20 passed。

---

## 三、仍未解决 / 需要下一轮

### R1 — Measurement 版的 Code availability 仍是旧话

`MEASUREMENT_manuscript_DB.docx` 写"will be deposited in Zenodo before publication"，
而 DOI 已发布。整合稿 NDTE 已改为 1.1.0；Measurement 版是否同步取决于该稿是否还投、
投哪里。

### R2 — Zenodo 尚未出新版本

记录仍是 v1.0.0。推送并打 tag 后需在 Zenodo 上 **New version**（不要新建记录），否则
`doi:10.5281/zenodo.24128938` 指向的仍是旧包。

### R3 — 工作区体积

`am_monitoring` 约 5.3 GB，绝大部分是 `data/`（必须保留）；`paper_work/` 的 `*.png` 是历史
构建残留，可清。

### R4 — 图 4/5/6 仍需完整数据才能全量重绘

- 图 4 需要 `ae_spectral` 与 `lu_echo` 两个结果文件（已提交，可直接重绘）。
- 图 5 的 G1/G2 两条线、图 6 的跨重建与消融，需要 `data/xct/vol_g1`、`vol_g2`（各 120 层）。
  只放主卷时图 5 只画 GD，图 6 仍可全绘。

---

## 四、发布清单（由仓库所有者执行）

1. 推送本地提交到 `main`，确认 CI 绿色。
2. `git tag -a v1.1.0 -m "v1.1.0: measured re-analyses, figures, 35 stages"`；本地的
   `v1.1.0` 已指向最终提交，若已存在旧 tag，先 `git tag -d v1.1.0` 再重打。
3. 推送 tag，GitHub Release 指向 `v1.1.0`（MIT）。
4. Zenodo 记录页 → **New version** → 上传与本 tag 一致的源码包 → 版本 1.1.0；确认新版本
   DOI 与 concept DOI 不变。
5. 若同时启用 GitHub–Zenodo 集成，不要重复手工上传，二选一。

发布前建议核对包内容与 tag 一致：

```bash
git archive --format=zip --prefix=AM-MultiModal-Monitoring/ -o /tmp/am-1.1.0.zip v1.1.0
unzip -l /tmp/am-1.1.0.zip | tail -n +4 | wc -l    # 文件数 + 目录数
```
