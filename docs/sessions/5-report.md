# 任务卡 5-report：验证报告、交付、里程碑 B（S13–S15）

> 开始前先按 [`AGENTS.md`](../../AGENTS.md) 的“开工流程”读进度、认领、预检。

## 前置条件

- S11–S12 已完成：盲审成绩已由 CI 提交回仓库，最终数据集已作为 Release 附件发布。
- 本机没有数据时：从 `PROGRESS.md` 记录的 Release 下载并核对 SHA256。

## 需要人准备

- 验证报告和数据说明卡请人通读一遍。
- S15 合并 main 前请人确认（仓库约定：改动走 PR，不直接推 main）。

## 只读计划的这几节

[`docs/execution-plan.md`](../execution-plan.md) 的：第 1 节（论文标准）、第 3 节（验证 1–7）、第 6 节表格中 S13–S15 这几行、第 8 节（工程验证）、第 10 节。细节可查 proposal 的“D1”“D2”“D3”“异常指标”。

## 要做的阶段

### S13 验证报告（D1）

- 第 3 节的 1–7 全部完成：MALE 主指标和辅助指标；LightGBM 与 M1s、QM 分数差的块状重采样 95% 区间（不报 p 值）；按用途验证（偏高/正常/偏低的 Cohen's κ）；GFED 独立参照的合理性检查；不确定性覆盖率（必要时用验证集残差校准）；年代偏移调查；选定规则的执行记录。
- 6 张核心图，每张能单独讲清一件事；写局限性。报告放 `reports/validation.md`。

### S14 交付

- 数据集（CSV 和 Parquet）、数据说明卡（ESSD 风格：来源、处理、不确定性、局限）、AI 使用说明、异常指标参考实现和标准测试用例（给前端逐项对答案）、更新 `HANDOFF.md`。

### S15 ★里程碑 B

- 在干净环境里一条命令复现（例如 `uv run python pipeline.py all`），结果与成绩表一致。
- 发 Release v1；请人确认后把 `feat/data-harmonization` squash-merge 进 main。

## 验收标准

- 每张图都能单独讲清一件事；前端能用标准测试用例逐项对答案；干净环境复现结果与成绩表一致。

## 禁止事项

- 为了好看改动已报告的测试成绩；把稳定性区间说成“真实值 90% 落在其中”。
- 未经人确认合并 main。

## 结束时更新

- `PROGRESS.md` 阶段表 S13–S15；状态块：如果还有额度且人同意，改为 `current_card: docs/sessions/G-global.md`、`status: ready`；否则 `status: done`。README 进度框同步。CI 绿。

## 下一张卡

[`G-global.md`](G-global.md)（计划内，2026-11-03 用户已同意扩展到全球）
