# 维护审计 · AM-MultiModal-Monitoring

审计时间：2026-11-11 20:30（Asia/Shanghai）
审计对象：本工作区 `C:\Users\lei'shen\Desktop\am_monitoring`
GitHub：https://github.com/Xbotsd/AM-MultiModal-Monitoring
Zenodo：https://zenodo.org/records/24135622（v1.1.0；concept 24128937）
前置库：https://github.com/Xbotsd/detectability-bound（Zenodo v0.1.0，24080213，concept 24080212）

---

## 一、当前状态（已发布）

| 对象 | 状态 | 核验方式 |
|---|---|---|
| GitHub `main` | `e93c729`，CI success | Actions API |
| GitHub tag | `v1.1.0`（annotated `5e1efe8` → `e93c729`） | `git ls-remote` |
| GitHub Release | `v1.1.0`（2026-11-11 12:10 UTC，无附件） | Releases API |
| Zenodo | **v1.1.0，记录 24135622**，83 文件 / 277 282 B / md5 `a1c2b183…` | Records API + 下载比对 |
| Zenodo concept DOI | `10.5281/zenodo.24128937` → 已解析到 24135622 | DOI 解析 |
| v1.0.0 | 记录 24128938 原样保留 | Records API |
| 论文（整合稿） | `NDTE_manuscript.docx/.pdf`：35 阶段 / 14-9-12 / 20 测试 / v1.1.0 | 文本抽取 |

**GitHub–Zenodo 集成是开启的**：发 Release 后 Zenodo 自动建了 v1.1.0 草稿（归档为 GitHub 从 tag 打的包，元数据取自仓库 `.zenodo.json`），本次只补了 `version` 字段并发布，未重复上传。以后发 Release 即自动进 Zenodo，不要再手工 New version。

---

## 二、与前置库 `detectability-bound` 的关系

这是本仓库完整度里此前漏掉的一层。两个库是**两个独立工件、两个 DOI**，关系是单向的前置依赖：

| | `detectability-bound`（前置） | 本仓库 |
|---|---|---|
| 角色 | 界的理论、demo 与参考实现 | 被界约束的监测系统 |
| 回答 | 任一检测器在这条感知链上**最多**能做到什么、代价多少 | 这条链**实际**测到了什么、哪些算工艺证据 |
| 范围 | 与模态无关：体缺陷 + 瞬态事件 | 声学、激光超声、相位/点云、融合、控制、六个公开数据集 |
| 不负责 | 阶段、溯源、监测数据、测量链 | 推导或修改界；XCT 估计器归前置库 |

- **代码边界**：`src/dbound/` 是上游 `81d99a2` 的 vendored 副本；`src/ammonitor/decision.py` 是唯一适配层（`energy_at`、`ndtr(d′−z)`、`required_voxel`）；`tests/test_system.py::test_volumetric_energy_matches_the_bound_module` 断言两边一致。本仓库除同步外不修改 `src/dbound/`。
- **结果边界**：dbound 的 `measure_vol_gd / cross_group / ablation / comparison` 由 `CODE/7_measured_real/run_xct_clutter.py` 调用并落到 `results/xct_clutter.json`；`verify_algebra` 不复制；表 1 的 `design_rule` 尚未复制（见 G3）。
- **论文边界**：整合稿 §2、§4.4–4.6 属前置库；§3、§4.1–4.3、§4.7–4.9 属本仓库；表 9 分开标注。
- **版本对应**：AM v1.1.0（24135622）↔ dbound v0.1.0（24080213），vendored `81d99a2`。

完整映射（模块级、结果级、同步流程、引用方式）见 [`docs/RELATION_TO_DBOUND.md`](docs/RELATION_TO_DBOUND.md)；`.zenodo.json` 已把 dbound 版本 DOI 以 `requires` 写入 related identifiers（下一次发版生效）。

---

## 三、v1.1.0 修掉的问题

1. **实测分析入库**：融合、分级决策、解缠、高度图、XCT 杂波/跨重建/消融/检测器、LU 回波、声学谱界共 7 个新的 measured 阶段，全部实跑复现论文数字。
2. **图 1–6 入库**：`6_visualization:run_ndte_figures` 从 `results/*.json` 画六图，系统图计数读注册表。
3. **注册表**：28 → 35（14 measured / 9 simulated / 12 derived）；删除 0 字节的 `make_refs.py`。
4. **数据文档**：`data/README.md` 补齐六个数据集（DOI、许可、布局、对应阶段）。
5. **dbound 同步**：`a652d04` → `81d99a2`，补 `__main__.py` 与 `bound` 子命令。
6. **测试**：20 条；本地 18 passed + 2 deselected（沙箱临时目录 ACL），CI 全绿。

---

## 四、完整度与剩余缺口

工程结构约 95%，**证据链约 75%**，综合约 85%。缺口按严重度：

### G1 — 旧脚本结果未入库（最该补）

论文表 4/9 有 6 个数字只存在 `data/**`（被 gitignore）：

| 文件 | 对应数字 |
|---|---|
| `data/statistics/cv_acoustic.json` | 82.2 % ± 2.18 %；F1 85.28/76.70/84.72；macro P/R/F1 ✅ |
| `data/statistics/cross_subset_epfl.json` | 84.3/92.7/86.0/87.3，均值 87.6 ✅ |
| `data/complexity/complexity_analysis.json` | 0.656 ms、3 139 参数、1.107 MB ✅ |
| `data/statistics/roc_auc.json` | 见 G2 |
| `data/output/acoustic_ablation.json` | 见 G2 |
| `data/statistics/cv_laser_ultrasound.json` | 旧 LU 分类 93.8 %（与表 4 的 88.2 不同任务） |

### G2 — 表 4 两处数字待核对

- soft vote：稿 87.5 %；`acoustic_ablation.json` 同一组实验为 **86.56 %**（kNN 85.21、MLP 87.92 与稿一致）。
- macro AUC：稿 **0.975**；`roc_auc.json` acoustic macro 为 **0.9594**。

需用同一脚本、同一划分重跑并落盘后才能确认；在此之前不视为已复现。

### G3 — 表 1 无结果物

`design_rule` 只能现算（`ammonitor bound` / `python -m dbound bound`），没有 `results/design_rule.json`。

### G4 — 数据与门面

- 本机 `data/` 只有 EPFL（4.48 GB）与 Cranfield（45 MB）；Peregrine/fringe/WLI/XCT 在 `D:\`，5 个 measured 阶段显示 `!`。补全约需 1.2 GB 下载。
- 缺 `CITATION.cff`、`CHANGELOG`；仓库 About 描述、Homepage（建议指 concept DOI）、Topics 仍是旧版。

---

## 五、下一步

1. G1：把 6 个 JSON 收进 `results/`，旧脚本输出路径改到 `results/`，加“结果文件存在”测试。
2. G2：重跑 `run_eplf_v12` 与 `run_roc_auc`，确认或修正 87.5 / 0.975，输出落盘。
3. G3：加 `run_design_rule`（derived）产 `results/design_rule.json`。
4. 发 **v1.1.1**：tag + Release（会自动生成 Zenodo 新版）；`.zenodo.json` 里的 `requires` 关系随之生效。

完成后证据链完整度约 97%，剩余是“数据需下载”和“论文数字与结果文件的自动对账”。
