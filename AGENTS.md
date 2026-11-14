# AGENTS.md：给 AI 的项目规则（Claude Code、Codex、Cursor 通用）

> English summary for non-Chinese readers: this file is binding for any AI agent working in this
> repo. Read it fully, then `PROGRESS.md`, then the task card it points to. Red lines below are
> enforced by CI (`tools/guardrails.py`) no matter which AI tool you use.

## 项目是什么

把 MODIS（2000 年起）和 VIIRS（2012 年起）的火点记录协调成 **VIIRS 尺度的月度序列**（0.25° 格子 × 自然月，2000-11 至 2026-10），交给前端做燃烧日历网页。本仓库这条线只负责数据分析和算法；前端、提案、Demo 由队友负责。

- **唯一依据**：[`docs/execution-plan.md`](docs/execution-plan.md)（执行计划 v4）。[`docs/proposal.md`](docs/proposal.md) 是背景，两者冲突时以执行计划为准。
- **进度**：[`PROGRESS.md`](PROGRESS.md) 顶部的状态块。
- **任务卡**：[`docs/sessions/`](docs/sessions/)，一个会话做一张卡。
- **人类接力说明**：[`HANDOFF.md`](HANDOFF.md)。

## 红线（违反任何一条都要立刻停下，告诉人）

1. **测试集隔离（计划第 4 节）**
   - 本机**永远不下载** 2012 年和 2013 年的 S-NPP VIIRS 数据（年度包、API、任何镜像都不行）。只有 GitHub Actions 的阅卷工作流 `grader.yml` 可以下载它们。
   - 留出区（S01 登记在 `config/regions.json`）的 VIIRS 记录在导入时直接丢弃，不写入磁盘。模型冻结前不看、不画、不统计留出区的 VIIRS。
   - 所有下载代码在发请求前必须调用 `tools/guardrails.py` 里的 `assert_download_allowed(source, start, end)`。
   - 最终测试只能考一次：推送 `final-test` 标签由人决定，AI 不得自行推送这个标签。
2. **不准改冻结文件**：`config/frozen-manifest.json` 里列出的文件（S01 起会有 settings、留出区、grader；S07 起有 prepare、evaluate）只有人能改。解冻必须由人在提交信息里写 `[unfreeze]` 并说明理由。
3. **禁用特征**：年份、地区名、任何 VIIRS 信息都不能做模型输入。特征列表放在 `config/features.json`，CI 会检查。
4. **密钥**：FIRMS MAP_KEY 只放在 `.env`（已被 gitignore）。不要打印、不要读进对话、不要写进任何文件、日志、提交信息或 PR。代码里用 `python-dotenv` 读取。
5. **方法不自由发挥**：模型只做 M0、M1s、QM（分位数映射）、LightGBM（计划第 2 节）。数据切分、评估指标、选定规则都按计划和预注册来，不能看了分数再改。
6. **不直接推 main**：在 `feat/data-harmonization` 分支上工作，通过 PR 合并（S15 时 squash-merge）。

护栏有三层：Claude Code 钩子（`.claude/settings.json`，最早拦截）、pre-commit（提交前）、CI（每次 push，最终裁决）。**用 Codex 等其他工具时没有钩子，所以要自己对照红线**；CI 一样会把违规提交标红。

## 开工流程（每个会话都一样）

1. **读进度**：读本文件和 `PROGRESS.md`。用大白话向人汇报：项目做到哪一步、下一张任务卡是哪张、需要人准备什么（看状态块里的 `needs_human` 和任务卡的“需要人准备”）。
2. **认领**：看状态块的 `claimed_by` 和 `claimed_at`。如果别人在 12 小时内认领了同一张卡，**立刻停下**告诉人。否则写上认领人（问人要名字）和当前 UTC 时间，`status` 改为 `in_progress`，commit 并 push。push 被拒时先 `git pull --rebase`，再看一次认领信息。
3. **预检**：运行 `uv sync`，再运行 `uv run python tools/preflight.py`（数据阶段加 `--need-gb 50`）。有 `[FIX]` 项时，能自己修的修好；需要人本人做的（申请 FIRMS key、`gh auth login --web`、装软件需要授权、填 `.env`）停下来一步一步教人做。
4. **执行任务卡**：只读任务卡指定的计划章节，按顺序做它列出的阶段。
5. **每完成一个阶段（S 级）**：`uv run pytest` → 更新 `PROGRESS.md`（阶段表、状态块）→ commit → push。长阶段中途也定期 push。
6. **结束**：任务卡验收全部通过后，状态块改为下一张卡、`status: ready`、清空认领；README 顶部进度框同步更新；push 后确认 CI 是绿的。

## 遇到不确定的事

- 任务卡和计划都没覆盖的决定：写一份 `docs/decisions/NNNN-简短标题.md`（背景、选项、你的建议），在 `PROGRESS.md` 的 `needs_human` 里加一条“待人确认：…”，然后**停下问人**或先做不受影响的部分。不要擅自改变方法、数据切分或评估规则。
- 计划里明确写“需要团队确认”的事（例如留出区），必须等人确认后再提交。
- 快没额度或要中断时：先把已完成的部分 push，再在 `PROGRESS.md` 的“交接备注”写清楚做到哪里、下一步做什么、有没有半成品文件。

## 环境约定

- Python 3.12，用 `uv` 管理（`uv sync` 按 `uv.lock` 装）。不需要 GPU。
- 代码统一用 `pathlib`，不写只能在 PowerShell 或只能在 bash 下跑的脚本；CI 在 Linux 上跑，保证 Mac/Linux 也能用。
- 原始数据和处理后的大文件**不进 git**，放在 `.env` 里 `INSPIRATIO_DATA_DIR` 指向的目录（本机是 `D:/inspiratio-data`）。每个数据阶段结束时，处理后的 Parquet 上传为 GitHub Release 附件并记录 SHA256。
- Windows 上路径可能过长：仓库已开 `git config core.longpaths true`，项目放在短路径下。
- LightGBM 开确定性模式、固定种子。
- 每个阶段写 `.done` 标记（放在数据目录），支持断点续跑。
- **Codex 用户**：需要允许联网和执行命令（下载数据、跑测试、push 都要用到）。

## 仓库地图

```
AGENTS.md / CLAUDE.md     AI 规则（本文件；CLAUDE.md 引用本文件）
PROGRESS.md               进度状态块 + 阶段表 + 交接备注
HANDOFF.md                人类接力说明 + 通用接力提示词（中英文）
docs/execution-plan.md    执行计划（唯一依据）
docs/proposal.md          原始提案（背景）
docs/sessions/            任务卡：1-data、2-baselines、3-model、4-freeze-test、5-report、G-global
docs/decisions/           待人确认或已确认的决定记录
config/                   settings、regions、features、frozen-manifest（S01 起）
tools/guardrails.py       护栏（CI、pre-commit、钩子共用）
tools/preflight.py        环境预检
tests/                    pytest
.claude/                  Claude Code 钩子
.github/workflows/        ci.yml（每次 push）；grader.yml（S01 提交，外部盲审）
```

## 常用命令

```bash
uv sync                                   # 装环境
uv run python tools/preflight.py          # 预检
uv run pytest                             # 测试
uv run ruff check . && uv run ruff format .
uv run python tools/guardrails.py check   # 护栏
uv run pre-commit install                 # 每个 clone 装一次提交前检查
```
