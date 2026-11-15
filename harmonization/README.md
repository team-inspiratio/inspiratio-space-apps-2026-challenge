# harmonization：代码地图

> English: the pipeline code, grouped by stage. To rebuild everything, run `uv run python -X utf8
> pipeline.py all --from-release` from the repo root; you rarely need to call a module directly.
> Files marked 🔒 are frozen (listed in `config/frozen-manifest.json`); only a human may change them.

数据从左到右流动：**下载 → 导入 → 清洗 → 网格化 → 基线 → 模型 → 冻结与盲审 → 数据集 → 报告**。根目录的 [`pipeline.py`](../pipeline.py) 按顺序调用这些模块并核对结果。

| 阶段 | 文件 | 做什么 |
|---|---|---|
| 共用 | `config.py` | 路径和设置；密钥只从 `.env` 读，不打印 |
| S02 下载 | `download.py`、`crosscheck.py` | FIRMS 年度包和 API、缺测清单、GFED；API 与年度包逐行抽查 |
| S03 导入 | `ingest.py` | CSV 流式转成 Parquet；**留出区的 VIIRS 在这里直接丢弃** |
| S04 清洗 | `clean.py` | 按 `config/settings.yaml` 的规则清洗 |
| S05 网格化 | `grid.py` | 0.25° 格子 × 自然月 × 传感器计数，MODIS 特征 |
| S06 体检 | `explore.py` | 数据体检的 4 张图 |
| S07 判卷机器 | `prepare.py` 🔒、`evaluate.py` 🔒、`final_test.py` 🔒、`judge_check.py` | 切验证窗口、打分、一次性盲审（只在 GitHub Actions 上跑） |
| S08 基线 | `baselines.py` | M0、M1s、QM 和桥接、接续 |
| S10 模型 | `harmonize.py` 🔒、`autoexp.py`、`program.md`、`experiments.csv`、`s10_scores.py`、`model_review.py` | 所有方法的实现；AI 自动实验循环和规则；37 轮实验记录；成绩表；前 3 名的独立审核 |
| S11 冻结 | `freeze.py` 🔒 | 冻结选定模型（E028），封存盲审答卷 |
| S09、S12 数据集 | `series.py`（v0）、`series_v1.py`（v1） | 生成最终月度序列、区间和前端文件 |
| S13 报告 | `validation.py` | 验证报告的数字和 6 张核心图 |
| S14 网页 | `anomaly.py` | 异常指标的参考实现，前端照它做 |
| G 全球 | `global_grid.py`、`series_global.py` | 全球格子和全球重跑 |

每次实验的完整代码在 `exp/lightgbm` 分支上，`experiments.csv` 是全部实验的记录。
