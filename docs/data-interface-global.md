# 数据接口规范：全球版（global-v1，阶段 G）

> 给前端用。全球版在 GitHub Release `global-v1`（CC BY 4.0），用 `uv run python -X utf8 pipeline.py global` 生成（各步见 `harmonization/series_global.py`）。字段、JSON 格式、来源标记、异常指标的规则**和 v1 完全相同**（`docs/data-interface.md` 第 2–6 节），本文只写不同的地方。做法细节见 `docs/decisions/0013`。

## 1. 和 v1 有什么不同

- **范围**：全球 278,192 个 0.25° 格子 × 312 个月（2000-11 至 2026-10），共 8,680 万格子-月份。纳入规则：GFED 陆地格子、有过任何火点的格子、评分矩形和 v1 六个框里的格子（`config/regions-global.json`）。范围外的格子（主要是远海）一律当作 0。
- **区域**：按 GFED4.1s 的 14 个基础分区（`region` 字段：`BONA`、`TENA`、`CEAM`、`NHSA`、`SHSA`、`EURO`、`MIDE`、`NHAF`、`SHAF`、`BOAS`、`CEAS`、`SEAS`、`EQAS`、`AUST`）。三个留出区（`north_australia`、`central_siberia`、`indo_gangetic`）**单列**，不算进所在的 GFED 区。新增字段 `gfed_region`：每个格子所在的 GFED 区，包括留出区格子。
- **模型**：还是 E028，参数和树的轮数都是冻结的，但用全球训练格子（2014-01 至 2021-06，不含留出区）重新训练。所以它**不是**考过测试的那个模型。S11 的测试成绩属于只用 3 个示范区训练的版本，全球版只有验证窗口的分数（`reports/global-scores.md`）。
- **区间**：用 S11 封存整年重抽的**前 50 次**（v1 用 100 次）。为了省运行时间，这是近似，分位数会稍微抖一些（ADR 0013 第 5 条补充）。区域总量区间的放大系数在全球验证窗口上用同一公式重新求，同样各用 50 次：
  - 结果是 **16.75**（v1 是 5.37）。
  - 不放大时，验证窗口上区 × 月真值落在区间里的只有 14%；放大后是 90%。
  - 所以全球版的区域区间比 v1 宽得多。模型年份区 × 月区间的宽度中位数是估计值的 0.5–1.6 倍，北方森林、中东、欧洲和留出区最宽。约 19% 的模型区 × 月区间下限为 0。
  - 数值见 `meta.json` 的 `interval`。
- **来源**：所有非留出区格子都是“训练格子”，2014-01 以后的完整月份都是 S-NPP 观测（`source = snpp`）。留出区每个月都是模型估计。

## 2. 文件

| 文件 | 内容 |
|---|---|
| `frontend/index.json` | 前端文件清单：每个区或框的 `name`、`label`、`role`、`bbox`、`kind`（`region` / `box`）、`file`、`cells` |
| `frontend/<名字>.json.gz` | 每个区一个，格式和 v1 第 3 节完全相同。14 个 GFED 区和 3 个留出区（`kind = region`）；另有 v1 的 3 个训练框 `california`、`cordoba`、`southern_africa`（`kind = box`，从全球结果里截出来，数值来自全球模型，和 v1 不同）。GFED 区的 `bbox` 是格子的外包矩形，区域实际形状以 `cells` 为准 |
| `dataset_global-v1.parquet` | 全部格子 × 月份的长表：v1 第 2 节的字段，加 `gfed_region` |
| `dataset_global-v1.csv.gz` | 同一张表的 CSV（规则同 v1） |
| `region_totals_global-v1.csv` | 区 × 月的总量、区间、来源、标记（14 个 GFED 区 + 3 个留出区） |
| `box_totals_global-v1.csv` | v1 六个框 × 月的总量和区间（用全球模型算） |
| `resamples20_global-v1.parquet` | 前 20 次重抽的格子级非零估计（列同 v1），给用户自圈区域近似区间 |
| `meta.json` | 模型、训练范围、轮数、区间系数、验收结果 |
| `data-interface-global.md`、`data-card.md`、`anomaly-cases.json` | 本文、数据说明卡、异常指标测试用例（和 v1 相同） |
| `SHA256SUMS.txt` | 各文件的 SHA256 |

大小：Parquet 约 201 MB，CSV.gz 约 398 MB，`resamples20` 约 663 MB，前端 JSON 合计约 32 MB（压缩后）。

## 3. 前端怎么用

- 先读 `frontend/index.json` 列出可选区域，再按需加载单个区的 `.json.gz`。每个文件压缩后 0.1–5 MB，解压后最大约 57 MB（BOAS，44,958 个格子）。建议按需加载，不要一次全读。
- 世界地图上的总览可以用 `region_totals_global-v1.csv`（区 × 月，很小）。
- 异常指标的规则和测试用例不变（v1 第 6 节）。

## 4. 可信度（网页上要标）

- **全球验证分数**（`reports/global-scores.md`，两个验证窗口平均的 MALE，越低越好）：
  - 全部评分矩形：全球 E028 0.534，M1s 0.619。
  - 有 4 个区 M1s 更好：CEAM、EQAS、NHSA、SHSA。
  - 北方森林最差：BOAS 约 1.03，BONA 约 0.65。和测试 2 一致（中西伯利亚 MALE 1.14）。
  - 建议网页对 BOAS、BONA、MIDE 和留出区标“低置信度”。
- **2012-02 至 2013-12**：全球也是模型估计（本机永远没有这两年的 S-NPP，红线 1）。
- **只有 Terra 的月份**（`model_terra_bridge`）照旧是低置信度。
- 估计值只表示“VIIRS S-NPP 尺度的火点数”，不是火灾次数或燃烧面积。
