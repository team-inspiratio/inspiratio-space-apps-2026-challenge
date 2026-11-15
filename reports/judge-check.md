# 判卷机器检查（S07）

由 `uv run python -m harmonization.judge_check` 生成。两个假方法在两个验证窗口上各跑两次；“永远预测 0”应明显差于“直接用 MODIS 数”，同一方法两次结果的 SHA256 必须相同。

| 方法 | 窗口 | male | male_all | n_primary | excluded_share | zero_ge1 | low_mae |
|---|---|---:|---:|---:|---:|---:|---:|
| always 0 | main | 5.7628 | 4.9176 | 11727 | 0.0000 | 0.0000 | 4.1092 |
| always 0 | aux | 6.0419 | 5.1757 | 11407 | 0.0417 | 0.0000 | 3.8688 |
| always 0 | 两窗口合并 MALE | 5.9023 |
| MODIS count as is (= M0) | main | 1.7986 | 1.5977 | 11727 | 0.0000 | 0.0562 | 3.4664 |
| MODIS count as is (= M0) | aux | 1.7906 | 1.5904 | 11407 | 0.0417 | 0.0646 | 3.2742 |
| MODIS count as is (= M0) | 两窗口合并 MALE | 1.7946 |

两次运行的 SHA256：

- always 0：`b17bb605fe308be4…` / `b17bb605fe308be4…`
- MODIS count as is (= M0)：`15dfd1ce8f1ab5c8…` / `15dfd1ce8f1ab5c8…`

结论：可重复性 通过。
