# 任务卡 3-model：LightGBM 和 AI 自动实验（S10）

> 开始前先按 [`AGENTS.md`](../../AGENTS.md) 的“开工流程”读进度、认领、预检。

## 前置条件

- S07–S09 已完成：判卷机器已冻结，保底模型分数表 v1 已出，里程碑 A 预发布版存在。
- 本机没有数据时：从 `PROGRESS.md` 记录的 Release 下载并核对 SHA256。
- CPU 满载数小时、内存 10–20 GB；不需要 GPU。

## 需要人准备

- 确认可以连续跑最多 8 小时（上课时说“上课了”，后台降到低优先级、最多 8 个线程；说“下课了”恢复全速；说“暂停”就在当前实验跑完后停）。
- 审核子代理的结论请人过目。

## 只读计划的这几节

[`docs/execution-plan.md`](../execution-plan.md) 的：第 2 节（模型、特征）、第 3 节第 7 条（选定规则）、第 5 节（AI 自动实验）、第 6 节表格中 S10 这一行；以及 [`docs/preregistration.md`](../preregistration.md)。实验框架和 `program.md` 模板见 proposal 的“AI 自动实验循环”和“B4”。

## 要做的阶段

### S10 LightGBM 和 AI 实验

- 手写初版（在 `harmonization/harmonize.py`）：Tweedie 目标（variance_power 从 1.3 起）或 Poisson；对 MODIS 计数加单调递增约束；15–31 个叶子、每叶至少 50 条；学习率 0.05；确定性模式、固定种子。特征列表写进 `config/features.json`（CI 会查禁用特征）。
- 写 `harmonization/program.md`（照 proposal 模板），跑实验循环：**只能改 `harmonize.py`**；LLM 只做结构性改动，数值调参交给 Optuna；每次实验一句话假设，记入 `harmonization/experiments.csv`；结果好就保留并 commit 到独立分支（例如 `exp/lightgbm`），定期 push。
- 预算：最多 150 次实验或 8 小时，连续 30 次没有提升就停；改进要超过 1 个标准误才算数。
- 结束后开一个**全新上下文的审核子代理**审查前 3 名：查泄漏、删减特征实验、预测关系图、辅助窗口是否稳定。审核记录写进 `reports/model-review.md`。

## 验收标准

- `experiments.csv` 完整；审核记录完成；前 3 名的验证分数与 M1s、QM 并列、带“年份 × 区域”块状重采样 95% 区间。

## 禁止事项

- 改 `harmonize.py` 以外的任何评估相关文件；用年份、地区名、VIIRS 信息做特征。
- 看测试集或留出区数据；推送 `final-test` 标签（属于会话 4，由人决定）。
- 做计划之外的模型（CNN、像元级等）；M2、M5 只在 S15 之后、还有额度时做。

## 结束时更新

- `PROGRESS.md` 阶段表 S10（实验次数、最佳验证 MALE、相对 M1s 的改进）；状态块改为 `current_card: docs/sessions/4-freeze-test.md`、`status: ready`、清空认领、`last_pushed_stage: S10`，`needs_human` 加上“会话 4 需要人决定推送 final-test 标签”。README 进度框同步。CI 绿。

## 下一张卡

[`4-freeze-test.md`](4-freeze-test.md)
