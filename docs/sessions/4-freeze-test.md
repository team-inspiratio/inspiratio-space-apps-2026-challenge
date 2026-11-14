# 任务卡 4-freeze-test：冻结、外部盲审、最终数据集（S11–S12）

> 开始前先按 [`AGENTS.md`](../../AGENTS.md) 的“开工流程”读进度、认领、预检。

## 前置条件

- S10 已完成：`experiments.csv` 和审核记录齐全。
- `grader.yml` 已在 S01 提交并冻结；prepare、evaluate、final_test 已在 S07 冻结。
- `results/final-test/` **不存在**（存在说明已经考过，只能考一次，立刻停下告诉人）。

## 需要人准备

- **人本人决定**是否推送 `final-test` 标签。AI 只准备好一切，然后停下，给出要运行的命令，等人确认。
- `gh auth login --web` 已完成（查看 Actions 运行结果、发版本）。

## 只读计划的这几节

[`docs/execution-plan.md`](../execution-plan.md) 的：第 2 节（生成序列需要的方法）、第 3 节第 5、7 条、第 4 节（外部盲审）、第 6 节表格中 S11–S12 这两行；以及 [`docs/preregistration.md`](../preregistration.md)。细节可查 proposal 的“B5”“B6”“生成最终序列”。

## 要做的阶段

### S11 冻结与盲审

- 按预注册的选定规则（比 M1s 至少好 10%、两个窗口都不明显退步、护栏指标在容差内、通过泄漏审查、改进超过 1 个标准误）决定用 LightGBM 还是 M1s，写 `docs/decisions/` 决策记录。
- 写冻结清单（特征、参数、树轮数、代码版本），冻结 `harmonize.py` 和 `config/features.json`。
- 用训练区 2014-01 至 2021-06 重训冻结模型，**只用 MODIS 输入**生成测试期预测 `submission.parquet`（测试 1 年份 + 留出区），把它的哈希写进冻结清单并 commit、push（先封存答卷）。M1s 的答卷一起封存作为对照。
- 停下，请人推送标签：`git tag final-test && git push origin final-test`。GitHub Actions 自己下载锁住的数据、打分、把成绩提交回仓库。
- 成绩回来后 `git pull`，如实写进 `reports/final-test.md`，不管好坏。

### S12 最终数据集

- 用训练区 2012-02 至 2021-06 全部重叠数据重训上线版本（留出区仍隔离）。评估版和上线版各自记录代码、特征、轮数、训练范围。
- 年份块重采样 100 次得到稳定性区间（先加总成区域或月份总量再取 5%/95% 分位）；在测试集上报告实际覆盖率（计划第 3 节第 5 条）。
- 生成 2000-11 至 2026-10 的序列，打来源标记（VIIRS 实测、MODIS 估计、Terra 低置信度、NOAA-20 接续、近实时、缺测）。
- 验收抽查：S-NPP 段（2012-02 至 2026-10 完整月）与同一质量控制下的观测计数完全一致。

## 验收标准

- 成绩由 CI 提交回仓库；`reports/final-test.md` 如实记录。
- 最终数据集通过“S-NPP 段与观测完全一致”的检查；处理后的数据上传为 Release 附件并记录 SHA256。

## 禁止事项

- AI 自己推送 `final-test` 标签；看了测试成绩再改模型重考；在多个模型之间用测试成绩挑选。
- 修改 `grader.yml` 或任何冻结文件；本机下载锁住的数据。

## 结束时更新

- `PROGRESS.md` 阶段表 S11–S12（选定模型、测试 MALE、覆盖率）；状态块改为 `current_card: docs/sessions/5-report.md`、`status: ready`、清空认领、`last_pushed_stage: S12`。README 进度框同步。CI 绿。

## 下一张卡

[`5-report.md`](5-report.md)
