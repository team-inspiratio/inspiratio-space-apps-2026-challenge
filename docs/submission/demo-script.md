# Demo script draft

> **草稿。11/13 官方指南发布后逐项核对。** DRAFT: check against the official guide published on November 13. The format (30-second captioned video, or up to 7 slides) comes from the 2025 rules in `docs/proposal.md`.
>
> The video must be the team's original work. If any team member is under 18, their photo, voice or likeness must not appear (official FAQ). This script uses screen recording and captions only.

## 主线

问题（2012 年跳 5 倍）→ 修复（协调开关）→ 用法（选区域、看当月异常、下载）→ 验证（测试成绩）。

**录制前提**：用 PR #5 合并并部署后的网站。线上旧版没有方法页，当月卡片也是旧写法。

## 30-second video

Captions are the only text channel. Keep each on screen for its full duration.

| # | Time | Length | Screen | Action | Caption |
|---|---|---|---:|---|---|
| 1 | 0:00–0:05 | 5 s | Fire Atlas home, map in view | Slow scroll | S-NPP just stopped. MODIS is retiring. 26 years of fire records are at a handover. |
| 2 | 0:05–0:11 | 6 s | Southern Africa, Direct splice calendar | Click Southern Africa, click Direct splice | Join the old and new sensors as they are, and fire jumps about 5× at 2012. |
| 3 | 0:11–0:16 | 5 s | Same calendar | Click Harmonized | That was the sensor, not more fire. Harmonized: one scale, no jump. |
| 4 | 0:16–0:23 | 7 s | Córdoba, month card, then Download data | Click Córdoba, point at card, click Download data, click Selected monthly series | Pick a region. See if the latest month is unusual. Download the data. |
| 5 | 0:23–0:28 | 5 s | `/methods.html`, score table | Scroll to Primary score | One blind test: 22% lower error in training regions. Unseen regions: 2.5× larger error. |
| 6 | 0:28–0:30 | 2 s | Logo and web address | Hold | Fire Atlas · Team Inspiratio · NASA FIRMS data |

**Checks after editing:**

- Total length is 30 seconds or less in a player, not just in the editor.
- Caption 5 stays as written. Cutting the second sentence would overstate accuracy outside the training regions.
- Do not add "predicts", "accuracy", "error bars" or "burned area".

**Why each number is safe:**

| Caption | Source |
|---|---|
| S-NPP stopped, MODIS retiring | `docs/proposal.md`, FIRMS and Earthdata notices |
| 26 years | Release v1 covers 2000-11 to 2026-10 |
| About 5× | `reports/validation.md`, conclusion 1 |
| 22% lower, 2.5× larger | `reports/final-test.md`, sections 1 and 6 |

## 演示路线

2026-11-04 在 PR #5 的生产构建（`7da3a4a`，Release v1 数据）上用真实鼠标点击走过一遍，三条都能走通，没有控制台错误。

**“一键进入”的实际情况**：左侧六个预设区域按钮都是一键进入区域。但网页**没有**“一键直达某区域某月”的入口，地址也不记录区域和月份，所以每条路线要 1–3 次点击。这不是 bug，加深链接属于新功能，按要求没有做。需要的话由人决定。

| 路线 | 操作 | 页面显示 | 旁白 |
|---|---|---|---|
| **A 加州 2020 大火季** | 打开首页（默认加州）→ 点日历 2020 年 Sep 格 | September 2020，125,460，Above normal · 100th percentile，21.9× | September 2020 is the biggest month in California's record: 125,460 detections, about 22 times the median of earlier Septembers. |
| **B 科尔多瓦看最近一个月** | 刷新页面 → 点 Córdoba | October 2026，1,272，Below normal · 0th percentile，0.3×，标 Preliminary | Córdoba's latest month reads below normal: 1,272 detections against a usual 4,220 or so, and the figure is still preliminary. |
| **C 南部非洲看 2012 跳变** | 点 Southern Africa → 点 Direct splice → 点 Harmonized | 直接拼接：2011 年 266,145，2014 年 1,195,314；协调后 2011 年约 129 万 | Joined as-is, 2011 shows about 266,000 detections and 2014 about 1.2 million; harmonized, 2011 is about 1.29 million and the jump is gone. |

**路线 B 的备用**：点 Córdoba 后再点日历 2020 年 Sep 格，显示 19,346，Above normal · 100th percentile，2.4×。

**录制注意**：

- 月份会跨区域保留：走完路线 A 再点 Córdoba，看到的还是 2020 年 9 月。要看最新月份，先刷新页面。
- 路线 C 的跳变，日历上要滚到 2014 和 2012 附近，下方折线图更直观。
- “Download data” 打开的是弹窗，要再点 “Selected monthly series” 才会下载（科尔多瓦得到 310 行的 `cordoba-monthly-v1.csv`）。
- 路线 B 的 2026-10 是近实时数据，页面标了 Preliminary，以后可能小幅修订。如果数据更新了，录制前重看一遍数字。
- 只用这三个训练区。不要用留出区讲故事，它们每个月都是低置信度估计。
- 全球版接入后，上述数字可能不同（全球模型的数值和 v1 不同），要重走一遍。

**数字来源**：路线里的数值是网页显示的 Release v1 数据，其中加州 2020-09 和 2020-05 的对比也在 `web/test/scale.test.mjs` 里；南部非洲的跳变倍数以 `reports/validation.md` 为准。

## Backup: slide outline (7 slides maximum)

Use this if the team submits slides instead of a video. All slides in English.

| # | Title | Content | Visual |
|---|---|---|---|
| 1 | One fire record across two satellite generations | S-NPP has stopped and MODIS is retiring. The record needs one scale | Atlas home screenshot |
| 2 | The 2012 jump is not real | Same fires, VIIRS records 4.8–5.6× more detections than Aqua (southern Africa, 2014–21). Joined as-is, fire jumps about 5× | `reports/figures/d1-1-problem.png` or the redrawn Figure 1 |
| 3 | Harmonized: one scale, MODIS inputs only | Two-stage LightGBM learned on the overlap. Estimates flagged, observations kept | Calendar with the Harmonized / Direct splice switch |
| 4 | Use it: region, month, download | Pick a region or draw one. Compare a month with its history. Take the CSV | Month card and calendar |
| 5 | Tested once, blind | Pre-registered. Sealed submission graded by GitHub Actions. Test 1 MALE 0.258 vs 0.332 for the simple ratio | Score table |
| 6 | Where it holds, and where it doesn't | Training regions: within 9% yearly. Unseen regions: 2.5× larger error, totals run low. Global version: validation only, no blind test | `reports/figures/d1-2-test-totals.png` |
| 7 | Open data, open method | Dataset CC BY 4.0, reproducible pipeline, SI use disclosed. Next: more training regions and a new blind test | Links |

**Do not add a slide 8.** If one more point is needed, merge it into slide 7.
