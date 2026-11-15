# PROGRESS：项目进度

> 机器可读的状态块在下面两行注释之间，格式是 YAML。每个会话开始时读它、认领时改它、每完成一个阶段更新它。
> `tests/test_progress.py` 会检查它的格式。

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/4-freeze-test.md   # 下一张（或正在做的）任务卡
status: in_progress                     # ready | in_progress | blocked | done
claimed_by: "qiuxue-yee"                # 认领人名字；空表示无人认领
claimed_at: "2026-11-04T03:00:28Z"    # 认领时间，ISO 8601 UTC，例如 2026-11-03T08:00:00Z
last_pushed_stage: S10                  # 最后一个完成并 push 的阶段
last_pushed_at: 2026-11-04
branch: feat/data-harmonization
data_release: data-v0                   # gh release download data-v0；SHA256 见交接备注；里程碑 A 数据在 milestone-a
next_step: "S11 答卷已封存（E028，results/submission.parquet 已进冻结清单）。等人推送 final-test 标签、GitHub 阅卷把 results/final-test/ 提交回本分支后，git pull，写 reports/final-test.md，再做 S12"
needs_human:
  - "现在由人做：在仓库文件夹运行 git pull，再运行 git tag final-test && git push origin final-test（只能考一次，AI 不能自己推）。阅卷跑完之前不要往 feat/data-harmonization 推任何提交"
  - "请过目：S10 审核记录 reports/model-review.md（结论：前 3 名都通过泄漏审查；风险：纬度在只有 3 个训练区时起了区域标签的作用，留出区可能变差，测试 2 会检验）"
  - "待人决定：NOAA-20 接续的通过标准（docs/decisions/0005 第 4 条；标准是看了检验结果后提出的）"
  - "待人决定：留出区的 Terra 桥接用训练区合并比例还是当地 MODIS 比例（docs/decisions/0005 第 6 条，影响 S12 上线版）"
  - "待人确认：QM 细节、λ 选择、桥接年份、v0 来源规则（docs/decisions/0005 第 1–3、5 条）"
  - "已记录：S10 LightGBM 与实验循环的实现细节（docs/decisions/0006），按用户授权由 AI 决定"
  - "已记录：S10 预算缩减、截止时间和补救重跑是用户的决定（docs/decisions/0007）"
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
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | ✅ 完成 |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | 🔄 进行中（qiuxue-yee） |
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
| S10 | LightGBM 和 AI 实验 | ✅ done | 2026-11-04 | 37 次实验（E000–E036，预算按 ADR 0007 缩减并提前收工）；最佳验证 MALE：E028 两段式 LightGBM 0.2947，比 M1s（0.3766）低 21.8%（差 −0.082 ± 0.016，95% 区间 −0.113～−0.053），比 QM 低 0.169；前 3 名都通过护栏和泄漏审查（`reports/scores-s10.md`、`reports/model-review.md`） | |
| S11 | 冻结与外部盲审 | 🔄 答卷已封存，等人推 final-test 标签 | | 按预注册选定 E028（5 条门槛全过）；重训 2014-01–2021-06，轮数 766/970；答卷 596,032 行 + 100 列重采样，校准系数 5.37（`docs/decisions/0008`、`results/freeze.json`） | |
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
- **S12 半成品**：`harmonization/series_v1.py`（已提交，还没正式运行）：上线版 = 冻结的评估版（本机永远没有 2012–2013 年 S-NPP，红线 1），只有 Terra 的月份用 Terra 造 Aqua 输入再进模型（先在验证窗口上和 v0 的 M1s 链条比，`terra-check`），留出区桥接用当地 MODIS 比例（ADR 0005 第 6 条选项 B），区间按 ADR 0008 第 5 节决定要不要乘校准系数，验收 `recount()` 已在 v0 上试过（426 个区域-月，0 处不一致）。中间结果在数据目录 `s11/`。
