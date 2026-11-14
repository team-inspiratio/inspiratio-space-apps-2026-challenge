# 任务卡 1-data：预注册与数据（S01–S06）

> 一个会话做完这张卡。开始前先按 [`AGENTS.md`](../../AGENTS.md) 的“开工流程”读进度、认领、预检。

## 前置条件

- S00 已完成（`PROGRESS.md` 里 S00 为 done，CI 是绿的）。
- 不需要任何 Release 数据包：本卡从零下载。
- 机器：约 50 GB 空闲磁盘（数据目录）、16 GB 以上内存、稳定网络。下载年度包合计几十 GB，需要数小时。

## 需要人准备

1. `.env` 里有 `FIRMS_MAP_KEY` 和 `INSPIRATIO_DATA_DIR`（预检会查）。
2. `gh auth login --web` 已完成（本卡结束时要用 `gh release create` 上传数据包）。

**留出区已确认，不用再问人**（用户，2026-11-03，见 [`docs/decisions/0001-留出区选择.md`](../decisions/0001-留出区选择.md)）：澳大利亚北部（稀树草原）、西伯利亚中部（北方森林）、印度恒河平原（农田），各约 10°×10°。S01 直接按这三个区写 `config/regions.json`：具体边界只按地理位置和生态类型定，**不看任何 VIIRS 数据**，不与训练区重叠，写好后冻结。

## 只读计划的这几节

[`docs/execution-plan.md`](../execution-plan.md) 的：第 1 节（已核实的事实）、第 2 节（方法）、第 3 节（验证，用于写预注册）、第 4 节（测试集隔离）、第 6 节表格中 S01–S06 这几行、第 10 节（数据接力）。需要字段含义、清洗细节时可查 [`docs/proposal.md`](../proposal.md) 的“数据”“基本单位与数据准备”和“A 线”；与执行计划冲突时以执行计划为准（例如执行计划用全球年度包，不需要 Earthdata 账号）。

## 要做的阶段

### S01 预注册（必须在任何建模之前 commit）

- `config/settings.yaml`：网格 0.25°、自然月（UTC）、时间范围 2000-11 至 2026-10、质量控制阈值（type=0；MODIS 置信度 ≥ 30；VIIRS 保留 n/h）、数据切分（训练 2016-01–2021-06；验证 2014–2015；辅助倒推 训练 2018–2021-06 验证 2016–2017；测试 1 2012-02–2013-12；测试 2 留出区）、随机种子。
- `config/regions.json`：训练和展示区（加州、阿根廷科尔多瓦、非洲南部稀树草原，边界参考 proposal 的“示范区域”）+ 已确认的 3 个留出区（见上），字段为 name、west/south/east/north、role（train 或 holdout）。
- 随机矩形：固定种子生成，每个 GFED 区约 150 个、每个示范区另加 200 个，1°–5° 见方，存为 `config/rectangles.parquet` 或 `.csv`（小文件可以进 git）。GFED 区的边界从 GFED4.1s 的 basis regions 取。
- `docs/preregistration.md`：把计划第 3 节的 1–7 条写成具体的指标、门槛和容差（例如选定规则“比 M1s 至少好 10% 且改进超过 1 个标准误”、零火点正估计比例的容许变化幅度），写明在看任何验证分数之前固定。
- `.github/workflows/grader.yml`（外部盲审，计划第 4.4 条）：
  - 只在推送 `final-test` 标签时触发；
  - 先检查 `results/final-test/` 是否已存在，存在就失败退出（只能考一次）；
  - 校验 `submission.parquet` 的哈希与冻结清单一致；
  - 在云端下载 2012、2013 年 S-NPP 年度包和留出区 VIIRS（年度包公开，不需要 key），用与标签同一 commit 的代码（`harmonization/final_test.py`，S07 写、S07 冻结）算标准答案并打分；
  - 把成绩提交回仓库（需要 `permissions: contents: write`）。
  - S01 时 `final_test.py` 还不存在，工作流里写好调用约定即可，在预注册里说明。
- 扩展护栏：在 `tools/guardrails.py` 里加留出区空间锁的辅助函数（例如 `in_holdout(lat, lon)`，读 `config/regions.json`），并补测试。
- 冻结：`uv run python tools/guardrails.py freeze config/settings.yaml config/regions.json config/rectangles.* .github/workflows/grader.yml tools/guardrails.py`，提交冻结清单。commit 信息写明“S01 预注册”。

### S02 下载

- 年度包：MODIS 2000–2025、S-NPP 2014–2025（**跳过 2012、2013**）、NOAA-20 2018–2025，下载到 `INSPIRATIO_DATA_DIR/raw/`，断点续传，每个文件记 SHA256 和行数到 `data/manifest`（小文件进 git，例如 `docs/data-manifest.csv`）。每次请求前调用 `assert_download_allowed()`。
- FIRMS API（用 `.env` 的 key，限速）：2026 年全年 SP 和 NRT（SP：VIIRS 到 2026-07-31、MODIS 到 2026-08-31；之后用 NRT），S-NPP 只到 2026-11-02。缺测清单 `/api/missing_data/?action=fetch_data`。
- GFED4.1s（0.25°，月度燃烧面积），作为第 3 节第 4 条的独立参照。
- 验收：随机抽几天，把 API 返回和年度包逐行比对，结果一致。

### S03 导入

- 流式把 CSV 转成 Parquet（按卫星、年份分区）。VIIRS 落在留出区的记录在流式导入时直接丢弃，不写盘。
- 导入完成后删除原始 VIIRS 压缩包，只保留哈希。
- 验收：行数账目闭合（原始行数 = 写入行数 + 留出区丢弃行数，每个文件一行账）。

### S04 清洗

- 只保留 type=0；MODIS 置信度 ≥ 30；VIIRS 保留 n/h；只合并重复下载的记录（按卫星、日期、分钟、经纬度；SP 优先于 NRT）。
- NRT 段没有 type 列：用 SP 期 type=2 的位置做固定热源掩膜，在清洗报告里注明。
- 随机抽 20 条被删记录人工检查。产出清洗报告 `reports/cleaning.md`（每条规则删了多少）。

### S05 网格化与特征

- 格子 × 月 × 卫星的计数；MODIS 特征（计数、FRP 中位数和 75 分位、低 FRP 占比、平均像元尺寸、纬度、月份、夜间占比、有火天数、邻格计数）。空格子的 FRP 类特征记缺失并加“无检测”标记。
- 区分 0 与缺测（缺测清单）。
- 验收：格子计数总和 = 清洗后火点总数（总数守恒），写进 pytest。

### S06 数据体检（A5）

- proposal 要求的 4 张图（训练区月度序列；S-NPP/Aqua 比值随时间；比值随纬度和像元尺寸；NOAA-20/S-NPP 比值），VIIRS 只画 2014-01 以后、只画训练区。
- 写 `reports/findings.md`（一页发现记录）。

## 验收标准

- S01 的 commit 时间早于任何建模代码；`grader.yml` 和预注册已提交并冻结；CI 绿。
- S02 抽样比对一致；S03 行数账目闭合；S04 清洗报告完成；S05 总数守恒测试通过；S06 4 张图和 findings.md 完成。
- 处理后的数据（清洗后 Parquet 和格子 × 月表，约 1–2 GB）已上传为 GitHub Release 附件（例如标签 `data-v0`，预发布），SHA256 记录在 `PROGRESS.md` 和数据清单里。

## 禁止事项

- 下载 2012/2013 年 S-NPP 任何数据；把留出区 VIIRS 写入磁盘；为挑区或调参看留出区或 2012–2013 年的 VIIRS。
- 换掉已确认的留出区（要换必须先问人）；S01 冻结后再改 settings、regions、grader。
- 把原始数据或大文件提交进 git；把 key 写进任何文件或日志。
- 开始任何建模（M0、M1s 等属于会话 2）。

## 结束时更新

- `PROGRESS.md`：S01–S06 每完成一个就更新阶段表（状态、时间、关键数字、commit）并 push；全部完成后状态块改为 `current_card: docs/sessions/2-baselines.md`、`status: ready`、清空认领、`last_pushed_stage: S06`，`needs_human` 换成会话 2 需要的东西。
- README 顶部进度框同步。确认 CI 是绿的。

## 下一张卡

[`2-baselines.md`](2-baselines.md)
