# results：冻结和盲审的凭据

> English: tamper-evident records of the freeze and the one-shot blind test. Do not edit; most of
> these files are frozen (see `config/frozen-manifest.json`).

| 文件 | 内容 |
|---|---|
| `freeze.json` 🔒 | 冻结的模型（E028）、参数、轮数、重抽种子、区间系数 |
| `submission.parquet` 🔒 | 封存的盲审答卷：冻结后、看到测试数据之前就交了 |
| `final-test/` | GitHub Actions 阅卷的原始输出：成绩、来源记录、锁住数据的 SHA256 |
| `expected/` | 复现核对用的期望哈希（`pipeline.py` 用它检查重跑结果是否逐位一致） |

可读版成绩在 [`reports/final-test.md`](../reports/final-test.md)。
