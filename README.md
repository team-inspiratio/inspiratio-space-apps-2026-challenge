> **Rehearsal replay.** This repository replays, stage by stage, work that Team Inspiratio finished **before the event** (2026-11-02 to 2026-11-08) in a private draft repository. Commit times are replay times, not development times. See [SIMULATION.md](SIMULATION.md).

# MODIS × VIIRS 火点协调

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
README.md          本文件
docs/proposal.md   完整方案（主提案 + 执行手册）
notes/             阅读和学习笔记
requirements.txt   Python 依赖
.env.example       密钥模板（复制成 .env，.env 不提交）
```

## 约定

- 改动走分支和 Pull Request，不直接推 main。
- 密钥（如 FIRMS MAP_KEY）只放在本地 `.env`。
- 原始数据和处理后的大文件不进仓库，来源和下载方式写在文档里。
