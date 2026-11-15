# PROGRESS：项目进度

> 机器可读的状态块在下面两行注释之间，格式是 YAML。每个会话开始时读它、认领时改它、每完成一个阶段更新它。
> `tests/test_progress.py` 会检查它的格式。

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/3-model.md   # 下一张（或正在做的）任务卡
status: ready                           # ready | in_progress | blocked | done
claimed_by: ""                          # 认领人名字；空表示无人认领
claimed_at: ""                          # 认领时间，ISO 8601 UTC，例如 2026-11-03T08:00:00Z
last_pushed_stage: S09                  # 最后一个完成并 push 的阶段
last_pushed_at: 2026-11-03
branch: feat/data-harmonization
data_release: data-v0                   # gh release download data-v0；SHA256 见交接备注；里程碑 A 数据在 milestone-a
next_step: "开新会话执行任务卡 3-model：S10 LightGBM 初版 + AI 自动实验 + 独立审核"
needs_human:
  - "待人决定：NOAA-20 接续的通过标准（docs/decisions/0005 第 4 条；标准是看了检验结果后提出的）"
  - "待人决定：留出区的 Terra 桥接用训练区合并比例还是当地 MODIS 比例（docs/decisions/0005 第 6 条，影响 S12 上线版）"
  - "待人确认：QM 细节、λ 选择、桥接年份、v0 来源规则（docs/decisions/0005 第 1–3、5 条）"
  - "通知前端：milestone-a 预发布版 + docs/data-interface.md 已可用（PR #2 已留言）"
  - "GitHub CLI 登录：这台电脑已登录可跳过；换电脑接力先运行 gh auth login --web（下载 Release 数据要用）"
```
<!-- STATUS:END -->

## 会话总览

| 会话 | 任务卡 | 覆盖阶段 | 状态 |
|---|---|---|---|
| 0 | （本仓库搭建） | S00 | ✅ 完成 |
| 1 | [`1-data`](docs/sessions/1-data.md) | S01–S06 | ✅ 完成 |
| 2 | [`2-baselines`](docs/sessions/2-baselines.md) | S07–S09（里程碑 A） | ✅ 完成 |
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | ⏭ 下一张 |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | 待开始 |
| 5 | [`5-report`](docs/sessions/5-report.md) | S13–S15（里程碑 B） | 待开始 |
| G | [`G-global`](docs/sessions/G-global.md) | 全球重跑 | 待开始（S15 之后） |

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
| S10 | LightGBM 和 AI 实验 | ⬜ todo | | | |
| S11 | 冻结与外部盲审 | ⬜ todo | | | |
| S12 | 最终数据集 | ⬜ todo | | | |
| S13 | 验证报告（D1） | ⬜ todo | | | |
| S14 | 交付 | ⬜ todo | | | |
| S15 | ★里程碑 B：一条命令复现、Release v1、合并 main | ⬜ todo | | | |

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
