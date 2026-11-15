# PROGRESS：项目进度

> 机器可读的状态块在下面两行注释之间，格式是 YAML。每个会话开始时读它、认领时改它、每完成一个阶段更新它。
> `tests/test_progress.py` 会检查它的格式。

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/1-data.md   # 下一张（或正在做的）任务卡
status: in_progress                     # ready | in_progress | blocked | done
claimed_by: "qiuxue-yee"                # 认领人名字；空表示无人认领
claimed_at: "2026-11-03T18:48:11Z"      # 认领时间，ISO 8601 UTC，例如 2026-11-03T08:00:00Z
last_pushed_stage: S03                  # 最后一个完成并 push 的阶段
last_pushed_at: 2026-11-03
branch: feat/data-harmonization
next_step: "任务卡 1-data 继续：S04 写 reports/cleaning.md → S05 跑完 grid 并验证总数守恒 → S06 写 findings.md → 上传 data-v0 Release（见交接备注 S01–S03）"
needs_human:
  - "待人确认：冻结的 tools/guardrails.py 在中文 Windows 上读 git 历史会按 GBK 崩溃，目前用 -X utf8 绕开；是否由人 [unfreeze] 修编码（docs/decisions/0002）"
  - "数据阶段需要约 50 GB 磁盘、16 GB 以上内存；.env 里填好 FIRMS_MAP_KEY 和 INSPIRATIO_DATA_DIR"
  - "GitHub CLI 登录：在这台已登录的电脑上接力可以跳过；换电脑接力时先运行一次 gh auth login --web（会话 1 结束时要用 gh 上传 Release 数据包）"
```
<!-- STATUS:END -->

## 会话总览

| 会话 | 任务卡 | 覆盖阶段 | 状态 |
|---|---|---|---|
| 0 | （本仓库搭建） | S00 | ✅ 完成 |
| 1 | [`1-data`](docs/sessions/1-data.md) | S01–S06 | 🔄 进行中（qiuxue-yee） |
| 2 | [`2-baselines`](docs/sessions/2-baselines.md) | S07–S09（里程碑 A） | 待开始 |
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | 待开始 |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | 待开始 |
| 5 | [`5-report`](docs/sessions/5-report.md) | S13–S15（里程碑 B） | 待开始 |
| G | [`G-global`](docs/sessions/G-global.md) | 全球重跑 | 待开始（S15 之后） |

## 阶段表

| 阶段 | 内容 | 状态 | 完成时间 | 关键数字 | commit |
|---|---|---|---|---|---|
| S00 | 环境、护栏、CI、自说明文件 | ✅ done | 2026-11-03 | CI 绿；pytest 17 项通过 | 3dcf808 |
| S01 | 预注册（settings、留出区、随机矩形、grader.yml） | ✅ done | 2026-11-03 | 6 区（3 训练 + 3 留出）；3300 个矩形；冻结 5 个文件 | 7d1aa0c |
| S02 | 下载（年度包、API 2026、缺测清单、GFED） | ✅ done | 2026-11-03 | 46 个年度包（约 9 GB，跳过锁定年份）；API 918 个卫星-日；GFED 24 年；缺测 178 天；抽 4 天×3 源比对：年度包每行都在 API 中 | 7df072f |
| S03 | 导入（流式转 Parquet，丢弃留出区 VIIRS） | ✅ done | 2026-11-03 | 46 个年度包 + 6 个 API 源，每个文件 原始行数 = 写入 + 留出区丢弃（`docs/ingest-ledger.csv`）；VIIRS 压缩包已删除 | 见下一条 commit |
| S04 | 清洗 | ⬜ todo | | | |
| S05 | 网格化与特征 | ⬜ todo | | | |
| S06 | 数据体检（A5） | ⬜ todo | | | |
| S07 | 判卷机器（prepare、evaluate） | ⬜ todo | | | |
| S08 | 保底模型 M0、M1s、QM；桥接与接续 | ⬜ todo | | | |
| S09 | ★里程碑 A：数据集 v0、前端导出、预发布版 | ⬜ todo | | | |
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

### 会话 1 中断交接（2026-11-03，额度用完）

- **已完成并 push**：S01（预注册、冻结 5 个文件）、S02（下载与比对）、S03（导入，账目闭合）。S04–S06 的代码已提交（`harmonization/clean.py`、`grid.py`、`explore.py`）。
- **数据目录里已经跑完的**：`interim/points/`（导入结果）、`processed/clean/`（清洗结果，规则计数在 `docs/cleaning-counts.csv`，抽查样本 `docs/removed-sample.csv`，都已提交）。中断时 `python -m harmonization.grid` 和 `explore` 正在后台跑（日志 `D:/inspiratio-data/logs/s03-06-final.log`）；如果没有 `D:/inspiratio-data/S05.done` 和 `S06.done`，就重跑这两条命令（几分钟）。
- **下一步**：
  1. S04：根据 `docs/cleaning-counts.csv` 和 `docs/removed-sample.csv` 写 `reports/cleaning.md`（每条规则删多少；20 条抽查结论；注明 NRT 段用 SP type=2 的约 1 km 格子 + 8 邻格做固定热源掩膜；API 比年度包多约 0.4% 的海上点，绝大多数 type=3）。
  2. S05：`uv run python -X utf8 -m pytest`（总数守恒测试在有数据时自动运行），提交 `config/features.json`、`docs/month-status.csv`。
  3. S06：看 `reports/figures/` 4 张图和 `reports/a5-stats.json`，写 `reports/findings.md`。试跑时的观察：NOAA-20/S-NPP 中位数约 0.98–1.00；S-NPP/Aqua 比值随季节波动大（约 3–20 倍），2021-07 前后没有明显跳变；S-NPP 2026-05 整月缺测。
  4. 上传 Release `data-v0`（预发布）：建议 `processed/grid/*.parquet` + MODIS 清洗后点数据（约 1.2 GB）；VIIRS 清洗后点数据约 4.6 GB，超出任务卡“约 1–2 GB”，建议不传（标签已在网格表里，可用哈希锁定的原始数据重建）——这一点需要人确认。SHA256 记进 PROGRESS 和数据清单。
  5. 状态块改为卡 2、README 进度框同步、确认 CI 绿。
- **注意**：本机跑护栏和测试要加 `-X utf8`（`docs/decisions/0002`）。Claude 钩子会把提交信息里同时出现“锁定年份 + 下载”字样的命令误拦，提交信息别这样写。
