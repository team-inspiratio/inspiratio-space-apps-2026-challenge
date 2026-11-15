# 数据接口规范（草稿，数据集 v0 / 里程碑 A）

> 给前端用。数据在 GitHub 预发布版 `milestone-a`，用 `harmonization/series.py` 生成。v0 是 **M1s 保底版**：先让网页能开工，S12 会出最终版（字段不变，可能会加区间字段）。这里没写到的约定，以提案“网页成果”“异常指标”“从格子到用户区域”为准。

## 1. 文件

| 文件 | 内容 |
|---|---|
| `frontend/<region>.json.gz` | 每个预设区域一个 gzip 压缩的 JSON（格式见第 3 节），网页直接读 |
| `dataset_v0.parquet` | 六个区全部格子 × 月份的长表（第 2 节），给分析和下载用 |
| `region_totals_v0.csv` | 区域 × 月 × 来源的总量，给快速核对用 |
| `SHA256SUMS.txt` | 上面各文件的 SHA256 |

六个区域：`california`、`cordoba`、`southern_africa`（训练区），`north_australia`、`central_siberia`、`indo_gangetic`（留出区）。边界见 `config/regions.json`。

## 2. 基本单位和字段（`dataset_v0.parquet`）

- **格子**：0.25° × 0.25°。`lat_idx = floor((lat + 90) / 0.25)`、`lon_idx = floor((lon + 180) / 0.25)`，从西南角起算。格子中心纬度 = −90 + (lat_idx + 0.5) × 0.25，经度同理。
- **时间**：自然月，按 UTC 统计，`month` 写成 `YYYY-MM`，范围 2000-11 至 2026-10，共 312 个月。

| 字段 | 类型 | 单位 / 取值 | 含义 |
|---|---|---|---|
| `lat_idx`, `lon_idx` | int16 | — | 格子编号 |
| `region`, `role` | string | `train` / `holdout` | 所属区域和角色 |
| `month` | string | `YYYY-MM` | 月份 |
| `est` | float32 | 火点数 / 格子 / 月（VIIRS S-NPP 375 m 等效） | **主值**：协调后的月度火点数。估计值可以有小数 |
| `source` | category | 见第 4 节 | `est` 的来源 |
| `input_complete` | bool | — | 这个值所用的传感器在该月是否完整；`false` 表示有缺测天，数值可能偏低 |
| `est_m0` | float32 | 火点数 | 直接拼接（2012-02 前用 MODIS 原始数，之后用 S-NPP 观测），只用来展示“不协调会怎样”；没有观测时为空 |
| `aqua_count`, `terra_count` | float32 | 火点数（MODIS 1 km） | MODIS 原始计数；传感器没在轨或整月缺测时为空 |
| `snpp_count` | float32 | 火点数 | S-NPP 原始观测（只有训练区、2014-01 以后有）；留出区和 2012–2013 年全部为空 |

**0 和空值不一样**：`0` 表示“这个月没有记录到火点”，不等于确定没有火（云、烟都可能造成漏检）；空值表示没有数据（缺测或不在轨）。`est` 没有空值。

## 3. 前端 JSON（`frontend/<region>.json.gz`）

```json
{
  "version": "v0",
  "region": "california",
  "label": "California, USA (Mediterranean forest and shrubland)",
  "role": "train",
  "bbox": [-124.5, 32.5, -114.5, 42.0],
  "cell_deg": 0.25,
  "months": ["2000-11", "...", "2026-10"],
  "month_source": ["m1s_terra_bridge", "...", "snpp"],
  "month_input_complete": [true, "...", true],
  "cells": {"lat_idx": [490, "..."], "lon_idx": [222, "..."]},
  "est": [[0.0, 1.25, "..."], "..."],
  "totals": {"est": [...], "est_m0": [...], "aqua_count": [...], "terra_count": [...], "snpp_count": [...]},
  "model": {"lambda": 20.0, "m1s_fit": ["2014-01", "2021-06"], "...": "..."}
}
```

- `est[i][t]` 是第 i 个格子（`cells.lat_idx[i]`, `cells.lon_idx[i]`）在第 t 个月（`months[t]`）的估计值，保留 2 位小数。
- 同一区域里，**同一个月所有格子的来源都相同**，所以来源按月给（`month_source`、`month_input_complete`）。
- `totals.*[t]`：整个区域在第 t 个月的总量；`null` 表示该月没有这类数据。

## 4. 来源标记（`source` / `month_source`）

| 值 | 含义 | 网页显示建议 |
|---|---|---|
| `snpp` | S-NPP VIIRS 观测值（训练区，2014-01 起的完整月） | 观测 |
| `noaa20_scaled` | 该月 S-NPP 缺测或部分缺测，改用 NOAA-20 整月值换算到 S-NPP 尺度（不和 S-NPP 相加） | 换算值；连续性检验还没通过人审，**先别写“连续”**（`docs/decisions/0005` 第 4 条） |
| `m1s_aqua` | 用 Aqua MODIS 和 M1s 比例换算出的估计 | 估计值 |
| `m1s_terra_bridge` | 只有 Terra（2000-11 至 2002-06，以及 Aqua 缺测月）：Terra → Aqua 桥接，再用 M1s | 低置信度估计 |

v0 的限制：
- 本机永远没有 2012–2013 年的 S-NPP，所以训练区这两年也是 `m1s_aqua`。
- 留出区每个月都是估计值（`m1s_*`）。
- 留出区的 Terra 桥接段可能明显偏高（北澳约偏高 1.5–2 倍，见 `docs/decisions/0005` 第 6 条）。
- v0 没有不确定性区间，S12 会补上。

## 5. 从格子到用户圈选区域

把落在区域里的格子加起来；格子只有一部分在区域内时，按重叠面积的比例分配。这里假设火点在格子里均匀分布：圈的范围小时，边界误差会比较明显。圈选范围小于一个格子时，只给近似值，并提示这个限制。

## 6. 异常指标（定义，参考实现在 S14）

- **只评价已经结束的完整月份**。当月还没结束时，只显示“截至某日的累计火点数”，不下异常结论。
- **异常倍数** = 该月 `est` ÷ 历史同月中位数。
- **历史百分位**：参考集是目标年份之前、同一日历月、完整可用（`input_complete = true`）的年份，目标月本身不算在内。参考值为 x₁…xₙ、目标为 h，百分位 = 100 × [小于 h 的个数 + 0.5 × 等于 h 的个数] ÷ n，同时显示参考年数 n。
- **活动等级**：n ≥ 10 时，百分位 ≥ 90 记“偏高”，≤ 10 记“偏低”，其余记“正常”；n < 10 时不分等级，只显示数值，并注明“历史不足”。
- **中位数很小（< 5）时**：不显示倍数，只显示百分位，并注明“该月历史上通常很少记录到火点”。
- **缺测**：目标月 `input_complete = false` 时，显示已有计数和“覆盖不完整”，不分等级。
- **基准期**：默认从 2001 年起；也可以只用 S-NPP 观测月（`source = snpp`）作为基准期。页面上同时显示基准期、数据版本、参考年数和截至日期。
- **措辞**：一律写“火点活动偏高 / 正常 / 偏低（VIIRS 等效估计）”，不写火灾次数、烧毁面积或灾害严重程度。

## 7. 版本

| 版本 | 时间 | 说明 |
|---|---|---|
| v0 | 2026-11-03 | 里程碑 A：M1s 保底版，预发布版 `milestone-a` |
