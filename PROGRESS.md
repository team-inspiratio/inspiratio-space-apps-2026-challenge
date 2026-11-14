# PROGRESS：项目进度

> 机器可读的状态块在下面两行注释之间，格式是 YAML。每个会话开始时读它、认领时改它、每完成一个阶段更新它。
> `tests/test_progress.py` 会检查它的格式。

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/1-data.md   # 下一张（或正在做的）任务卡
status: ready                           # ready | in_progress | blocked | done
claimed_by: ""                          # 认领人名字；空表示无人认领
claimed_at: ""                          # 认领时间，ISO 8601 UTC，例如 2026-11-03T08:00:00Z
last_pushed_stage: S00                  # 最后一个完成并 push 的阶段
last_pushed_at: 2026-11-03
branch: feat/data-harmonization
next_step: "开新会话执行任务卡 1-data：S01 预注册 → S02 下载 → S03 导入 → S04 清洗 → S05 网格化 → S06 数据体检"
needs_human:
  - "数据阶段需要约 50 GB 磁盘、16 GB 以上内存；.env 里填好 FIRMS_MAP_KEY 和 INSPIRATIO_DATA_DIR"
  - "GitHub CLI 登录：在这台已登录的电脑上接力可以跳过；换电脑接力时先运行一次 gh auth login --web（会话 1 结束时要用 gh 上传 Release 数据包）"
```
<!-- STATUS:END -->

## 会话总览

| 会话 | 任务卡 | 覆盖阶段 | 状态 |
|---|---|---|---|
| 0 | （本仓库搭建） | S00 | ✅ 完成 |
| 1 | [`1-data`](docs/sessions/1-data.md) | S01–S06 | ⏭ 下一张 |
| 2 | [`2-baselines`](docs/sessions/2-baselines.md) | S07–S09（里程碑 A） | 待开始 |
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | 待开始 |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | 待开始 |
| 5 | [`5-report`](docs/sessions/5-report.md) | S13–S15（里程碑 B） | 待开始 |
| G | [`G-global`](docs/sessions/G-global.md) | 全球重跑 | 待开始（S15 之后） |

## 阶段表

| 阶段 | 内容 | 状态 | 完成时间 | 关键数字 | commit |
|---|---|---|---|---|---|
| S00 | 环境、护栏、CI、自说明文件 | ✅ done | 2026-11-03 | CI 绿；pytest 17 项通过 | 3dcf808 |
| S01 | 预注册（settings、留出区、随机矩形、grader.yml） | ⬜ todo | | | |
| S02 | 下载（年度包、API 2026、缺测清单、GFED） | ⬜ todo | | | |
| S03 | 导入（流式转 Parquet，丢弃留出区 VIIRS） | ⬜ todo | | | |
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
