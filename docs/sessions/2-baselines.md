# 任务卡 2-baselines：判卷机器、保底模型、里程碑 A（S07–S09）

> 开始前先按 [`AGENTS.md`](../../AGENTS.md) 的“开工流程”读进度、认领、预检。

## 前置条件

- S01–S06 已完成，`PROGRESS.md` 记录了数据 Release（例如 `data-v0`）和 SHA256。
- 本机没有数据时：用 `gh release download data-v0` 下载到 `INSPIRATIO_DATA_DIR`，核对 SHA256；或者用 pipeline 从头重建（慢）。
- 普通笔记本即可（不需要 50 GB）。

## 需要人准备

- `gh auth login --web` 已完成（下载 Release 数据、发预发布版要用）。
- S07 冻结 prepare、evaluate 前，请人过目一遍（计划要求“负责人确认后冻结”）。

## 只读计划的这几节

[`docs/execution-plan.md`](../execution-plan.md) 的：第 2 节（方法、切分）、第 3 节（验证）、第 4 节（测试集隔离）、第 6 节表格中 S07–S09 这几行、第 10 节；以及 [`docs/preregistration.md`](../preregistration.md)。实现细节可查 proposal 的“验证体系”“B1”“B2”“生成最终序列”“异常指标”“C1”。

## 要做的阶段

### S07 判卷机器

- `harmonization/prepare.py`：按冻结的 settings 切出主验证窗口和辅助倒推窗口；读冻结的随机矩形。
- `harmonization/evaluate.py`：两个窗口上打分，输出 MALE（主分数，按区和完整年份求均值再等权汇总）和辅助指标（零火点正估计比例、1–9 个火点误差、总量偏差、季节相关）。调 `predict()` 时**只传 MODIS 特征**，不传 VIIRS 列和年份列（写 pytest 证明）。
- `harmonization/final_test.py`：给 `grader.yml` 用，S01 定好的调用约定。本机不运行它。
- 用“永远预测 0”和“直接用 MODIS 数”两个假方法检查分数合理地差；连跑两次逐位一致。
- 人过目后冻结：`uv run python tools/guardrails.py freeze harmonization/prepare.py harmonization/evaluate.py harmonization/final_test.py`。

### S08 保底模型

- `harmonization/harmonize.py`（唯一允许 AI 实验修改的文件）里实现 M0、M1s（λ ∈ {0, 5, 20, 50, 100} 用验证集选）、QM（分位数映射）。
- Terra→Aqua 桥接比例；用 2018–2026-10 的重叠期做 NOAA-20→S-NPP 接续检验（拟合早段、检验晚段，按昼夜检查）。
- 分数表 v1：`reports/scores-v1.md`。

### S09 ★里程碑 A

- 用 M1s 生成数据集 v0（2000-11 至 2026-10，带来源标记）。
- 导出前端文件（每区域一个压缩 JSON），写数据接口规范草稿 `docs/data-interface.md`（字段、单位、来源标记、缺测表示、异常指标的定义）。
- 发 GitHub 预发布版（例如 `milestone-a`），附数据包和 SHA256。通知前端可以开工（在 PR 和 PROGRESS 里写明）。

## 验收标准

- prepare、evaluate、final_test 已冻结，CI 的冻结哈希检查通过；假方法检查和可重复性测试通过。
- 分数表 v1 含 M0、M1s、QM 在两个验证窗口上的全部指标。
- 预发布版存在，前端拿到文件和接口规范就能开工。

## 禁止事项

- 用测试集或留出区数据做任何事；让 `predict()` 能拿到 VIIRS 列或年份列。
- 冻结后再改 prepare、evaluate、final_test。
- 开始 LightGBM（属于会话 3）。

## 结束时更新

- `PROGRESS.md` 阶段表 S07–S09；状态块改为 `current_card: docs/sessions/3-model.md`、`status: ready`、清空认领、`last_pushed_stage: S09`。README 进度框同步。CI 绿。

## 下一张卡

[`3-model.md`](3-model.md)
