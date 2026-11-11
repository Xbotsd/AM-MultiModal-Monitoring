# 维护审计 · AM × DB 孪生两库

审计时间：2026-11-11 21:40（Asia/Shanghai）
维护对象：
- **AM**：`C:\Users\lei'shen\Desktop\am_monitoring` — https://github.com/Xbotsd/AM-MultiModal-Monitoring
- **DB**：`D:\new_project\proj_dbound` — https://github.com/Xbotsd/detectability-bound

两库是孪生：**DB 是决策半，为解决 AM“测到的结果到底能看见什么”而造；AM 是测量半。**
代码上 AM 单向 vendor DB；溯源上两者是兄弟，不是父子。

---

## 一、当前状态

| | AM | DB |
|---|---|---|
| 版本 | `1.1.2` | `0.1.1` |
| 版本 DOI | concept `10.5281/zenodo.24128937` | `10.5281/zenodo.24136698` |
| concept DOI | `10.5281/zenodo.24128937` | `10.5281/zenodo.24080212` |
| 提交 | `main`（见 GitHub） | `main` = `9924285` |
| 阶段 / 测试 | 36 阶段（14/9/13），21 测试 | 11 测试 |
| 归档 | GitHub Release + Zenodo 自动 | GitHub Release + Zenodo 手工版本 |
| 交叉引用 | 元数据 `requires` → DB v0.1.1 | 元数据 `isSupplementedBy` → AM concept |

## 二、这一轮做了什么

### DB v0.1.1（文档与元数据，代码未变）

- README 新增 **“Twin of the monitoring system”**：说明两库是同一工作的两半，DB 为解决
  AM 的问题而造，并给出角色、问题、版本、代码关系的对照表。
- `CITATION.cff` 与 `.zenodo.json` 引用 AM concept DOI；`.zenodo.json` 增加
  `in-situ monitoring`、`sensor fusion`、`defect detection` 关键词。
- 版本 0.1.0 → 0.1.1；`src/dbound` 代码与 `81d99a2` 完全一致。
- 归档：Zenodo `24136698`，文件 `detectability-bound-v0.1.1.zip`，771 564 B，
  md5 `77b2248bd05dd74ca20fb92cfd3c0558`。

### AM v1.1.2（文档与交叉引用）

- `docs/RELATION_TO_DBOUND.md` → **`docs/TWIN_LIBRARIES.md`**：改写为孪生叙事，
  保留模块级、结果级、论文段落、版本/DOI 映射与同步流程。
- README “Prerequisite” → **“Twin library: the decision half”**；
  `ARCHITECTURE.md` 第 0 层同步改写。
- `src/dbound/VENDORED.md`：记录 vendored 于 DB `v0.1.1`（`9924285`，代码同 `81d99a2`）。
- `.zenodo.json`、`CITATION.cff`：DB 版本 DOI 由 `24080213` 更新为 `24136698`；
  AM 版本 1.1.1 → 1.1.2。
- 整合稿中的 “standalone prerequisite … built first” 改为 “twin … created to answer
  the question that measurement cannot”，并同步 DB 版本与 DOI；docx/pdf 重建。

## 三、关系（一句话版）

> AM 报告“这条链测到了什么”；DB 报告“同一条链上任何检测器最多能看到什么、要付出什么代价”。
> DB 因 AM 的问题而生，AM 因 DB 的界而有意义；代码上 AM 固定引用 DB，溯源上两者平级。

- 代码咬合：`src/ammonitor/decision.py` 包装 `bound/psf/detectors`；
  `run_xct_clutter` 调 `experiments`；测试断言 `volumetric_energy == energy_at`。
- 结果咬合：`results/xct_clutter.json` ← DB 的四个实验；`results/design_rule.json`
  由 DB 的 `required_voxel` 生成。
- 论文咬合：§2 与 §4.4–4.6 属 DB；§3 与 §4.1–4.3、4.7–4.9 属 AM；表 9 分开标注。

## 四、证据链

v1.1.1 已闭合三个缺口：旧结果全部进 `results/`（G1）；表 4 的 soft vote 由 87.5 %
更正为可复现的 88.8 %、AUC 0.9746（G2）；表 1 由 `run_design_rule` 生成（G3）。
门面（CITATION、CHANGELOG、About/Topics）已补（G4 部分）。

整体完整度约 **97 %**。剩余：

1. 四个数据集本地化（Peregrine / fringe / WLI / XCT，约 1.2 GB 下载）。
2. 放齐数据后跑一次 `ammonitor chain measured` 做端到端回归。
3. 图 5/6 的全量重绘需要 XCT 的 `vol_g1`/`vol_g2`。

## 五、维护约定

- DB 先行：DB 改代码 → 在 AM 里同步 `src/dbound/` → 更新 `VENDORED.md` 的提交号 →
  `pytest -q`（21 条）。
- 版本对：DB `0.1.x` ↔ AM `1.1.x`；每次发布同时更新两边的 `related_identifiers`。
- 论文数字只能来自 `results/`；`results/` 只能由脚本生成。
