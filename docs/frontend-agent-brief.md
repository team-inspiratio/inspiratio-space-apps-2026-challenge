# 给前端 / 网页 agent 的简报

> **English summary for agents:** you are building the burn-calendar website on top of a finished,
> published dataset. Read this file first (about 5 minutes), then only the docs it points to.
> Do **not** read the data-pipeline code, the execution plan or the task cards; they are history.
> The data is final: do not regenerate it, retrain anything or "fix" numbers on the front end.
> Section 7 has a prompt to paste into a fresh agent.

这份文件把数据这条线两天里的结论压缩成网页 agent 需要知道的东西。数据已经做完、发布了，网页只负责**用好它、讲清楚它**。数据线的完整经过和每个决定的理由在 [`docs/project-journey.md`](project-journey.md)，需要讲故事时再看。

## 1. 网页要做什么

一条流程（提案“网页成果”一节）：**选区域 → 看燃烧日历 → 判断最近一个月是否异常 → 下载**。

1. **选区域**：在地图上点选预设区域，或者画框、画多边形，或者输入经纬度。
2. **看历史**：燃烧日历，每行一年、每列一月，颜色表示火点多少。鼠标悬停显示数值、来源标记和区间。可以切换“协调后 / 直接拼接”做对比，这是 Demo 的核心画面。
3. **最近月份卡片**：最近一个完整月份是历史同月中位数的几倍，排在历史第几百分位，写成“偏高 / 正常 / 偏低”。
4. **下载**：月度 CSV、日历图片。

不做火灾预测。

## 2. 用哪份数据

| 用途 | Release | 说明文档 |
|---|---|---|
| **主数据：世界地图 + 任意区域** | `global-v1`（CC BY 4.0） | [`docs/data-interface-global.md`](data-interface-global.md) |
| 示范区版（6 个区，经过一次外部盲审的模型） | `v1`（CC BY 4.0） | [`docs/data-interface.md`](data-interface.md) |

下载：

```bash
gh release download global-v1 --repo team-inspiratio/inspiratio-space-apps-2026 -D data/global-v1
```

下载后用 `sha256sum -c SHA256SUMS.txt` 核对。不需要 FIRMS key，也不需要 Python。

**网页通常只需要这几个文件：**

- `frontend/index.json`：所有可选区域的清单，含名字、角色、外包矩形和文件名。
- `frontend/<名字>.json.gz`：每个区一个，按需加载。压缩后 0.1–5 MB，最大的 BOAS 解压后约 57 MB，**不要一次全读**。
- `region_totals_global-v1.csv`：区 × 月的总量，很小，适合做世界总览。
- `resamples20_global-v1.parquet`（663 MB）：只在“用户自己圈区域还要显示区间”时才需要。可以先不做区间，或者放到后端处理。

JSON 格式、字段、来源标记见 `data-interface.md` 第 3–4 节；全球版不同的地方见 `data-interface-global.md` 第 1 节。

## 3. 必须照做的规则

- **用户圈选区域**：把落在区域里的格子按月加总。做法见 `data-interface.md` 第 5 节。
- **异常指标**：照抄参考实现 [`harmonization/anomaly.py`](../harmonization/anomaly.py) 的规则。前端实现必须逐字段通过 [`docs/anomaly-cases.json`](anomaly-cases.json) 的 25 个标准用例，写成前端单元测试。规则见 `data-interface.md` 第 6 节。
- **0 和空值不同**：`0` 是“没记录到火点”，空值是“没有数据”。日历上要用两种颜色。
- **单位**：数值是“VIIRS S-NPP 375 m 尺度的月火点数”，不是火灾次数，也不是燃烧面积。图例和悬停提示都要这么写。

## 4. 可信度要怎么显示

这些是数据的真实局限，网页上要诚实显示，但不用放大：

- **来源标记**：每个值都有 `source`。悬停时要显示，日历上可以用花纹或角标区分“观测”和“模型估计”：
  - 2014 年以后的训练格子是实际观测；
  - 2012 年以前是模型估计；
  - 只有 Terra 的早期月份可信度低。
- **低置信度区域**：BOAS、BONA（北方森林）、MIDE（中东），以及三个留出区（`north_australia`、`central_siberia`、`indo_gangetic`）。建议加一个“低置信度”标签。
- **区间很宽**：全球版区域区间的放大系数是 16.75。区间典型宽度是估计值的 0.5–1.6 倍，约 19% 的下限是 0。要叫“大致范围”，**不要叫“误差条”或“置信区间”**。可以默认隐藏，悬停时再显示。
- **2012-02 至 2013-12**：全球都是模型估计，这是项目规则决定的。
- **近实时**：`nrt = true` 的月份（VIIRS 2026-08 起）以后会小幅修订，可以加个小标记。

## 5. Demo 和项目页可以讲的数字

所有数字都有出处，可以直接用：

- **问题**：2012 年 VIIRS 接替 MODIS，同一片火，VIIRS 数出的火点多好几倍。直接拼接的话，历史序列在 2012 年会有一个假台阶。例子：南部非洲 2003–2011 年，直接拼接每年只有 25 万个，协调后 125 万个，和 2014–2021 年观测的 122 万个接得上（`reports/validation.md`）。
- **全球没有断层**：2013 年（模型）全球 1,600 万个火点，2014 年（观测）1,660 万个（`reports/global-review.md`）。
- **外部盲审，只考一次**：在 GitHub 云端打分，测试 1 比基线 M1s 误差低 **22%**，测试 2（没见过的地区）低 **25%**（`reports/final-test.md`）。
- **全球验证**：比基线低 **14%**，14 个大区赢了 10 个（`reports/global-scores.md`）。
- **数据规模**：
  - 5.29 亿条原始火点记录，清洗后 4.44 亿条；
  - 4 颗卫星（Terra、Aqua、S-NPP、NOAA-20），2000-11 至 2026-10，共 26 年；
  - 全球 27.8 万个格子、8,680 万个格子-月份。
- **可复现**：从零克隆，一条命令 87 分钟跑完，37 项核对逐位一致（ADR 0012）。
- **时机**：S-NPP 已停、MODIS 将退役，这份数据让火灾记录在交接时不断档。提案建议把这句放在 Demo 的前 5 秒。

**不要说的话**：“预测火灾”“准确率 XX%”（我们的指标是 MALE 误差，不是准确率）、“误差条”、“燃烧面积”。

## 6. 还有疑问时看哪里

| 问题 | 看这里 |
|---|---|
| 某个字段什么意思 | `data-interface.md` 第 2 节 |
| 数据怎么来的、局限 | [`docs/data-card.md`](data-card.md) |
| 为什么这么做 | [`docs/project-journey.md`](project-journey.md)，再看 [`docs/decisions/`](decisions/) |
| 图和成绩 | [`reports/validation.md`](../reports/validation.md)、[`reports/figures/`](../reports/figures/) |
| AI 在项目里怎么用 | [`docs/ai-usage.md`](ai-usage.md)，项目页需要 AI 使用声明时直接引用 |

数据有问题，比如数值看着不对、缺字段：**不要在前端改数**。记下区域、月份和现象，交给数据线的人处理。

## 7. 给新 agent 的开场提示词

把下面这段原样贴给做网页的 agent（Claude Code、Codex、Cursor 都可以）：

```text
你要为 NASA Space Apps 2026 的 Team Inspiratio 做“燃烧日历”网页。数据已经做完并公开发布，你只负责网页。
先读仓库 team-inspiratio/inspiratio-space-apps-2026 里的 docs/frontend-agent-brief.md（必读，5 分钟），
再按需读它指向的 docs/data-interface-global.md 和 docs/data-interface.md。不要读数据处理代码和执行计划。
规则：
1）数据从 GitHub Release global-v1 下载，不要重新生成或在前端修改数值；
2）异常指标必须通过 docs/anomaly-cases.json 的 25 个用例，写成单元测试；
3）按简报第 4 节显示来源标记和低置信度；区间叫“大致范围”，不叫误差条；
4）文案只用简报第 5 节的数字。
先给我一个页面结构和技术选型的简短方案（一页以内），我确认后再写代码。
```
