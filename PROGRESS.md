# PROGRESS：项目进度

> 机器可读的状态块在下面两行注释之间，格式是 YAML。每个会话开始时读它、认领时改它、每完成一个阶段更新它。
> `tests/test_progress.py` 会检查它的格式。

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/G-global.md        # 下一张（或正在做的）任务卡
status: done                            # ready | in_progress | blocked | done
claimed_by: ""                          # 认领人名字；空表示无人认领
claimed_at: ""                          # 认领时间，ISO 8601 UTC，例如 2026-11-03T08:00:00Z
last_pushed_stage: G4                   # 最后一个完成并 push 的阶段
last_pushed_at: 2026-11-04
branch: feat/data-harmonization
data_release: global-v1               # 正式版 Release v1（CC BY 4.0，S15）；全球版在 Release global-v1（阶段 G）；6 个区的 v1 仍是 Release v1；处理后的输入在 data-v0，里程碑 A 在 milestone-a；SHA256 见交接备注和 results/expected/
next_step: "全部任务卡已完成。全球版 Release global-v1 已发布（docs/data-interface-global.md）；等 PR 合并进 main"
needs_human:
  - "通知前端：全球版 Release global-v1 已发布（CC BY 4.0）：gh release download global-v1 --repo team-inspiratio/inspiratio-space-apps-2026；接口见 docs/data-interface-global.md（区间放大系数 16.75，网页上要说明区间很宽）"
  - "请合并：G-global 的 PR（feat/data-harmonization → main）"
  - "已确认（用户 2026-11-04 批准发布 global-v1 时一并确认）：G-global 上线版用全球重训模型，区间系数在全球验证窗口上重新求（docs/decisions/0013 第 3、5 条）"
  - "待人确认（过目即可，不阻塞）：S15 验收用 pipeline.py all --from-release 入口（从 Release data-v0 网格表起步），没有从原始数据完整重跑（docs/decisions/0012 第 1 条）"
  - "通知前端：正式版 Release v1 已发布（CC BY 4.0）：gh release download v1 --repo team-inspiratio/inspiratio-space-apps-2026，数据与预发布版 dataset-v1 相同，多了 CSV、数据说明卡、异常测试用例"
  - "通知前端：异常指标参考实现 harmonization/anomaly.py + 25 个标准测试用例 docs/anomaly-cases.json（逐字段对答案；补充细节见 docs/data-interface.md 第 6 节、docs/decisions/0011 第 1 条）；数据集新增 CSV 版"
  - "请通读：数据说明卡 docs/data-card.md、AI 使用说明 docs/ai-usage.md"
  - "请通读：验证报告 reports/validation.md（6 张核心图 + 局限性；结论：训练区可信，留出区误差 2.5 倍、偏低 14–45%）"
  - "待人确认（过目即可，不阻塞）：S13 新做的 GFED 检查和年代偏移调查的实现细节（docs/decisions/0010：年代偏移主数字用 5 折平均 AUC；GFED 只到 2016 年；文献数值不做数值比较）"
  - "请过目：最终测试成绩 reports/final-test.md（测试 1 比 M1s 好 22%；留出区误差是训练区的 2.5 倍、总量偏低 20–35%，全球阶段 G 前要考虑）"
  - "通知前端：最终数据集预发布版 dataset-v1 + docs/data-interface.md（v1：来源名改为 model_*，新增 lo_90/hi_90、nrt）"
  - "待人确认：S12 上线版沿用 2014-01–2021-06 的冻结模型，训练区 2012–2013 年用估计值，因为本机永远没有这两年 S-NPP（docs/decisions/0009 第 1 条）"
  - "请过目：S10 审核记录 reports/model-review.md（结论：前 3 名都通过泄漏审查；风险：纬度在只有 3 个训练区时起了区域标签的作用，留出区可能变差，测试 2 会检验）"
  - "待人决定：NOAA-20 接续的通过标准（docs/decisions/0005 第 4 条；标准是看了检验结果后提出的）"
  - "已记录：留出区 Terra 桥接按 ADR 0005 第 6 条建议用当地 MODIS 比例（选项 B），按用户授权由 AI 决定（docs/decisions/0009 第 3 条）"
  - "待人确认：QM 细节、λ 选择、桥接年份、v0 来源规则（docs/decisions/0005 第 1–3、5 条）"
  - "已记录：S10 LightGBM 与实验循环的实现细节（docs/decisions/0006），按用户授权由 AI 决定"
  - "已记录：S10 预算缩减、截止时间和补救重跑是用户的决定（docs/decisions/0007）"
  - "通知前端：milestone-a 预发布版 + docs/data-interface.md 已可用（PR #2 已留言）"
  - "GitHub CLI 登录：这台电脑已登录可跳过；换电脑接力先运行 gh auth login --web（下载 Release 数据要用）"
  - "待人处理：按 docs/review-packet.md 开一次 1 小时审核会，优先 X1（PR #4/#5 未合并）、X2（仓库私有且无 LICENSE）"
  - "待人确认：是否解锁 2012–2013 年 S-NPP 观测值替换训练区估计值（docs/decisions/0014，建议只替换不重训、云端汇总；要由人提交 [unfreeze]）"
  - "待人确认：全球产品的置信度等级、M1s 回退、网页标注（docs/decisions/0015，建议分级细化、不回退）"
  - "待人确认：网站部署方案（docs/decisions/0016，建议先用现有 Sites 重新发布修复版，仓库公开后改 GitHub Pages）"
  - "待人处理：11/13 官方指南发布后逐项核对 docs/submission/ 的全部草稿，并填写方括号项"
  - "待人决定：是否需要“一键直达某区域某月”的入口（现在预设按钮只能一键进区域，路线要 1–3 次点击；这是新功能，没有做）"
```
<!-- STATUS:END -->

## 提交准备（非数据线）

> 这一节记录比赛提交准备工作。不改数据线状态块，也不认领 G-global。

- 任务 1 完成：人工审核包 `docs/review-packet.md`（覆盖数据分支 `5dbc2e2` 的 20 条 needs_human，另加 X1、X2 两条盘点发现）。
- 任务 2 完成：提案 ADR 0014（解锁 2012–2013 年 S-NPP 观测值）、ADR 0015（全球置信度等级、M1s 回退、网页标注），都只写提案，没有实现。
- 任务 3 完成：部署方案对比草稿 ADR 0016（chatgpt.site、Vercel、Netlify、GitHub Pages），没有部署任何东西。
- 任务 4 完成：提交材料草稿 `docs/submission/`（`project-page.md`、`demo-script.md`、`checklist.md`），全部标注 11/13 官方指南发布后逐项核对。
- 任务 5 完成：三条演示路线已在 PR #5 构建上实测，写入 `docs/submission/demo-script.md`。没有发现阻碍演示的 bug，所以没有改网页代码。

## 会话总览

| 会话 | 任务卡 | 覆盖阶段 | 状态 |
|---|---|---|---|
| 0 | （本仓库搭建） | S00 | ✅ 完成 |
| 1 | [`1-data`](docs/sessions/1-data.md) | S01–S06 | ✅ 完成 |
| 2 | [`2-baselines`](docs/sessions/2-baselines.md) | S07–S09（里程碑 A） | ✅ 完成 |
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | ✅ 完成 |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | ✅ 完成 |
| 5 | [`5-report`](docs/sessions/5-report.md) | S13–S15（里程碑 B） | ✅ 完成 |
| G | [`G-global`](docs/sessions/G-global.md) | 全球重跑 | ✅ 完成 |

## 阶段表

| 阶段 | 内容 | 状态 | 完成时间 | 关键数字 | commit |
|---|---|---|---|---|---|
| S00 | 环境、护栏、CI、自说明文件 | ✅ done | 2026-11-03 | CI 绿；pytest 17 项通过 | 3dcf808 |
| S01 | 预注册（settings、留出区、随机矩形、grader.yml） | ✅ done | 2026-11-03 | 6 区（3 训练 + 3 留出）；3300 个矩形；冻结 5 个文件 | 7d1aa0c |
| S02 | 下载（年度包、API 2026、缺测清单、GFED） | ✅ done | 2026-11-03 | 46 个年度包（约 9 GB，跳过锁定年份）；API 918 个卫星-日；GFED 24 年；缺测 178 天；抽 4 天×3 源比对：年度包每行都在 API 中 | 7df072f |
| S03 | 导入（流式转 Parquet，丢弃留出区 VIIRS） | ✅ done | 2026-11-03 | 46 个年度包 + 6 个 API 源，每个文件 原始行数 = 写入 + 留出区丢弃（`docs/ingest-ledger.csv`）；VIIRS 压缩包已删除 | 84abd8c |
| S04 | 清洗 | ✅ done | 2026-11-03 | 5.29 亿 → 4.44 亿行；类型 −6.1%、低置信度 −9.7%、NRT 掩膜 −0.18%、重复 222 条；抽查 20 条无误删（`reports/cleaning.md`） | 94669f0 |
| S05 | 网格化与特征 | ✅ done | 2026-11-03 | 总数守恒（各卫星格子计数和 = 清洗后点数）；区域稠密表 261.6 万行；20 个特征 | 0ec693d |
| S06 | 数据体检（A5） | ✅ done | 2026-11-03 | S-NPP/Aqua 年比约 4.6–10；NOAA-20/S-NPP 中位数 0.98–1.00；Terra/Aqua 2020 年后骤降 | 6603ac1 |
| S07 | 判卷机器（prepare、evaluate） | ✅ done | 2026-11-03 | 假方法：永远 0 合并 MALE 5.90，直接用 MODIS 1.79；两次运行 SHA256 一致（`reports/judge-check.md`） | |
| S08 | 保底模型 M0、M1s、QM；桥接与接续 | ✅ done | 2026-11-03 | 两窗口合并 MALE：M1s（λ=20）0.377、QM 0.463、M0 1.795；Terra→Aqua→M1s 链条 0.522；NOAA-20 接续月总量偏差中位数 −0.3%～+3.1%（`reports/scores-v1.md`） | |
| S09 | ★里程碑 A：数据集 v0、前端导出、预发布版 | ✅ done | 2026-11-03 | 261.6 万格子-月份：S-NPP 观测 55.4 万、NOAA-20 换算 4.7 万、M1s 182 万、Terra 桥接 19.7 万；预发布版 `milestone-a`，下载后 9 个文件 SHA256 全部核对通过 | |
| S10 | LightGBM 和 AI 实验 | ✅ done | 2026-11-04 | 37 次实验（E000–E036，预算按 ADR 0007 缩减并提前收工）；最佳验证 MALE：E028 两段式 LightGBM 0.2947，比 M1s（0.3766）低 21.8%（差 −0.082 ± 0.016，95% 区间 −0.113～−0.053），比 QM 低 0.169；前 3 名都通过护栏和泄漏审查（`reports/scores-s10.md`、`reports/model-review.md`） | |
| S11 | 冻结与外部盲审 | ✅ done | 2026-11-04 | 选定 E028。测试 MALE：测试 1 **0.258**（M1s 0.332，低 22%），测试 2 留出区 **0.644**（M1s 0.857）；κ 0.69 / 0.53；区域区间覆盖率校准后 95.5% / 55.9%（原始 37.9% / 12.9%）；留出区零火点和低火点指标比 M1s 差、总量偏低 20–35%（`reports/final-test.md`） | 742547e |
| S12 | 最终数据集 | ✅ done | 2026-11-04 | 上线版 = 冻结评估版 E028（ADR 0009）；261.6 万格子-月份：S-NPP 观测 55.4 万、模型估计 181.7 万、Terra 桥接 19.7 万、NOAA-20 换算 4.7 万；100 次重抽区间，区域区间乘校准系数 5.37；验收：S-NPP 段 426 个区域-月共 1519 万点与观测逐个一致；预发布版 `dataset-v1` | |
| S13 | 验证报告（D1） | ✅ done | 2026-11-04 | 第 3 节 1–7 全部完成（`reports/validation.md`）。新做的两项：年代偏移 AUC 0.57（训练区）/ 0.56（留出区），对照 2022–2026 年 0.75 / 0.70（Terra 漂移）；GFED 每 km² 燃烧面积火点数 2012 年前后不变（南部非洲 2.77 → 2.92，科尔多瓦 5.90 → 5.86），直接拼接跳约 5 倍。6 张核心图 `reports/figures/d1-*.png` | |
| S14 | 交付 | ✅ done | 2026-11-04 | 数据集 CSV 版 `dataset_v1.csv.gz`（18 MB，和 Parquet 逐列核对，相对误差 < 5×10⁻⁶）；数据说明卡 `docs/data-card.md`；AI 使用说明 `docs/ai-usage.md`；异常指标参考实现 `harmonization/anomaly.py` + 25 个标准测试用例 `docs/anomaly-cases.json`（19 个手算边界 + 6 个真实数据）；HANDOFF 第 6 节“成果在哪”；ADR 0011 | |
| S15 | ★里程碑 B：一条命令复现、Release v1、合并 main | ✅ done | 2026-11-04 | 用户确认后 squash-merge 进 main、发布正式版 Release `v1`（CC BY 4.0）。全新克隆 + 空数据目录运行 `pipeline.py all --from-release`：87 分钟，`pipeline.py check` 37 项全过（成绩文件逐字相同；两个验证窗口分数等于 freeze.json 和 E028；测试集 est_final 和 100 次重抽与封存答卷逐位相同；数据集 v0、v1 每个文件 SHA256 一致）。顺带修好下载和导入在空数据目录里误跳过的问题（ADR 0012） | |
| G1 | 全球配置与全球稠密表 | ✅ done | 2026-11-04 | `config/regions-global.json`：GFED 14 区 + 3 个留出框，278,192 个格子（训练 273,712、留出 4,480），8,680 万格子-月份；按 10° 纬度带分块；一次全球训练约 4 分钟（2,436 万行） | |
| G2 | 全球验证分数（按 GFED 区，只报告） | ✅ done | 2026-11-04 | 两窗口合并 MALE（全部矩形）：E028 全球重训 **0.534**、M1s 0.619（差 −0.084 ± 0.013）、QM 0.680、M0 2.030；参照 S11 三区模型 0.563。M1s 在 CEAM、EQAS、NHSA、SHSA 更好；BOAS 1.03 最差；1–9 火点误差是 M1s 的 1.13 倍（`reports/global-scores.md`） | 6f84fc0 |
| G3 | 全球重抽与区间校准 | ✅ done | 2026-11-04 | 每组前 50 次封存重抽（ADR 0013 第 5 条补充，用户批准）；全球验证窗口校准系数 **16.75**（S11 是 5.37），覆盖率从 14% 到 90% | fd36618 |
| G4 | 全球数据集生成与发布 | ✅ done | 2026-11-04 | 8,680 万格子-月份；S-NPP 复核 1,988 个区 × 月、1.89 亿个火点，0 不符；全球年总量 2013 年（模型）16.0 M 到 2014 年（观测）16.6 M，没有断档（`reports/global-review.md`）。用户过目后发布 Release `global-v1`（CC BY 4.0），SHA256 在 `results/expected/dataset-global-v1.sha256` | |

## 交接备注

### S00（2026-11-03）

- 分支 `feat/data-harmonization` 已建，草稿 PR：https://github.com/team-inspiratio/inspiratio-space-apps-2026/pull/2 。计划原样提交为 `docs/execution-plan.md`。
- 环境：`uv` + Python 3.12，依赖见 `pyproject.toml`，锁文件 `uv.lock`。
- 护栏：`tools/guardrails.py`（冻结文件哈希且只增不改、禁用特征、锁住年份的下载、密钥），CI、pre-commit、Claude 钩子三层共用。目前冻结清单为空，S01 开始往里加。
- 数据目录：本机 `D:/inspiratio-data`（写在 `.env` 的 `INSPIRATIO_DATA_DIR`）。
- 本机注意：uv 的默认缓存目录在这台 Windows 上有文件系统重定向问题，已在用户级 `uv.toml` 把缓存改到 `C:/Users/ASUS/.uv-cache`。其他机器不受影响。
- 接力演练已通过：新会话只凭仓库文件就正确说出了进度、下一张卡 `1-data` 和需要人准备的事项。据此补了 `docs/decisions/`（说明见其 README）和更清楚的 gh 登录说明；Claude 钩子改为用 `git rev-parse --show-toplevel` 定位仓库根目录（找不到再退回 `$CLAUDE_PROJECT_DIR`），避免会话中途换目录后钩子找不到脚本、挡住所有工具。
- **留出区已确认**（用户，2026-11-03）：澳大利亚北部（稀树草原）、西伯利亚中部（北方森林）、印度恒河平原（农田），各约 10°×10°，见 [`docs/decisions/0001-留出区选择.md`](docs/decisions/0001-留出区选择.md)。S01 照此直接写 `config/regions.json`，不需要再问人；具体边界只按地理和生态定，不看任何 VIIRS。同日用户也确认了扩展到全球、主产品保持 VIIRS 尺度。

### 会话 1（2026-11-03，qiuxue-yee）

- **完成**：S01–S06 全部完成并 push，CI 绿。预注册和冻结在 `7d1aa0c`，早于任何建模代码。
- **数据 Release `data-v0`**（预发布）：https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/data-v0 。下载：`gh release download data-v0 --repo team-inspiratio/inspiratio-space-apps-2026 -D <INSPIRATIO_DATA_DIR>/release/data-v0`，再核对 `SHA256SUMS.txt`：

  | 文件 | 行数 | SHA256 |
  |---|---:|---|
  | `grid_regions.parquet`（示范区和留出区稠密表：MODIS 特征 + VIIRS 标签） | 2,615,808 | `c9b254b945c8049554cb0fa309edfab1ff7ba8d661ed22897c206e376955623c` |
  | `grid_counts.parquet`（全球稀疏计数） | 22,944,336 | `f350a062871614e7750084d2300ff7e9a92997efbc860f856f7fb93eec6e7b05` |
  | `grid_month_status.parquet` | 1,248 | `21fa09aa6b354e07395fe437b97147d743306f493b5a13dca18fbc5746c39ab5` |
  | `clean_aqua.parquet` | 69,034,390 | `26312bb94b2d4b910cd22a7634935885da8c46cde2f16458e6ac3393c19d29b7` |
  | `clean_terra.parquet` | 36,272,942 | `6647342f9e5636c4b3e8f6eddacf1c78d7fbff442e86c70deabbdb66584947f3` |

  VIIRS 清洗后点数据（约 4.6 GB）按决定不传（`docs/decisions/0003`，已确认）。
- **给会话 2 的提示**：
  - 网格表的格子编号：`lat_idx = floor((lat+90)/0.25)`、`lon_idx = floor((lon+180)/0.25)`（从西南角起算）；评分矩形边界在 0.25° 网格上，矩形值 = 内部格子之和。
  - `*_status` 列：只有 `complete` 能用于训练和评分（预注册第 0、2 节）；`partial` 也有计数但要排除。留出区的 VIIRS 列全是空值。
  - Terra/Aqua 比例 2020 年后骤降，Terra→Aqua 桥接只能用比例稳定的年份（`reports/findings.md` 第 7 条）。
  - 本机跑护栏和测试要加 `-X utf8`：`uv run python -X utf8 -m pytest`（`docs/decisions/0002`，已确认不解冻）。
  - Claude 钩子会把提交信息里同时出现“锁定年份 + 下载”字样的命令误拦，提交信息别这样写；代码注释同理（CI 扫描）。

### 会话 2（2026-11-03，qiuxue-yee）

- **完成**：S07–S09 全部完成并 push。判卷机器 `prepare.py`、`evaluate.py`、`final_test.py` 经人过目后冻结（`e19f26c`），实现细节见 `docs/decisions/0004`（已确认）。
- **分数表 v1**：`reports/scores-v1.md`。两窗口合并 MALE：M1s（λ = 20，从 {0, 5, 20, 50, 100} 中按验证集选出）0.377，QM 0.463，M0 1.795；QM 比 M1s 差 0.087（95% 区间 0.074–0.100）。判卷检查（假方法、可重复性）在 `reports/judge-check.md`。
- **里程碑 A 预发布版 `milestone-a`**：https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/milestone-a 。下载：`gh release download milestone-a --repo team-inspiratio/inspiratio-space-apps-2026`，再用 `sha256sum -c SHA256SUMS.txt` 核对。生成：`uv run python -m harmonization.series`（同一输入重跑，字节完全相同）。

  | 文件 | SHA256 |
  |---|---|
  | `dataset_v0.parquet` | `66c1696d3a1cdc953ebcc4064054263daf973853ef824ee4b2d01b14aeb43ae8` |
  | `region_totals_v0.csv` | `6d5343c520d18164fd31bd7c908d7ecfe88406c7fab472bc3ccea5aec35d1dab` |
  | `data-interface.md` | `6f00419f11c2855c0e9c76f0b2f8c05e375de00e50dbc3c02720571f3363823e` |
  | `<region>.json.gz` × 6 | 见 Release 里的 `SHA256SUMS.txt` |

- **给会话 3 的提示**：
  - 模型接口：`fit(train_table) -> predict`，`predict(feature_table) -> 估计值`，打分用 `evaluate.evaluate(fit)` 和 `evaluate.bootstrap_diff(m1s结果, 新结果)`。predict 拿到的表有格子编号 `lat_idx`、`lon_idx`，**LightGBM 不能把它们当特征**，特征只能来自 `config/features.json`（ADR 0004 第 4 条）。
  - M1s 对照：`harmonize.fit_m1s(t, 20.0)`；选定规则比较的基准是它。只能改 `harmonization/harmonize.py`。
  - 发现：留出区的 Terra 桥接段（2000-11 至 2002-06）可能偏高 1.5–2 倍（ADR 0005 第 6 条，待人决定）。这不影响 S10 选模型。
  - 生成 Release 文件时要固定 gzip 时间戳、统一用 LF 换行，否则 Windows 和 Linux 上的哈希会不一样（`series.py` 已经这样做了）。

### 会话 3（2026-11-03 至 04，qiuxue-yee）

- **完成**：S10。LightGBM 在 `harmonization/harmonize.py` 的 `fit_lgb()`；现在这个文件就是第 1 名 E028 的原样源码（SHA256 与 `experiments.csv` 的 E028 行一致）。默认的 `fit()` 仍是 M1s，S11 按选定规则决定后再改。
- **实验**：`harmonization/experiments.csv`（37 行，每行一句假设、全部指标、是否通过护栏、是否保留）；每次实验的源码在分支 `exp/lightgbm` 的 `harmonization/variants/E###.py`（已 push，本机另有 worktree `../inspiratio-exp`）。运行器 `harmonization/autoexp.py`，规则 `harmonization/program.md`、ADR 0006（待人确认）、ADR 0007（用户的提速决定）。
- **过程**：单个 LightGBM 合并 MALE 能到 0.23，但会在每个格子上撒一点小的正估计，零火点护栏严重不合格（94% 对 6%）。E001–E014 用各种归零、打折规则都没过关。用户要求提速后改成“两段式”：先判断有没有火，有火才估数。E016 第一次通过全部护栏。之后围绕它做了删减和派生特征，分数都在 0.293–0.305 之间。最接近的两个用 30 次 Optuna 重跑（E035 不合格，E036 合格），按规则用重跑分数代替原分数。
- **前 3 名**（`reports/scores-s10.md`）：E028 0.2947、E018 0.2950、E032 0.2954。三个都通过预注册第 4 节第 1–4 条，审核子代理认定第 5 条泄漏审查也通过。三者之间的差别远小于标准误，实际上一样好。
- **给会话 4 的提示**：
  - 按预注册，第 1 名 **E028** 满足第 1–5 条，应选它。冻结的是 E028 的特征、参数（两个窗口各自调出的参数见数据目录 `experiments/E028.json`）和树的轮数。主窗口和辅助窗口调出的轮数相差 2–4 倍。重训用 2014-01–2021-06，要先写清楚轮数和参数怎么定，不要看测试结果再改（审核记录第 4 节）。
  - **风险**（审核记录第 5 节）：3 个训练区的纬度完全不重叠，纬度起了“这是哪个区”的标签作用。新区域会套用纬度最近的训练区的换算。测试 2（留出区）正好检验这一点。**不要因为这一点在测试前删掉纬度**，那等于看了验证结果再改方法。
  - 模型很依赖 Terra 的输入，而 Terra 2020 年后有漂移（`reports/findings.md` 第 7 条），报告里要写。
  - 两段式下配置里的 `zero_rule` 不起作用（审核记录第 1.1 节），读代码时别误解。
  - 2002 年 Aqua 上线前（只有 Terra）的月份不在 S10 评估范围内，S12 生成序列前要检查。

### 会话 4（2026-11-04，qiuxue-yee）

- **S11 做到哪**：按预注册第 4 节选定 LightGBM E028（逐条核对见 `docs/decisions/0008` 第 1 节）。冻结了 `harmonize.py`（默认 `fit()` 改为 `fit_lgb`，其余与 E028 源码相同）、`config/features.json`，然后用冻结程序在训练区 2014-01–2021-06 上重训，100 次整年重抽给稳定性区间，校准系数用两个验证窗口定（5.37）。答卷 `results/submission.parquet`、冻结清单 `results/freeze.json`、生成脚本 `harmonization/freeze.py` 已进 `config/frozen-manifest.json`。封卷前用假答案把冻结的阅卷函数跑通。
- **下一步**：人推 `final-test` 标签 → GitHub 阅卷（`grader.yml`）把 `results/final-test/` 提交回本分支 → `git pull` → 如实写 `reports/final-test.md`（原始/校准覆盖率按 ADR 0008 第 5 节的规则）→ S12。
- **阅卷期间不要 push 本分支**：工作流最后一步要往本分支推结果，期间有别的提交会让它推送失败。
- **S12（已完成）**：`harmonization/series_v1.py`（已提交，还没正式运行）：上线版 = 冻结的评估版（本机永远没有 2012–2013 年 S-NPP，红线 1），只有 Terra 的月份用 Terra 造 Aqua 输入再进模型（先在验证窗口上和 v0 的 M1s 链条比，`terra-check`），留出区桥接用当地 MODIS 比例（ADR 0005 第 6 条选项 B），区间按 ADR 0008 第 5 节决定要不要乘校准系数，验收 `recount()` 已在 v0 上试过（426 个区域-月，0 处不一致）。中间结果在数据目录 `s11/`。
- **S11 成绩**：测试 1 MALE 0.258（M1s 0.332），测试 2 0.644（M1s 0.857），E028 都更好；但留出区零火点和低火点指标比 M1s 差、总量偏低 20–35%（北澳除外），中西伯利亚 MALE 1.14。区间覆盖率按 ADR 0008 规则用校准后的：95.5% / 55.9%。全文 `reports/final-test.md`。
- **S12 数据集 v1**（预发布版 `dataset-v1`）：`uv run python -X utf8 -m harmonization.series_v1 build` 生成（重抽结果缓存在数据目录 `s12/`，没有缓存要重训 100 次，约 1 小时）。上线版和评估版是同一个模型（训练区 2014-01–2021-06，轮数 766/970），重训逐位复现答卷的 `est_final`。下载：`gh release download dataset-v1 --repo team-inspiratio/inspiratio-space-apps-2026`，再 `sha256sum -c SHA256SUMS.txt`。

  | 文件 | SHA256 |
  |---|---|
  | `data-interface.md` | `535aed67ec0a0e365b263c23e5e83775f42597964e83a94c7e3674420938fcf7` |
  | `dataset_v1.parquet` | `60d13babfa450b86194ae72fd1d2d8c048085b303a1e381a7685e6d23b5a559e` |
  | `california.json.gz` | `f206711f9a55bfac7f7256b8b087d7b3bbc7e684c0ef5f7c05e233be0ef98a3f` |
  | `central_siberia.json.gz` | `08e510de4bf5e5a23062158ae16fd44a3f19a028f50da402b2c98ca8ff4ea426` |
  | `cordoba.json.gz` | `703ad6f3b2343ff0a47611de6f38c7f925342a630ab512e8e59968a2d9195175` |
  | `indo_gangetic.json.gz` | `af0e3742caf0f4f253ffa2e175e17eec262e4561d3a73f938043a61e0f58f2d7` |
  | `north_australia.json.gz` | `c38ae0a87c5d79f138a0b8a5bdf5f9da2d3334a305100fb68f968fe57b963c97` |
  | `southern_africa.json.gz` | `c7b00890426b6699979f24bd1caffb6c6902d045feca9ed8ca026bce69958dda` |
  | `meta.json` | `6abc6c3663a45aa093a036b7328c0a5b6ac17652b00a2494d33ddf3290f0b8db` |
  | `region_totals_v1.csv` | `54e3cfbff46a70cd0c2318c0139b3e9a281e67f397b96cebb5c8de1076e10dda` |
  | `resamples20_v1.parquet` | `7cd6d799f3aa8a5e94c1eb1de9119eab1dab5251fe264afb0c629a8293f2c56e` |

- **给会话 5 的提示**：
  - 报告（S13）要写清楚：测试 2 的弱点（第 3 节）、区间在新区域覆盖不足、训练区 2012–2013 年在数据集里是估计值（ADR 0009 第 1 条，待人确认）、只有 Terra 的月份误差约是有 Aqua 时的 1.6 倍（ADR 0009 第 2 条）。
  - 年代偏移调查（预注册第 8 节）还没做，在 S13。
  - GFED 合理性检查里 2012–2013 年的 VIIRS 部分只能用盲审同口径的数据，本机没有。

### 会话 5（2026-11-04，qiuxue-yee）

- **S13 验证报告**：`reports/validation.md`，代码 `harmonization/validation.py`（`drift | gfed | figures | all`），6 张核心图和 2 张补充图在 `reports/figures/d1-*.png`，实现细节见 ADR 0010。
- **S14 交付**：`docs/data-card.md`、`docs/ai-usage.md`，异常指标参考实现 `harmonization/anomaly.py` 和 25 个标准测试用例 `docs/anomaly-cases.json`，`dataset_v1.csv.gz`，HANDOFF 第 6 节；细节见 ADR 0011。本机数据目录 `processed/v1` 已重新打包，包含 CSV、数据说明卡、异常用例和新的 `SHA256SUMS.txt`。
- **S15 一条命令复现**：`pipeline.py`（仓库根目录）。
  - 命令：`all --from-release`（从 Release `data-v0` 起步，约 1.5 小时）、`all`（从原始数据起步，要 FIRMS key 和约 50 GB）、`check`、`list`。
  - 每个阶段在数据目录写 `pipeline_<阶段>.done`，中断后重跑会跳过做完的阶段；加 `--force` 全部重跑。
  - 期望的数据集哈希在 `results/expected/`。
  - 验收结果：在 `D:/inspiratio-repro`（全新克隆 + 空数据目录）跑完 37/37 通过，结果写在数据目录 `pipeline_check.json`。这个目录可以删。
  - 范围、不重跑的步骤和理由见 ADR 0012。
- **许可证、Release v1、合并 main**（用户 2026-11-04 确认）：
  - 数据集用 CC BY 4.0，已写进数据说明卡和 ADR 0011。
  - PR #2 squash-merge 进 main。
  - 正式版 Release `v1`（tag 打在 main 的合并提交上）：https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/v1 。文件来自本机 `D:/inspiratio-data/processed/v1`，SHA256 和 `results/expected/dataset-v1.sha256` 一致。和预发布版 `dataset-v1` 比，数据完全相同，多了 CSV、数据说明卡、异常测试用例，接口文档也更新了。下载：`gh release download v1 --repo team-inspiratio/inspiratio-space-apps-2026`，再 `sha256sum -c SHA256SUMS.txt`。
- **给 G-global 会话的提示**：
  - main 现在是完整的里程碑 B，`feat/data-harmonization` 分支保留。继续在这个分支上工作前，先 `git merge origin/main`，让分支历史和 squash 后的 main 接上，再开新 PR。
  - 测试 2 的弱点会直接影响全球推广：留出区误差是训练区的 2.5 倍、总量偏低 14–45%、区间覆盖率只有 56%。全球产品必须标明“训练区以外的估计不确定性更大”。
  - 冻结模型只用 3 个训练区，纬度起了区域标签的作用（S10 审核记录第 5 节）。全球重跑按计划来，不要事后改冻结模型。


### 会话 G（2026-11-04，qiuxue-yee，完成）

- **分支**：`feat/data-harmonization` 先合并了 `origin/main`（squash 后的 PR #2），在这个分支上继续，最后开新 PR（ADR 0013 第 1 条）。
- **做法**：ADR 0013。代码 `harmonization/global_grid.py`、`harmonization/series_global.py`，配置 `config/regions-global.json`，一条命令 `pipeline.py global`。冻结文件没动。
- **中间结果**都在数据目录：
  - `processed/global/grid/`：全球稠密表，按纬度带分块；
  - `global/inputs/`：去重后的模型输入；
  - `global/resamples/{deploy,main,aux}/`：每次重抽一个 `.npy`，`est.npy` 是不重抽的估计。
- **重抽**：每组只用前 50 次（ADR 0013 第 5 条补充，用户已批准；aux 已有 100 次，只用前 50 次）。三组都已完成。以后要补跑，用 `uv run python -X utf8 -m harmonization.series_global resample <deploy|main|aux> --max-new 20`，会跳过已完成的（`--max-new` 让进程每 20 次退出一次）。
- **内存**：两个重抽进程并行时，主窗口两次内存不够（`_ArrayMemoryError`）。原因是长时间运行的进程占用的提交内存越来越大（上线版进程跑了 31 次后占到 34 GB）。现在**一次只跑一个进程**（先 main 再 deploy），每次重抽后释放模型。结果和并行完全一样，只是慢一些。
- **已完成**：`calibrate`（系数 16.75）→ `build`（24 分钟，S-NPP 复核 0 不符）→ `package`。发布文件在 `D:/inspiratio-data/processed/global-v1/`，`SHA256SUMS.txt` 在同一目录。
- **发布**：用户过目后（2026-11-04）发布 [Release `global-v1`](https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/global-v1)，共 30 个文件。前端文件在 Release 里是平铺的，下载后放进 `frontend/`。全部 SHA256 在 `results/expected/dataset-global-v1.sha256`，`pipeline.py check` 会对照。主要文件：
  - `dataset_global-v1.parquet`：`446cd805725bd7e313e54874944b52bcc56962008a30b9f4473aa077d0205114`
  - `region_totals_global-v1.csv`：`52f77eee3004b0e2ba5648b1c9f82376aacaa2ffdd36d6a8c702aebd03a0f6b3`
  - `resamples20_global-v1.parquet`：`44aa476ac0e96e6035126218d8b6f0345c4897776e4b61f11499077f8a000a3a`
  - `meta.json`：`52c9c5a1a0723941073090a5494ff7a1d02790e4b4be41c48fac8ad30b3c513e`
- **接下来**：PR（feat/data-harmonization → main）等人合并。
- **本机测试注意**：中文 Windows 上 `tests/test_guardrails.py` 读 `git log` 时会按 GBK 解码出错，要用 `PYTHONUTF8=1 uv run pytest` 跑；CI（Linux）不受影响。`tools/guardrails.py` 是冻结文件，没改。
