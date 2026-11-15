# 0003 data-v0 不上传 VIIRS 清洗后点数据

## 背景

任务卡 1-data 要求把“清洗后 Parquet 和格子 × 月表，约 1–2 GB”上传为 Release。实际清洗后点数据合计约 5.8 GB，其中 VIIRS（S-NPP、NOAA-20）约 4.6 GB，超出任务卡给的量级。

## 选项

1. **只传网格表和 MODIS 清洗点**（约 1.5 GB）：后续阶段用到的 VIIRS 信息只有格子 × 月计数（标签），已在网格表里；MODIS 点数据保留，便于重算特征。
2. **全部上传**（约 6.1 GB）：队友能拿到全部中间数据，但下载慢，超出任务卡量级。

## 建议

选项 1。VIIRS 点数据需要时可以用哈希锁定的原始数据重建（`docs/data-manifest.csv`、`docs/api-ledger.csv`，`harmonization.download` → `ingest` → `clean`）。

## 状态

**已确认：选项 1（qiuxue-yee，2026-11-03）。** 用户原话：“看你自己 你觉得哪个好就按照哪个来”。`data-v0` 已按选项 1 上传。
