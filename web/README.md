# Fire Atlas 前端源码交接（web/）

这是当前已部署网页的完整源码副本，来源为现有 Sites 源码提交 `bd39d7f2c5064917cee042607433375d59913ebf`。本次只整理源码和交接文档；`src/`、入口、依赖、锁文件和已有测试保持原样，不调整功能、科学算法或部署方式。

现在的网址：<https://inspiratio-fire-atlas.hybrid-0f7b5-5906.chatgpt.site>（Sites 私有访问）。本次分支为 `feat/web`，合并后从 `main` 的 `web/` 接手。

## 本地运行、构建、测试

需要 **Node.js 22.16+**、npm；准备真实数据时还需要 GitHub CLI，运行 `gh auth login` 并确保账号能读取这个团队私有仓库。前端不需要 Python、FIRMS MAP_KEY、GPU、数据库。

```sh
git clone https://github.com/team-inspiratio/inspiratio-space-apps-2026.git
cd inspiratio-space-apps-2026
git switch feat/web                 # PR 合并后改用 main
cd web
npm ci
npm run data:prepare                # 先准备运行网页所需的 Release v1 数据
npm test
npm run dev
```

Vite 打印本地地址，通常为 `http://127.0.0.1:5173/`；方法与验证页在 `/methods.html`。`package-lock.json` 记录的下载源是 `registry.npmmirror.com`，访问不到时可用 `npm ci --registry=https://registry.npmjs.org/ --replace-registry-host=always`（不改锁文件）。生产构建和本地生产预览：

```sh
npm run build                      # 产物：web/dist/（两个页面：index.html、methods.html）
npm run preview
npm run methods:data               # 仅在 reports/ 或 results/final-test/ 更新后：重新生成 src/methods-data.json
```

**干净环境中直接 `npm ci && npm run build` 可以成功，但不包含科学数据。** `build` 本身不下载数据；要让浏览器正常加载六区数据，或发布完整网站，必须先单独运行 `npm run data:prepare`，再构建。不要部署未准备数据的 `dist/`。依赖由 `package-lock.json` 精确锁定。

测试在 `test/`（`feat/web-fixes` 新增了后 5 个文件）：

- `anomaly.test.mjs`：25 个官方异常指标用例，快照在 `test/fixtures/anomaly-cases.json`，对应根目录 `docs/anomaly-cases.json`；逐字段对答案，覆盖并列、历史不足、缺测、近实时及基准期等情况。
- `aggregate.test.mjs`：完整/部分格子权重、无覆盖不当作零、每次重抽先加总再取区间。
- `data.test.mjs`：六区、312 个月真实数据守恒及区间边界。未准备数据时真实数据检查会跳过，不能当成完整验收。
- `scale.test.mjs`：日历按当前区域第 5–99 百分位的对数色阶（加州 2020-09 在最深端，2020-05 在浅端）。
- `series.test.mjs`：年度汇总只算月份齐全的年份；直接拼接每个空白月都有原因（2012–13 盲测保留、S-NPP 中断、留出区）。
- `format.test.mjs`：估计值不显示小数（“≈ 11,600”）、百分位序数。
- `cell-layer.test.mjs`：地图格子的悬停查找。
- `methods-data.test.mjs`：`src/methods-data.json` 必须与 `reports/validation.json`、`results/final-test/scores.json` 和 `reports/final-test.md` 的结论一致。

仓库根目录的 Python 测试及 pre-commit 另外按 `AGENTS.md` 执行，与前端的 `npm test` 是两套检查。

## 数据来源、下载时机和 Git 边界

数据来自 [正式版 Release v1](https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/v1)。**科学数据未放进源码仓库，也不是构建时自动下载。** `npm run data:prepare` 调用 `scripts/prepare-data.mjs`，通过接手者已有的 GitHub CLI 登录获取：

| Release 文件 | 用途 / 本地位置 |
| --- | --- |
| `california.json.gz`、`cordoba.json.gz`、`southern_africa.json.gz`、`north_australia.json.gz`、`central_siberia.json.gz`、`indo_gangetic.json.gz` | 原样放入 `public/data/v1/`，网页按区域读取格子、月份、估计值、来源、覆盖和区域汇总 |
| `meta.json` | 模型与区间元数据，放入 `public/data/v1/` |
| `SHA256SUMS.txt` | 发布文件的校验清单，脚本还固定这份清单自身的 SHA256 |
| `anomaly-cases.json`、`data-card.md`、`data-interface.md` | 测试契约、数据说明与接口文档，放入 `public/data/v1/` |
| `region_totals_v1.csv` | 已发布的区域月度总量，放入 `public/data/v1/` |
| `dataset_v1.parquet` | 下载到 `.source-data/`，提取自定义选区需要的逐格原始计数和直接拼接值 |
| `resamples20_v1.parquet` | 下载到 `.source-data/`，提供自定义选区的 20 次重抽近似区间 |

脚本逐文件验证 SHA256，下载失败逐文件重试，并复用已有的正确文件。它把两份 Parquet 重排成每区 `*.raw.f32.gz` 和 `*.draws.f32.gz`，另写 `browser-assets.json`，都放在 `public/data/v1/`；只改变浏览器传输格式，不重训模型、不改变估计。构建时 Vite 把准备好的 `public/` 内容复制到 `dist/`。

`.source-data/`、`public/data/`、`node_modules/`、`dist/`、测试产物和本地环境文件均被 Git 忽略。仓库只保存测试快照、验证图和源文件。不要提交任何密钥，也不要把 GitHub/FIRMS token 写入浏览器或配置文件。

## 目录结构与主要组件

这是原有的 **Vite + 原生 JavaScript 单页应用**，主要视图仍集中在 `src/main.js`；本次不拆组件、不重构。

```text
web/
├── index.html                   页面入口
├── package.json                 dev / build / preview / test / data:prepare
├── package-lock.json            精确依赖锁定
├── .gitignore                   依赖、产物、数据、环境文件忽略规则
├── .openai/hosting.json          现有 Sites 项目标识、静态目录 dist
├── AGENTS.md                    前端范围与限制
├── PROGRESS.md                  原前端验收记录（历史）
├── src/
│   ├── main.js                  页面模板、视图、交互、加载、下载
│   ├── style.css                桌面和手机布局
│   ├── anomaly.js               异常指标参考实现的 JS 版本
│   └── aggregate.js             格子多边形、面积权重、加总、重抽区间
├── scripts/prepare-data.mjs      获取及校验 v1，生成浏览器数据
├── public/
│   ├── favicon.svg              图标
│   └── methods/*.png            原始分析图（方法页链接到它们）
└── test/
    ├── anomaly.test.mjs
    ├── aggregate.test.mjs
    ├── data.test.mjs
    └── fixtures/anomaly-cases.json
```

| 组件 | 代码定位 / 职责 |
| --- | --- |
| 地图 | `main.js` 的 Leaflet 初始化、`draw`、`applySelection`、`renderMap`（格子由 `src/cell-layer.js` 单一画布图层绘制）；区域预设、绘图、坐标输入及月度格子。面积运算在 `aggregate.js` |
| 日历 | `renderCalendar`、`showTooltip`；年×月色块、年范围、来源/质量标记、协调值与直接拼接切换 |
| 当月卡片 | `renderInsight` 调用 `anomaly.js`；同月历史百分位、中位数、倍数、基准期、参考年数及缺测/初步结果 |
| 折线图 | `renderTrend`；协调值、Aqua MODIS、S-NPP VIIRS 年度总量和年份联动 |
| 方法页 | 独立页面 `methods.html` + `src/methods.js`（`/methods.html`，各节有锚点，如 `#gfed`）；核心图由 `src/charts.js` 按网站样式重画，数字来自 `src/methods-data.json`；原图在 `public/methods/` |
| 下载 / 来源 | `#downloads-dialog`、`csv`、`exportPNG`；月度 CSV、选区 GeoJSON、日历 PNG、说明及完整 Release 链接 |

## 现有部署和重新部署方法

当前使用 **Sites**，网址为 <https://inspiratio-fire-atlas.hybrid-0f7b5-5906.chatgpt.site>。项目 ID `appgprj_6aeb7d430ce081918f28cc355b227d73` 保存在 `.openai/hosting.json`，它不是密钥。

**本次不重新部署、不改访问权限、不配置 GitHub Pages，也不增加自动发布。** 团队仓库提交或合并不会自动更新当前网页。

需要重新部署时，由有该 Sites 项目编辑/发布权限的人，在安装 Sites 插件的 Codex 中按现有流程：

1. 取团队仓库要发布的 `web/`，执行 `npm ci` → `npm run data:prepare` → `npm test` → `npm run build`。
2. 选择上面的**现有** Sites 项目，读取访问状态并获取同一项目的短期源码写凭据，不创建新项目。凭据只通过发布助手的隐藏 stdin 传递，不存文件、不写命令参数。
3. 按 Sites 技能，用源码助手在独立的 Sites checkout 中打开现有源码，再把 `web/` 内容作为该 checkout 的项目根目录同步进去；不要嵌成 `web/web/`，不要覆盖 `.git/`。保留项目 ID 和 `static.directory = dist`。
4. 在该 checkout 准备相同的校验数据并测试、构建，使用 Sites 源码助手推送项目源码并打包静态产物；团队仓库里的 `dist/` 不入 Git。
5. 用源码助手返回的精确源码提交与归档，执行 Sites 保存/私有部署操作，等待成功，再检查原网址。保留现有私有访问范围；给其他人访问/发布权限需项目所有者另行授权。

这是沿用既有托管服务的人工发版流程；不需要 GitHub Pages/Vercel 配置或前端密钥。

## 已知问题待修

- v1 网页资产没有原始逐点火点分区文件。当前提供的是网格月度 CSV，不能标作原始点数据；后续需要数据负责人提供经批准的点文件。
- 当前是六区 v1，尚未接入 `global-v1`；全球数据工作仍由原执行者负责。
- 自定义选区按重叠面积近似分配；20 次重抽区间是未校准近似，不是保证覆盖率的误差界。
- 字体依赖 Google Fonts，底图依赖 OpenStreetMap；离线可能回退字体和本地 Natural Earth 陆地轮廓。
- 独立设备的人类可用性检查仍待团队实际完成。接手源码需要团队仓库权限，重新部署还需要 Sites 编辑/发布权限。

后续问题通过单独 PR 修改。异常指标和数据契约以仓库根目录 `docs/anomaly-cases.json`、`docs/data-interface.md` 为准。
