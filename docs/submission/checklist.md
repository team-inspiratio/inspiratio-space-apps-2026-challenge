# 提交前检查清单

> **草稿。11/13 官方指南发布后逐项核对。** Project Submission Guide 和 Judging & Awards Guide 都在 11 月 13 日发布，下面的要求来自 2026 年 FAQ、参赛条款和 `docs/proposal.md`（2025 年规则），到时候以官方指南为准。
>
> 依据：[Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/)、[Terms & Conditions](https://www.spaceappschallenge.org/legal/)（2026-11-04 读取）。

## 一、先解决的前提

- [ ] 确认队伍报的是 Local Event 还是 Universal Event。提案写的是 Universal；两者的联系人和截止时间不同
- [ ] 审核包的 A 组都已签字

## 二、资格

- [ ] 全员已在 spaceappschallenge.org 注册并接受条款（报名开放到 11 月 15 日比赛结束）
- [ ] 队伍不超过 6 人；Universal Event 至少 2 人才有全球评审资格
- [ ] 每人只在一个队，全队只做一个题目
- [ ] 全员都在同一个活动下
- [ ] 如果有未满 18 岁的队员：照片、视频、声音都不能用，且按 FAQ 由监护人注册和陪同

## 三、代码、数据、许可

- [ ] 代码仓库已公开，评委不登录能打开（现在是私有，审核包 X2）
- [ ] 公开前人工检查过历史和 Release 内容，gitleaks CI 通过
- [ ] 已加代码许可证，并符合 OSI 开源定义（现在仓库没有 LICENSE 文件）
- [ ] 数据集 Release v1 / global-v1 可公开下载，CC BY 4.0
- [ ] 非 NASA 材料都已确认公开可用，许可证写在提交文档里：GFED4.1s、OpenStreetMap 底图、Natural Earth、LightGBM、Leaflet、leaflet-draw、Turf、topojson-client、world-atlas、Vite、hyparquet
- [ ] **每一个来源都已引用**，包括开源软件。条款写明不引用可能被撤下或撤销奖项
- [ ] FIRMS 致谢语已放进项目页
- [ ] 确认作品不含出口管制信息（条款要求团队自己负责）

## 四、网站

- [ ] PR #4、#5 已合并，修复版已部署（ADR 0016）
- [ ] 无痕窗口打开首页和 `/methods.html`，都不是旧版
- [ ] 没登录过的手机上再测一次
- [ ] 方法页的代码和报告链接在仓库公开后能打开
- [ ] 确认网站能保留到 2027 年 1 月公布获奖名单之后
- [ ] 网页只用已发布数据，没有在前端改数

## 五、项目页

- [ ] `project-page.md` 里所有方括号都已处理
- [ ] 文中数字和 `reports/` 再核对一遍，末尾的“Where the numbers come from”已删除
- [ ] 全文没有 accuracy、error bar、forecast、burned area 这类说法
- [ ] 盲审成绩和全球验证成绩分开写，明确全球版没有盲审
- [ ] 训练区以外的局限写在正文里，不是脚注
- [ ] SI 使用说明已写，包括视频、图片用到的工具（官方要求每个项目都写）
- [ ] 第三方内容的使用符合 [品牌指南](https://www.spaceappschallenge.org/brand/)，没有擅用 NASA 标志
- [ ] 至少一名队友通读全文

## 六、演示

- [ ] 视频时长和格式符合官方指南（暂按 30 秒、英文字幕）
- [ ] 或幻灯片符合官方指南（暂按不超过 7 页、全英文）
- [ ] 用修复版网站录制
- [ ] 视频由团队自己制作，素材没有侵权（条款要求）
- [ ] 公开链接在无痕窗口可以播放

## 七、提交

- [ ] 在队伍页面的 Project 标签页提交，这是进入全球评审的唯一方式
- [ ] 所有必填项已填
- [ ] 确认活动的截止时间。提案记的是 11 月 14 日 9:00 开放、11 月 15 日 23:59（活动当地时间）截止，FAQ 说按所选活动的结束时间
- [ ] 至少提前几小时提交，留出修改时间
- [ ] 保存确认页截图

## 八、11/13 指南发布当天要核对

- [ ] 2026 年评分标准和奖项（提案用的是 2025 版）
- [ ] 视频长度、格式、幻灯片页数
- [ ] 必填字段和字数限制
- [ ] 对 AI（SI）说明的具体要求
- [ ] 挑战资源（11 月 13 日发布）里有没有新的数据或要求
