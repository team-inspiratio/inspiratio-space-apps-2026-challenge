# Inspiratio Site

这是独立的 Svelte / Vite 网站快照。项目主仓库中的 `archive/` 和 `website/` 是其他版本。

## 本地运行

从这个目录运行下列命令。

```sh
npm ci
npm run dev -- --port 5199
```

打开 [localhost:5199](http://localhost:5199)。运行 `npm test` 执行单元测试，`npm run check` 执行类型检查，`npm run build` 生成 `dist/`。

网站读取随目录提供的 `public/` 资源。月度数据和火点格网来自 Inspiratio `global-v1`（CC BY 4.0），基于 NASA FIRMS 的 MODIS 与 VIIRS 火点资料。地图地理资料来自 Natural Earth。数据口径见[全球数据接口](../docs/data-interface-global.md)。

## 交接材料

- [修改提示词及两张原始截图](revision-handoff/)
- [上一轮交接摘要](revision-handoff/PRIOR-STATUS.md)
- [既有演示录屏](out/scroll-desktop.mp4)和 [review 截图](review/)
