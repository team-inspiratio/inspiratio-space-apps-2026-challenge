# 0003 data-v0 does not upload the cleaned VIIRS point data

## Background

Task card 1-data asks for "the cleaned Parquet and the cell × month table, about 1–2 GB" to be uploaded as a Release. In practice the cleaned point data totals about 5.8 GB, of which VIIRS (S-NPP, NOAA-20) is about 4.6 GB, beyond the size the task card anticipated.

## Options

1. **Upload only the grid tables and the cleaned MODIS points** (about 1.5 GB): the only VIIRS information later stages use is the cell × month counts (the labels), which are already in the grid tables; the MODIS point data is kept so features can be recomputed.
2. **Upload everything** (about 6.1 GB): teammates get all intermediate data, but downloads are slow and beyond the size the task card anticipated.

## Recommendation

Option 1. When needed, the VIIRS point data can be rebuilt from the hash-pinned raw data (`docs/data-manifest.csv`, `docs/api-ledger.csv`; `harmonization.download` → `ingest` → `clean`).

## Status

**Confirmed: option 1 (qiuxue-yee, 2026-11-03).** The user's words (translated from Chinese): "Up to you; go with whichever you think is better." `data-v0` was uploaded according to option 1.
