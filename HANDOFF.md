# HANDOFF：接力说明 / Relay guide

> 你不需要了解这个项目。按下面的准备清单装好环境，然后把“通用接力提示词”整段复制给 AI（Claude Code 或 Codex），它会自己读进度、告诉你现在在哪一步、需要你做什么。
>
> You don't need to know this project. Prepare your machine with the checklist below, then paste the
> "universal relay prompt" into your AI tool (Claude Code or Codex). It will read the progress
> file, tell you where things stand and what you need to do.

## 1. 准备清单 / Checklist

| 步骤 | 中文 | English |
|---|---|---|
| 1 | 安装 [Git](https://git-scm.com/downloads)、[uv](https://docs.astral.sh/uv/getting-started/installation/)、[GitHub CLI](https://cli.github.com)。 | Install Git, uv and GitHub CLI. |
| 2 | 运行 `gh auth login --web`，在浏览器里授权（需要有本仓库权限）。 | Run `gh auth login --web` and approve in the browser (you need access to this repo). |
| 3 | `gh repo clone team-inspiratio/inspiratio-space-apps-2026 inspiratio`，然后 `cd inspiratio`，`git switch feat/data-harmonization`。Windows 上先运行 `git config --global core.longpaths true`，并把项目放在短路径下。 | Clone, `cd` in, switch to `feat/data-harmonization`. On Windows enable long paths and use a short folder path. |
| 4 | 免费申请自己的 FIRMS MAP_KEY（1 分钟）：<https://firms.modaps.eosdis.nasa.gov/api/map_key/>。 | Get your own free FIRMS MAP_KEY (1 minute). |
| 5 | 把 `.env.example` 复制为 `.env`，填 `FIRMS_MAP_KEY=你的key` 和 `INSPIRATIO_DATA_DIR=数据目录`（放在仓库外面，例如 `D:/inspiratio-data` 或 `~/inspiratio-data`）。**`.env` 永远不要提交、不要发给别人、不要贴给 AI。** | Copy `.env.example` to `.env`, fill in your key and a data folder outside the repo. Never commit, share or paste `.env`. |
| 6 | `uv sync`，然后 `uv run pre-commit install`，再 `uv run python tools/preflight.py` 看看缺什么。 | Run `uv sync`, `uv run pre-commit install`, then the preflight script. |

**机器要求 / Machine**：数据阶段（任务卡 1、G）约 50 GB 磁盘、16 GB 以上内存；其他阶段直接下载 Release 里的处理后数据，普通笔记本就够。不需要 GPU。Data stages need ~50 GB disk and 16 GB+ RAM; later stages use the processed data from GitHub Releases and run on a normal laptop. No GPU.

**AI 工具 / AI tool**：Claude Code 直接用（仓库自带钩子）。Codex 需要允许联网和执行命令。Claude Code works out of the box (the repo ships hooks). Codex needs network and command execution enabled.

## 2. 通用接力提示词（中文）

任何时候都用同一段，AI 会自己判断进度。把【我的名字】换成你的名字：

```
你在接力一个进行中的数据分析项目（MODIS×VIIRS 火点协调）。请严格按仓库规则做，不要自由发挥。
1. 先读 AGENTS.md 和 PROGRESS.md，用大白话告诉我：项目做到哪一步了、下一张任务卡是哪张、我需要准备什么。
2. 看 PROGRESS.md 的认领信息：如果别人在 12 小时内认领了同一张卡，立刻停下告诉我；否则把认领人写成"【我的名字】"并写上当前时间，然后 commit 并 push。
3. 按 AGENTS.md 的清单做环境预检。需要我本人做的事（申请 FIRMS key、登录 GitHub、安装软件需要授权），停下来一步一步教我做。
4. 执行任务卡，只读任务卡指定的计划章节。每完成一个阶段：跑测试 → 更新 PROGRESS.md → commit → push。
5. 任务卡没有覆盖到的决定，写进 docs/decisions/，并在 PROGRESS.md 里标成"待人确认"。不要擅自改变方法、数据切分或评估规则。
6. 快没额度或要中断时，先把已完成的部分 push，再在 PROGRESS.md 里写清楚"做到哪里了、下一步做什么"。
```

## 3. Universal relay prompt (English)

Same content, for teammates who don't read Chinese. Replace [MY NAME] with your name:

```
You are taking over an ongoing data-analysis project (MODIS x VIIRS active-fire harmonization). Follow the repository rules strictly; do not improvise.
1. First read AGENTS.md and PROGRESS.md and tell me in plain language: how far the project has got, which task card is next, and what I need to prepare.
2. Check the claim fields in PROGRESS.md: if someone else claimed the same card within the last 12 hours, stop immediately and tell me. Otherwise set the claimant to "[MY NAME]" with the current time, then commit and push.
3. Run the environment preflight from AGENTS.md. For anything I must do myself (getting a FIRMS key, logging in to GitHub, installing software that needs approval), stop and walk me through it step by step.
4. Execute the task card, reading only the plan sections it names. After each stage: run the tests -> update PROGRESS.md -> commit -> push.
5. For any decision the task card does not cover, write it up in docs/decisions/ and mark it "awaiting human confirmation" in PROGRESS.md. Do not change the method, data splits or evaluation rules on your own.
6. When you are running out of quota or need to stop, push what is finished first, then write in PROGRESS.md exactly where you stopped and what comes next.
```

## 4. 指定任务卡的一行版 / One-liner for a specific card

用于重做或指定某个阶段 / To redo or run a specific card:

```
按 AGENTS.md 的规则，执行 docs/sessions/3-model.md。
```

```
Following the rules in AGENTS.md, execute docs/sessions/3-model.md.
```

## 5. 常见问题 / FAQ

- **数据从哪来？** 会话 1 从 FIRMS 下载并处理；之后每个会话结束都把处理后的数据上传为 GitHub Release 附件，`PROGRESS.md` 记录用哪个 Release 和 SHA256。下载：`gh release download <标签> -D <你的数据目录>`。
- **CI 红了怎么办？** 把 Actions 的报错贴给 AI，让它按 AGENTS.md 修；如果是护栏（guardrails）报的错，说明碰了红线，先问人。
- **测试集是什么、为什么我不能下载 2012/2013 年 S-NPP？** 那是最终考试的标准答案，只由 GitHub Actions 在云端下载并打分，只能考一次。谁接力规则都一样。
- **Where does the data come from?** Session 1 downloads and processes it; each later session publishes processed data as a GitHub Release asset, recorded with SHA256 in `PROGRESS.md`.
- **Why can't I download 2012/2013 S-NPP data?** It is the locked test set. Only the GitHub Actions grader downloads it, and the test runs exactly once.
