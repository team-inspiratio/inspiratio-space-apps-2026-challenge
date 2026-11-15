# 数据接口规范（数据集 v1 / S12 最终版；v0 见第 7 节）

> 给前端用。v1 在 GitHub 预发布版 `dataset-v1`，用 `uv run python -X utf8 -m harmonization.series_v1 build` 生成。v1 用选定的模型 **LightGBM E028**（S11 冻结、经外部盲审打分），字段与 v0 兼容，新增区间和近实时标记，来源名从 `m1s_*` 改成 `model_*`。这里没写到的约定，以提案“网页成果”“异常指标”“从格子到用户区域”为准。做法细节见 `docs/decisions/0009`。

## 1. 文件

| 文件 | 内容 |
|---|---|
| `frontend/<region>.json.gz` | 每个预设区域一个 gzip 压缩的 JSON（格式见第 3 节），网页直接读 |
| `dataset_v1.parquet` | 六个区全部格子 × 月份的长表（第 2 节），给分析和下载用 |
| `dataset_v1.csv.gz` | 同一张表的 CSV（gzip 压缩，UTF-8，LF 换行）：空字段 = 没有数据，数值保留 6 位有效数字，布尔值写 `True`/`False`（S14） |
| `data-card.md` | 数据说明卡（来源、处理、不确定性、验证、局限、引用；英文，附中文摘要） |
| `anomaly-cases.json` | 异常指标的标准测试用例（第 6 节），前端逐项对答案 |
| `region_totals_v1.csv` | 区域 × 月的总量、区间、来源、标记 |
| `resamples20_v1.parquet` | 前 20 次重抽的格子级估计（只存非零值；列 `lat_idx, lon_idx, month, resample, value`），给用户自圈区域算区间：每个 `resample` 分别加总，再取第 2 小和第 19 大附近的值作近似 5%/95% |
| `meta.json` | 模型、训练范围、轮数、区间是否校准 |
| `SHA256SUMS.txt` | 上面各文件的 SHA256 |

六个区域：`california`、`cordoba`、`southern_africa`（训练区），`north_australia`、`central_siberia`、`indo_gangetic`（留出区）。边界见 `config/regions.json`。

## 2. 基本单位和字段（`dataset_v1.parquet`）

- **格子**：0.25° × 0.25°。`lat_idx = floor((lat + 90) / 0.25)`、`lon_idx = floor((lon + 180) / 0.25)`，从西南角起算。格子中心纬度 = −90 + (lat_idx + 0.5) × 0.25，经度同理。
- **时间**：自然月，按 UTC 统计，`month` 写成 `YYYY-MM`，范围 2000-11 至 2026-10，共 312 个月。

| 字段 | 类型 | 单位 / 取值 | 含义 |
|---|---|---|---|
| `lat_idx`, `lon_idx` | int16 | — | 格子编号 |
| `region`, `role` | string | `train` / `holdout` | 所属区域和角色 |
| `month` | string | `YYYY-MM` | 月份 |
| `est` | float32 | 火点数 / 格子 / 月（VIIRS S-NPP 375 m 等效） | **主值**：协调后的月度火点数。估计值可以有小数 |
| `lo_90`, `hi_90` | float32 | 火点数 | 格子级稳定性区间（100 次整年重抽的 5%/95% 分位数）；只反映“换一批训练年份估计会变多少”，不是误差范围。观测月和 NOAA-20 月等于 `est` |
| `source` | category | 见第 4 节 | `est` 的来源 |
| `nrt` | bool | — | 这个值来自近实时数据（VIIRS 2026-08 起、MODIS 2026-09 起），以后标准产品发布会小幅修订 |
| `input_complete` | bool | — | 这个值所用的传感器在该月是否完整；`false` 表示有缺测天，数值可能偏低 |
| `est_m0` | float32 | 火点数 | 直接拼接（2012-02 前用 MODIS 原始数，之后用 S-NPP 观测），只用来展示“不协调会怎样”；没有观测时为空 |
| `aqua_count`, `terra_count` | float32 | 火点数（MODIS 1 km） | MODIS 原始计数；传感器没在轨或整月缺测时为空 |
| `snpp_count` | float32 | 火点数 | S-NPP 原始观测（只有训练区、2014-01 以后有）；留出区和 2012–2013 年全部为空 |

**0 和空值不一样**：`0` 表示“这个月没有记录到火点”，不等于确定没有火（云、烟都可能造成漏检）；空值表示没有数据（缺测或不在轨）。`est` 没有空值。

## 3. 前端 JSON（`frontend/<region>.json.gz`）

```json
{
  "version": "v1",
  "region": "california",
  "label": "California, USA (Mediterranean forest and shrubland)",
  "role": "train",
  "bbox": [-124.5, 32.5, -114.5, 42.0],
  "cell_deg": 0.25,
  "months": ["2000-11", "...", "2026-10"],
  "month_source": ["model_terra_bridge", "...", "snpp"],
  "month_nrt": [false, "...", true],
  "month_input_complete": [true, "...", true],
  "cells": {"lat_idx": [490, "..."], "lon_idx": [222, "..."]},
  "est": [[0.0, 1.25, "..."], "..."],
  "totals": {"est": [...], "lo_90": [...], "hi_90": [...], "est_m0": [...], "aqua_count": [...], "terra_count": [...], "snpp_count": [...]},
  "model": {"model": "LightGBM E028 ...", "training": {"months": ["2014-01", "2021-06"]}, "interval": {"calibrated": true, "...": "..."}}
}
```

- `est[i][t]` 是第 i 个格子（`cells.lat_idx[i]`, `cells.lon_idx[i]`）在第 t 个月（`months[t]`）的估计值，保留 2 位小数。
- 同一区域里，**同一个月所有格子的来源都相同**，所以来源按月给（`month_source`、`month_input_complete`）。
- `totals.*[t]`：整个区域在第 t 个月的总量；`null` 表示该月没有这类数据。
- `totals.lo_90/hi_90`：区域总量的稳定性区间（先把每次重抽加总成区域总量，再取 5%/95%）。`model.interval.calibrated = true` 时已按验证集定的系数围绕估计值放大（`docs/decisions/0008` 第 5 节），并在测试集上检验过覆盖率（`reports/final-test.md`）。

## 4. 来源标记（`source` / `month_source`）

| 值 | 含义 | 网页显示建议 |
|---|---|---|
| `snpp` | S-NPP VIIRS 观测值（训练区，2014-01 起的完整月） | 观测 |
| `noaa20_scaled` | 该月 S-NPP 缺测或部分缺测，改用 NOAA-20 整月值换算到 S-NPP 尺度（不和 S-NPP 相加） | 换算值；连续性检验还没通过人审，**先别写“连续”**（`docs/decisions/0005` 第 4 条） |
| `model_aqua` | 用 MODIS（Aqua + Terra）输入和选定模型算出的估计 | 估计值 |
| `model_terra_bridge` | Aqua 不完整、只有 Terra（2000-11 至 2002-09，以及 Aqua 缺测月）：用 Terra 造出 Aqua 输入再进模型 | 低置信度估计（验证集上误差约是有 Aqua 时的 1.6 倍） |

v1 的限制：
- 本机永远没有 2012–2013 年的 S-NPP（测试集隔离），所以训练区这两年也是 `model_aqua`（`docs/decisions/0009` 第 1 条）。
- 留出区每个月都是估计值（`model_*`），桥接比例用当地 MODIS 拟合。
- 模型的纬度输入实际起了“像哪个训练区”的作用，离训练区很远的地方要看测试 2 的成绩再决定能不能用（`reports/model-review.md` 第 5 节、`reports/final-test.md`）。
- NOAA-20 段的连续性标准还没经人确认，先别写“连续”。

## 5. 从格子到用户圈选区域

把落在区域里的格子加起来；格子只有一部分在区域内时，按重叠面积的比例分配。这里假设火点在格子里均匀分布：圈的范围小时，边界误差会比较明显。圈选范围小于一个格子时，只给近似值，并提示这个限制。

## 6. 异常指标（参考实现 `harmonization/anomaly.py`，标准测试用例 `anomaly-cases.json`）

前端照下面的规则实现同一个函数 `anomaly(series, target, as_of, baseline)`，然后把 `anomaly-cases.json` 里每个用例的 `input` 喂进去，逐个字段和 `expected` 比（数值相对误差 1e-9 以内，列表完全相同）。25 个用例：19 个人工推算的边界情况（并列、正好 90/10、参考年数 9、中位数为 0、目标月缺测、当月未结束、S-NPP 基准期等），6 个用数据集 v1 真实区域总量的例子。输出字段：`status`、`value`、`n_ref`、`ref_years`、`median`、`ratio`、`percentile`、`level`（`high`/`normal`/`low`/空）、`preliminary`、`notes`。中英文措辞也在 JSON 的 `labels`、`notes` 里。下面原有的定义不变，S14 补上了几处细节（`docs/decisions/0011`）：

- **月份结束**：截至日期（UTC，`YYYY-MM-DD`）不早于下个月 1 日，这个月才算结束。
- **并列**：数值只给到 2 位小数，所以 |x − h| ≤ 0.005 算“等于”，x < h − 0.005 算“小于”。
- **参考集**：同一日历月、2001 年至目标年前一年、有值且 `input_complete = true`；基准期选“S-NPP”时只留 `source = snpp` 的月份。只有 Terra 的月份（低置信度）也算参考。
- **状态顺序**：没有值 `no_data` → 当月未结束 `month_in_progress`（只显示截至目前的值）→ 目标月缺测 `incomplete_coverage` → 没有参考月 `no_history` → 参考年数 1–9 `insufficient_history`（给百分位、中位数、倍数，不分等级）→ `ok`。
- 中位数 = 普通中位数（偶数个时取中间两个的平均）；中位数 < 5 时不给倍数，`notes` 加 `small_median`；目标值来自近实时数据时 `preliminary = true`。

原定义：

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
| v1 | 2026-11-04 | S12：选定模型 LightGBM E028 + 稳定性区间 + 近实时标记，预发布版 `dataset-v1` |
| v1（S14 交付） | 2026-11-04 | 数据不变；加 CSV 版、数据说明卡、异常指标参考实现和标准测试用例。正式发布为 Release `v1`（S15） |
