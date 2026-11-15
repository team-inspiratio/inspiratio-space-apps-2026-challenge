# S10 AI 自动实验：program.md

> 照提案“AI 自动实验循环 / program.md 模板”写，补上本项目的具体规定（`docs/decisions/0006`）。

# 目标
降低 `evaluate.py` 输出的两窗口合并验证集 MALE（越低越好），同时 VIIRS 零检测样本的正估计比例、
1–9 个火点的误差和区域总量偏差不能变差（预注册第 4 节第 3–4 条的容差，相对 M1s λ = 20）。

# 你可以改
只有 `harmonization/harmonize.py`（`LGB` 配置、`DERIVED` 派生特征、`fit_lgb()` 及其辅助函数）。
`fit()` 拿到带 VIIRS 真实值的训练表；`predict()` 只拿到 `prepare.feature_table()`：格子编号加
`config/features.json` 的 MODIS 特征。
当前起点（E000）：LightGBM，Tweedie 目标（variance_power 1.3），对 Aqua、Terra 火点数单调递增约束，
31 个叶子、每叶至少 50 条，学习率 0.05，确定性模式，种子 42，8 线程。

# 硬性规定
- 不能修改 `prepare.py`、`evaluate.py`、`final_test.py`、配置文件和数据切分。
- 不能把年份、地区名、格子编号（`lat_idx`、`lon_idx`）或任何 VIIRS 信息当特征；派生特征只能用
  `features.json` 里的列计算。
- 必须保留对 MODIS 火点数的单调递增约束。
- 树的轮数只用训练表内部最早 12 个月（倒推方向）确定；Optuna 只在这个内部切分上调数值参数，
  不看验证窗口。
- 线程数固定为 8（结果和线程数有关）；上课时只降低优先级（`--low`）。
- 每次实验一句话假设，用 `uv run python -X utf8 -m harmonization.autoexp run --hyp "..."` 运行，
  自动记入 `harmonization/experiments.csv` 并提交到 `exp/lightgbm` 分支。
- 保留规则：通过全部护栏，并且相对当前最好的版本的改进超过 1 个标准误（块状重采样）。
- 预算：最多 150 次实验或 8 小时；连续 30 次没有保留就停。
- 只做 LightGBM 的结构性改动；数值参数交给 Optuna。不做计划外的模型（CNN、像元级、M1s 混合等）。

# 值得尝试的方向
- 零值处理：MODIS 本格和邻格都没有火点时的估计（护栏指标对此最敏感）
- FRP 分布特征：中位数、75 分位数、低于 10 MW 的占比
- 平均像元尺寸，或按像元尺寸分档的火点数
- 周围格子的 MODIS 火点数之和
- 夜间火点占比
- Tweedie 的 variance_power 在 1.1 到 1.9 之间；Poisson 目标
- 更浅的树、更大的叶子，减少过拟合
- Terra 的特征在 2020 年后不稳定（`reports/findings.md` 第 7 条），可以试着去掉

# 背景
VIIRS 像元更小、没有赤道附近的轨道缝隙、斜视时更清楚，所以数到更多火点。
差距随观测角度、纬度、火的类型而变。
