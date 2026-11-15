# AI usage statement / AI 使用说明

> Scope: the data-analysis and algorithm work in this repository (branch `feat/data-harmonization`:
> download, cleaning, gridding, models, validation, dataset). The web page, proposal page and demo
> are made by teammates and described separately. NASA Space Apps 2026 asks every team to say how
> AI tools (called "SI" in this year's rules) were used. 中文版在后半部分。

## 1. Tools

| Tool | Used for |
|---|---|
| Claude Code (Anthropic), model Claude Opus 5.5 | Writing and running all code in this repository, running the experiment loop, writing reports and documents. Every commit made with it carries a `Co-Authored-By: Claude` line, so the git history shows exactly which changes were AI-assisted. |
| Fresh-context Claude sub-agent | Independent review of the top 3 models before the final choice (leakage, feature ablation, prediction plots): `reports/model-review.md`. |
| GitHub Actions | Not AI: runs the guardrails on every push and the one-time blind grader. |

## 2. What the AI did

- Wrote the pipeline: download (FIRMS archive and API, GFED), import, cleaning, gridding, the judge (`prepare.py`, `evaluate.py`, `final_test.py`), baselines, LightGBM, freezing, the final series, this validation report and the delivery files. About 5,000 lines of Python plus tests.
- Ran the **AI experiment loop** (plan section 5, `harmonization/program.md`): 37 experiments (E000-E036) on LightGBM, each with a one-sentence hypothesis, scored only on the two validation windows by the frozen judge, all logged in `harmonization/experiments.csv`, with each variant's code kept on branch `exp/lightgbm`. Methods compared in total: direct splice (M0), simple ratio (M1s, 5 shrinkage values), quantile mapping (QM), and the 37 LightGBM variants. The two-stage design (classifier, then count model) that won came out of this loop.
- Wrote every figure, report and decision record, including the ones that report the model's weaknesses.

## 3. What people did

- Approved the execution plan and the scope (including extending to a global run later).
- Chose the three holdout regions on geography and ecology alone (`docs/decisions/0001`).
- Reviewed the judge code before it was frozen (`docs/decisions/0004`).
- Decided to cut the experiment budget for time reasons (`docs/decisions/0007`, quoted).
- Pushed the `final-test` tag that starts the one-time blind test. The AI is not allowed to push it.
- Confirm or overrule every open decision in `docs/decisions/` (marked "待人确认", awaiting confirmation, in `PROGRESS.md`), and approve merging into `main` and the public release.

## 4. How we kept the AI honest

The main risk with an AI that tries many models is that it fits the test, on purpose or by chance. The safeguards are built into the repository, not left to good intentions:

1. **Pre-registration before any model**: metrics, data splits, the selection rule and its thresholds were written and frozen first (`docs/preregistration.md`, commit `7d1aa0c`).
2. **The test answers never reached the AI's machine**: 2012-2013 S-NPP data and all VIIRS data of the holdout regions are blocked at download and import. Only the GitHub Actions grader downloads them, and it runs once (`.github/workflows/grader.yml`).
3. **Three layers of guardrails** (`tools/guardrails.py`): a Claude Code hook that blocks forbidden downloads and edits of frozen files before they happen, a pre-commit check, and CI on every push. Forbidden model inputs (year, region name, any VIIRS information) are checked by CI.
4. **Frozen files**: the judge, the settings, the regions, the selected model and the sealed submission are hashed in `config/frozen-manifest.json`; only a person can unfreeze them.
5. **Selection on validation only**, with a rule fixed in advance (≥ 10% better than the simple ratio, more than one standard error, no window or region worse, guardrail metrics in tolerance, leakage review).
6. **Results reported as they came out**: the blind test showed the model is much weaker in unseen regions; this is reported in full (`reports/final-test.md`, `reports/validation.md`), and the model was not changed afterwards.

## 5. Limits of this statement

- People reviewed the plan, the judge, the decisions and the reports; most of the remaining code was checked by tests, CI and the independent AI review rather than read line by line by a person.
- The experiment loop was stopped early for time (37 experiments instead of a budget of up to 150), as recorded in `docs/decisions/0007`.

---

## 中文版

**范围**：本仓库数据分析和算法这条线（下载、清洗、网格化、模型、验证、数据集）。网页、项目页和 Demo 由队友负责，另行说明。

**工具**：Claude Code（Anthropic，模型 Claude Opus 5.5）写并运行了本仓库全部代码、跑实验循环、写报告和文档。用它做的每个提交都带 `Co-Authored-By: Claude`，从 git 历史就能看出哪些改动有 AI 参与。最终选模型前，由全新上下文的 Claude 子代理独立审核前 3 名（`reports/model-review.md`）。GitHub Actions 负责每次 push 的护栏检查和一次性外部阅卷，它不是 AI。

**AI 做了什么**：
- 写完整条流程：下载、导入、清洗、网格化、判卷机器、保底模型、LightGBM、冻结、最终序列、验证报告和交付文件，约 5000 行 Python 加测试。
- 跑 AI 实验循环：LightGBM 共 37 次实验（E000–E036），每次一句假设，只用冻结的判卷代码在两个验证窗口上打分，全部记在 `harmonization/experiments.csv`。一共比较了直接拼接（M0）、简单比例（M1s，5 个收缩值）、分位数映射（QM）和 37 个 LightGBM 变体。最终胜出的“两段式”设计就是在这个循环里找到的。
- 写全部图表、报告和决定记录，包括如实报告模型弱点的部分。

**人做了什么**：批准执行计划和范围；只按地理和生态选定 3 个留出区（ADR 0001）；冻结前审看判卷代码（ADR 0004）；出于时间考虑决定缩减实验预算（ADR 0007，有原话）；推送启动一次性盲审的 `final-test` 标签（AI 不允许推）；确认或推翻 `docs/decisions/` 里每一条待定决定；批准合并 main 和公开发布。

**怎么防止 AI 刷分**：
1. 动手前先预注册并冻结指标、切分、选定规则和门槛。
2. 测试答案从来没到过 AI 用的机器：2012–2013 年 S-NPP 和留出区的 VIIRS 在下载和导入时就被拦截，只有 GitHub 阅卷工作流能下载，而且只运行一次。
3. 三层护栏：Claude Code 钩子（事前拦截）、pre-commit、CI（每次 push）。禁用特征（年份、地区名、任何 VIIRS 信息）由 CI 检查。
4. 冻结文件（判卷代码、配置、区域、选定模型、封存的答卷）记了哈希，只有人能解冻。
5. 只在验证集上按事先定好的规则选模型。
6. 成绩出来就如实报告：盲审显示模型在没见过的地区明显变差，全文报告，事后没有改模型。

**这份说明的局限**：人审看了计划、判卷代码、各项决定和报告；其余大部分代码靠测试、CI 和独立 AI 审核把关，不是人逐行读过。实验循环因时间原因提前结束（37 次，预算上限 150 次），见 ADR 0007。
