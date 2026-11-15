# 分数表 S10：LightGBM 前 3 名与 M1s、QM

由 `uv run python -X utf8 -m harmonization.s10_scores` 生成，打分用冻结的判卷代码。前 3 名 = `harmonization/experiments.csv` 中通过全部护栏（eligible = yes）的实验里（被 30 次 Optuna 重跑取代的原始行不算，ADR 0007 第 5 条），两窗口合并验证 MALE 最低的三个；每个都从 `exp/lightgbm` 分支上的原样源码重新跑一遍。差 = 该方法 MALE − 对照 MALE（负数表示 LightGBM 更好），“年份 × 区域”块状重采样 2000 次，两窗口等权，格式为 差 ± 标准误 [95% 区间]。不报告 p 值。

## 1. 验证分数

| 方法 | 合并 MALE | main | aux | 零火点 Ĥ≥1 main/aux | 零火点 Ĥ≥5 main/aux | 1–9 火点 MAE main/aux | 总量偏差 main/aux | 对 M1s 的差 | 对 QM 的差 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M1s λ=20 | 0.3766 | 0.3933 | 0.3600 | 0.056/0.065 | 0.052/0.065 | 6.72/7.88 | 0.030/0.112 | — | — |
| QM | 0.4635 | 0.4884 | 0.4386 | 0.056/0.065 | 0.056/0.065 | 5.73/6.17 | 0.181/0.176 | — | — |
| LightGBM E028 | 0.2947 | 0.3003 | 0.2891 | 0.096/0.079 | 0.029/0.037 | 4.20/5.70 | 0.053/0.061 | -0.0820 ± 0.0155 [-0.1127, -0.0531] | -0.1688 ± 0.0137 [-0.1966, -0.1427] |
| LightGBM E018 | 0.2950 | 0.3021 | 0.2878 | 0.099/0.097 | 0.029/0.041 | 3.99/6.10 | 0.061/0.072 | -0.0817 ± 0.0151 [-0.1119, -0.0530] | -0.1685 ± 0.0130 [-0.1945, -0.1421] |
| LightGBM E032 | 0.2954 | 0.3020 | 0.2888 | 0.101/0.099 | 0.032/0.047 | 4.35/5.98 | 0.046/0.076 | -0.0812 ± 0.0149 [-0.1103, -0.0536] | -0.1681 ± 0.0133 [-0.1947, -0.1429] |

## 2. 各区 MALE

| 方法 | 窗口 | california | cordoba | southern_africa |
|---|---|---:|---:|---:|
| M1s λ=20 | main | 0.4431 | 0.4304 | 0.3063 |
| M1s λ=20 | aux | 0.4311 | 0.3686 | 0.2804 |
| QM | main | 0.5500 | 0.5081 | 0.4069 |
| QM | aux | 0.4899 | 0.4634 | 0.3625 |
| LightGBM E028 | main | 0.3099 | 0.3183 | 0.2726 |
| LightGBM E028 | aux | 0.2810 | 0.3160 | 0.2701 |
| LightGBM E018 | main | 0.3241 | 0.3102 | 0.2720 |
| LightGBM E018 | aux | 0.2767 | 0.3236 | 0.2633 |
| LightGBM E032 | main | 0.3083 | 0.3220 | 0.2757 |
| LightGBM E032 | aux | 0.2862 | 0.3196 | 0.2607 |

## 3. 选定规则初查（预注册第 4 节第 1–4 条，只看验证集；第 5 条见 `reports/model-review.md`，最终由 S11 决定）

| 实验 | 重跑一致 | ① 至少好 10% | ② 改进 > 1 个标准误 | ③④ 护栏 | 不通过的项 |
|---|---|---|---|---|---|
| E028 | 是 | 是 | 是 | 是 | — |
| E018 | 是 | 是 | 是 | 是 | — |
| E032 | 是 | 是 | 是 | 是 | — |

前 3 名的假设：

- **E028**：Two-stage (E016 setup) without the no-detection flags: they duplicate count == 0 and only add split candidates
- **E018**：Two-stage with summed MODIS count and log Aqua count as extra monotone inputs for both stages
- **E032**：Two-stage (E016 setup) without the fire-day counts: monthly counts may already carry the persistence information
