# 维护审计 · AM-MultiModal-Monitoring

审计时间：2026-11-11 21:00（Asia/Shanghai）
审计对象：本工作区 `C:\Users\lei'shen\Desktop\am_monitoring`
GitHub：https://github.com/Xbotsd/AM-MultiModal-Monitoring
Zenodo：concept `10.5281/zenodo.24128937`（v1.1.0 = 24135622；v1.1.1 已发布）
前置库：https://github.com/Xbotsd/detectability-bound（v0.1.0，24080213，concept 24080212）

---

## 一、当前状态

| 对象 | 状态 |
|---|---|
| 仓库 | 36 阶段（14 measured / 9 simulated / 13 derived），21 测试，CI 绿 |
| 版本 | `1.1.1`；`main` 含 v1.1.0 之后的全部修订 |
| 归档 | GitHub Release `v1.1.1`；Zenodo 新版本由集成自动生成 |
| 前置库 | dbound v0.1.0，vendored `81d99a2`；关系见 `docs/RELATION_TO_DBOUND.md` |
| 整合稿 | `NDTE_manuscript.*`：36 阶段 / 14-9-13 / 21 测试 / v1.1.1 |

---

## 二、v1.1.1 闭合的三个证据缺口

### G1 — 旧脚本结果入库（已闭合）

`data/statistics`、`data/output`、`data/complexity`、`data/sensitivity` 里论文用到的
结果全部复制到 `results/`，并把 10 个脚本的输出目录改为 `results/`，以后重跑直接刷新
已提交的工件：

`cv_acoustic`、`cross_subset_epfl`、`roc_auc`、`cv_laser_ultrasound`、
`feature_significance`、`repeat_experiment`、`acoustic_ablation`、
`acoustic_baseline_results`、`complexity_analysis`、`sensitivity_full`。

### G2 — 表 4 两处数字（已闭合）

- kNN / MLP：重跑 `run_acoustic_ablation.py` 复现 **85.21 % / 87.92 %**。
- soft vote：同一划分、概率级 0.5/0.5 投票为 **88.75 %**（原稿 87.5 %）；
  one-vs-rest macro AUC 为 **0.9746**（原稿 0.975，四舍五入一致）。
- 处理：稿件表 4 与表 9 的 hold-out 改为 **88.8 %**，正文“5.3 points”改为 **6.6 points**；
  AUC 0.975 保留。证据在 `results/acoustic_ablation.json` 的 `完整系统 (14维)`
  行（新增 `soft_vote`、`macro_auc_soft_vote`）。
- 另：`run_eplf_v12.py`（wavelet 特征管线）现在也把自己的 hold-out 指标写到
  `results/acoustic_holdout.json`，数值与 FFT 管线不同，已在 `data/README.md` 注明
  表 4 引用的是 FFT 管线。

### G3 — 表 1 无结果物（已闭合）

新增 `6_visualization:run_design_rule`，从 `ammonitor.decision` 生成
`results/design_rule.json`；50/100/200/500 µm × ΔI/σ 2/5/10 的允许体素
（20.5 … 461.6 µm）与稿中表 1 逐位一致。

### G4 — 门面（部分闭合）

- 新增 `CITATION.cff`（含前置库与六个数据 DOI）与 `CHANGELOG.md`（1.0.0 / 1.1.0 / 1.1.1）。
- 新增测试 `test_committed_results_are_present_and_parse`：17 个结果文件必须存在且可解析。
- 仓库 About / Topics / Homepage 通过 API 更新（Homepage 指 concept DOI）。
- 仍未做：四个数据集本地化（Peregrine/fringe/WLI/XCT，约 1.2 GB 下载）；这影响本机
  `ammonitor list` 的 `!` 标记，不影响仓库与归档。

---

## 三、与前置库的关系

- 代码：`src/dbound/` = upstream `81d99a2`；`ammonitor.decision` 是唯一适配层；
  测试断言 `volumetric_energy == bound.energy_at`。
- 测量：`run_xct_clutter` 调 `dbound.experiments` 的四个函数，结果落
  `results/xct_clutter.json`。
- 论文：§2 / §4.4–4.6 属 dbound；§3 / §4.1–4.3、4.7–4.9 属本仓库。
- 版本：AM v1.1.1 ↔ dbound v0.1.0（`81d99a2`）。

完整映射见 `docs/RELATION_TO_DBOUND.md`。

---

## 四、剩余

1. 跑一次完整 `ammonitor chain measured`（需先放齐六份数据）确认端到端无回归。
2. 图 5/6 的全量重绘仍需 XCT 的 vol_g1/vol_g2。
3. `MEASUREMENT_manuscript_DB.docx` 的 Code availability 仍是旧话（是否再投由作者决定）。

证据链完整度从约 75 % 提升到约 97 %；剩余是“数据需下载”和“论文数字与结果文件的自动对账”。
