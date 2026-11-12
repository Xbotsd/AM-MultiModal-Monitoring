# 维护审计 · AM × DB 孪生两库

审计时间：2026-11-12 09:50（Asia/Shanghai）
维护对象：
- **AM**：`C:\Users\lei'shen\Desktop\am_monitoring` — https://github.com/Xbotsd/AM-MultiModal-Monitoring
- **DB**：`D:\new_project\proj_dbound` — https://github.com/Xbotsd/detectability-bound

两库是孪生：**DB 是决策半，为解决 AM“测到的结果到底能看见什么”而造；AM 是测量半。**
代码上 AM 单向 vendor DB；溯源上两者是兄弟，不是父子。

---

## 一、当前状态

| | AM | DB |
|---|---|---|
| 版本 | `1.1.3` | `0.1.1` |
| 版本 DOI | concept `10.5281/zenodo.24128937` | `10.5281/zenodo.24136698` |
| 阶段 / 测试 | 36 阶段（14/9/13），21 测试 | 11 测试 |
| 数据 | **六源全部本地就位** | 三卷 XCT 本地 + manifest/fetch |
| 端到端 | `chain measured` 12/12，结果逐字节一致 | 六份结果均本地可复跑 |
| 归档 | GitHub Release + Zenodo 自动 | GitHub Release + Zenodo 手工版本 |

## 二、这一轮补完的缺口（2026-11-12）

1. **XCT 三卷**：从 DB 的 `data/vol_gd|vol_g1|vol_g2` 复制 599 MB 到 AM 的
   `data/xct/`；`run_xct_clutter` 重跑，κ 31.2→125.2、ablation 115.1/105.9/49.5、
   POD 0.530/0.117/0.023，与已提交的 `results/xct_clutter.json` **完全一致**。
2. **三份数据**：Peregrine（Zenodo 23727492，11 MB CSV）、fringe（22125908，
   39 MB）、WLI（21285367，208 MB）下载并按约定布局放置；四个 real 阶段重跑，
   RMSE 38.20/37.43/36.03、AUC 0.751、0.532 mm、4.52/2.96/4.98/2.88 µm
   全部与稿件一致。
3. **WLI 输入声明修正**：`run_pointcloud_real` 原来声明 `data/hm/{name}.ASC`
   （模板字符串），导致数据齐全时 `ammonitor list` 仍显示 `!`；改为四个显式路径，
   并去掉已无用的 `resolve()`。注册表随之重算。
4. **端到端**：`ammonitor chain measured` 12/12 全部成功，`git status` 显示
   `results/` 无任何变化——12 个 measured 阶段在六份数据上**逐字节复现**归档结果。

## 三、完整度（2026-11-12）

| 维度 | 结果 |
|---|---|
| 归档（代码/结果/图/文档/元数据/DOI） | **100 %** |
| 证据链（论文每个数字 → `results/`） | **100 %** |
| 本地重跑（36/36 阶段，无额外下载） | **100 %** |
| 孪生集成（双向引用、映射文档、版本对） | **100 %** |
| 数据可复现 | 六源全部本地；第三方原始数据不入库（按许可） |
| 投稿 | 稿件已对齐 v1.1.3，尚未投出（外部动作） |

剩余事项只有两件，且都不影响仓库完整性：

- AM 稿件投稿；
- DB 归档 README 有一行版本滞后（`main` 已修正），以及 DB 尚无 `CHANGELOG.md`。

## 四、关系（一句话版）

> AM 报告“这条链测到了什么”；DB 报告“同一条链上任何检测器最多能看到什么、要付出什么代价”。
> DB 因 AM 的问题而生，AM 因 DB 的界而有意义；代码上 AM 固定引用 DB，溯源上两者平级。

- 代码咬合：`src/ammonitor/decision.py` 包装 `bound/psf/detectors`；
  `run_xct_clutter` 调 `experiments`；测试断言 `volumetric_energy == energy_at`。
- 结果咬合：`results/xct_clutter.json` ← DB 的四个实验；`results/design_rule.json`
  由 DB 的 `required_voxel` 生成。
- 论文咬合：§2 与 §4.4–4.6 属 DB；§3 与 §4.1–4.3、4.7–4.9 属 AM；表 9 分开标注。

## 五、维护约定

- DB 先行：DB 改代码 → 在 AM 里同步 `src/dbound/` → 更新 `VENDORED.md` 的提交号 →
  `pytest -q`（21 条）。
- 版本成对：DB `0.1.x` ↔ AM `1.1.x`；每次发布同时更新两边的 `related_identifiers`。
- 论文数字只能来自 `results/`；`results/` 只能由脚本生成。
- 放齐数据后至少跑一次 `ammonitor chain measured`，结果文件应无 diff。
