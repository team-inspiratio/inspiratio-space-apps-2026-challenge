# docs：文档地图

> English: human-facing docs are in the first table; everything below it is a process record kept for
> audit and reproducibility. You rarely need the second half.

## 给人看的（先看这些）

| 文件 | 给谁 | 内容 |
|---|---|---|
| [`proposal.md`](proposal.md) | 所有人 | 完整方案：问题、做法、网页、验证、执行手册 |
| [`project-journey.md`](project-journey.md) | 写提案、做 Demo、做 v2 的人 | 两天的经过、结果、每个关键决定的理由、弱点、写论文还缺什么 |
| [`data-card.md`](data-card.md) | 数据使用者 | 数据说明卡：来源、处理、不确定性、局限、引用（英文，附中文摘要） |
| [`data-interface.md`](data-interface.md) | 前端 | 字段、JSON 格式、来源标记、用户圈选区域、异常指标（示范区版 `v1`） |
| [`data-interface-global.md`](data-interface-global.md) | 前端 | 全球版 `global-v1` 和 `v1` 不同的地方 |
| [`frontend-agent-brief.md`](frontend-agent-brief.md) | 做网页的 AI agent | 一页简报和开场提示词 |
| [`ai-usage.md`](ai-usage.md) | 评委、读者 | AI 在项目里用在哪、人做了哪些决定 |
| [`anomaly-cases.json`](anomaly-cases.json) | 前端 | 异常指标的 25 个标准测试用例 |

## 过程记录（审计和复现用，一般不用看）

| 文件或目录 | 内容 |
|---|---|
| [`decisions/`](decisions/) | 决定记录（ADR 0001–0013）：每个计划没写到的技术决定，含背景、选项、理由 |
| [`preregistration.md`](preregistration.md) | 预注册：看到任何结果之前就定好的评分、数据切分和选模规则（冻结） |
| [`execution-plan.md`](execution-plan.md) | 数据线的执行计划，AI 会话的唯一依据 |
| [`sessions/`](sessions/) | 任务卡：每个 AI 会话做哪几个阶段 |
| `data-manifest.csv`、`ingest-ledger.csv`、`api-ledger.csv` | 下载和导入的清单，含文件哈希 |
| `crosscheck-api-vs-yearly.csv` | FIRMS API 和年度包的逐行抽查 |
| `cleaning-counts.csv`、`removed-sample.csv` | 清洗规则各删了多少条，以及删除样本抽查 |
| `firms-missing-data.csv`、`month-status.csv` | FIRMS 缺测清单，以及每个传感器每月是否完整 |

这些文件的路径被代码和冻结文件引用，所以没有挪进子目录。
