> **Rehearsal replay.** This repository replays, stage by stage, work that Team Inspiratio finished **before the event** (2026-11-02 to 2026-11-08) in a private draft repository. Commit times are replay times, not development times. See [SIMULATION.md](SIMULATION.md).

# MODIS × VIIRS 火点协调

<!-- PROGRESS-BOX:BEGIN -->
> **当前进度 / Status**：里程碑 B 完成（S00–S15）。最终数据集 v1 已作为正式版 [Release `v1`](https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/v1) 发布（CC BY 4.0），说明见 [docs/data-card.md](docs/data-card.md)，前端接口见 [docs/data-interface.md](docs/data-interface.md)。最终模型是两段式 LightGBM（E028），外部盲审只考了一次：训练区 2012–2013 年的 MALE 0.258（简单比例法 M1s 0.332），完全没见过的留出区 0.644（M1s 0.857），验证报告见 [reports/validation.md](reports/validation.md)。一条命令复现：`uv run python -X utf8 pipeline.py all --from-release`（约 1.5 小时，37 项核对）。下一步：任务卡 [`G-global`](docs/sessions/G-global.md)（全球重跑）。
> Status: milestone B done. Dataset v1 is Release `v1` (CC BY 4.0); read `docs/data-card.md`. Final test (run once on GitHub): MALE 0.258 on the training regions 2012-2013 (M1s 0.332), 0.644 on unseen holdout regions (M1s 0.857). Reproduce with `pipeline.py all --from-release`. Next: task card `G-global`.
>
> **接力三步 / Take over in 3 steps**：① 按 [HANDOFF.md](HANDOFF.md) 装好环境、填好 `.env`；② 把 HANDOFF 里的“通用接力提示词”复制给 Claude Code 或 Codex；③ 按 AI 的提示做需要你本人做的事。详细进度见 [PROGRESS.md](PROGRESS.md)。
<!-- PROGRESS-BOX:END -->

把 MODIS（2000 年起）和 VIIRS（2012 年起）两代卫星的火点记录统一成一条可以前后比较的月度序列，再用一个网页让人选区域、看历史、判断最近一个完整月份是否偏高，并下载结果。

**完整方案：[docs/proposal.md](docs/proposal.md)**

## 一分钟看懂

- **问题：** 两种传感器的分辨率和灵敏度不同，VIIRS 看到的火点数明显更多。直接拼接，2012 年会出现一个由换卫星造成、而不是火情变化造成的跳变。
- **做法：** 用两者同时在轨的年份训练模型，只看 MODIS 的信息来预测 VIIRS 会记录多少火点，再把这个换算用到 2012 年以前。主模型是 LightGBM，简单比例法作为对照基线；AI 自动实验循环在验证集上帮忙改进模型。
- **验证：** 用后面的年份推前面的年份，另留一个完全没见过的地区；验证集选模型，测试集锁住，只在模型冻结后跑一次、如实报告。
- **产出：** 协调算法、公开数据集、网页三件套，加上一份方法与验证说明。

## 方案目录

| 部分 | 内容 |
|---|---|
| [项目概览](docs/proposal.md#项目概览) | 问题、解法、交付物 |
| [用大白话讲](docs/proposal.md#用大白话讲这个项目在干什么) | 不懂遥感也能看懂的解释 |
| [方案](docs/proposal.md#方案用机器学习把历史统一到-viirs-尺度) / [验证](docs/proposal.md#验证怎么证明模型可信) | 主提案的核心 |
| [网页成果](docs/proposal.md#网页成果) / [实施范围](docs/proposal.md#实施范围) | 用户能做什么、必做与扩展 |
| [附录：执行手册](docs/proposal.md#附录执行手册) | 数据、算法、验证体系、AI 循环、24 个任务、提交物、风险、参考资料 |

## 仓库结构

```
README.md               本文件
AGENTS.md / CLAUDE.md   给 AI 的项目规则
PROGRESS.md             进度（机器可读状态块 + 阶段表）
HANDOFF.md              接力说明和通用接力提示词（中英文）
docs/proposal.md        完整方案（主提案 + 执行手册）
docs/execution-plan.md  数据分析与算法部分的执行计划（唯一依据）
docs/sessions/          各会话的任务卡
tools/                  护栏和环境预检脚本
tests/                  pytest
notes/                  阅读和学习笔记
pyproject.toml, uv.lock Python 依赖（用 uv sync 安装）
.env.example            密钥模板（复制成 .env，.env 不提交）
```

## 约定

- 改动走分支和 Pull Request，不直接推 main。
- 密钥（如 FIRMS MAP_KEY）只放在本地 `.env`。
- 原始数据和处理后的大文件不进仓库，来源和下载方式写在文档里。
