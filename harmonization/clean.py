"""S04 cleaning (rules fixed in config/settings.yaml before any modelling).

uv run python -m harmonization.clean

Per sensor and year, in this order, counting what each rule removes:
  1. duplicates: same sensor, date, time, latitude, longitude (repeat downloads, records listed
     under two countries, SP/NRT overlap); the SP record wins over NRT;
  2. type: keep type 0 only. NRT rows have no type: drop NRT rows that fall on a static-source
     location (an ~1 km cell, or one of its 8 neighbours, with an SP type-2 detection in the
     mask years);
  3. confidence: MODIS >= 30; VIIRS nominal or high.
Output: <data>/processed/clean/<sensor>/<year>.parquet, docs/cleaning-counts.csv, and a sample
of removed rows for reports/cleaning.md.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from harmonization.config import ROOT, data_dir, settings

COUNTS = ROOT / "docs" / "cleaning-counts.csv"
COLUMNS = [
    "sensor",
    "product",
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "confidence",
    "frp",
    "scan",
    "track",
    "daynight",
    "type",
]


def points(sensor: str, year: int) -> pd.DataFrame:
    folder = data_dir() / "interim" / "points" / sensor / str(year)
    files = sorted(folder.glob("*.parquet"))
    if not files:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(
        [pq.read_table(f, columns=COLUMNS).to_pandas() for f in files], ignore_index=True
    )


def mask_key(lat: np.ndarray, lon: np.ndarray, cell: float) -> np.ndarray:
    i = np.floor((lat + 90) / cell).astype(np.int64)
    j = np.floor((lon + 180) / cell).astype(np.int64)
    return i * 100_000 + j


def static_mask() -> set[int]:
    """~1 km cells (with neighbours) where SP flagged a static source (type 2) in mask years."""
    m = settings()["quality_control"]["nrt_static_mask"]
    cell = m["cell_deg"]
    keys: set[int] = set()
    for sensor_dir in (data_dir() / "interim" / "points").iterdir():
        for year in range(m["years"][0], m["years"][1] + 1):
            for f in (sensor_dir / str(year)).glob("*.parquet"):
                t = pq.read_table(
                    f,
                    columns=["product", "latitude", "longitude", "type"],
                    filters=[("type", "=", 2), ("product", "=", "SP")],
                )
                if t.num_rows == 0:
                    continue
                lat = t["latitude"].to_numpy()
                lon = t["longitude"].to_numpy()
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        keys.update(mask_key(lat + di * cell, lon + dj * cell, cell).tolist())
    return keys


def clean(df: pd.DataFrame, mask: set[int]) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    qc = settings()["quality_control"]
    counts = {"rows_in": len(df)}
    removed = []

    order = df["product"].map({p: i for i, p in enumerate(qc["dedup_priority"])})
    df = df.assign(_order=order).sort_values("_order", kind="stable")
    dup = df.duplicated(["sensor", "acq_date", "acq_time", "latitude", "longitude"], keep="first")
    counts["removed_duplicate"] = int(dup.sum())
    removed.append(df[dup].assign(rule="duplicate"))
    df = df[~dup].drop(columns="_order")

    sp_bad = (df["type"] >= 0) & ~df["type"].isin(qc["keep_type"])
    counts["removed_type"] = int(sp_bad.sum())
    removed.append(df[sp_bad].assign(rule="type"))
    df = df[~sp_bad]

    nrt = (df["type"] < 0).to_numpy()
    static = np.zeros(len(df), dtype=bool)
    if nrt.any() and mask:
        cell = qc["nrt_static_mask"]["cell_deg"]
        keys = mask_key(df["latitude"].to_numpy()[nrt], df["longitude"].to_numpy()[nrt], cell)
        static[np.flatnonzero(nrt)] = np.isin(keys, np.fromiter(mask, dtype=np.int64))
    counts["removed_nrt_static_mask"] = int(static.sum())
    removed.append(df[static].assign(rule="nrt_static_mask"))
    df = df[~static]

    if df["sensor"].iloc[0:1].isin(["terra", "aqua"]).all():
        conf = pd.to_numeric(df["confidence"], errors="coerce")
        low = ~(conf >= qc["modis_min_confidence"])
    else:
        low = ~df["confidence"].str.lower().str[0].isin(qc["viirs_keep_confidence"])
    counts["removed_confidence"] = int(low.sum())
    removed.append(df[low].assign(rule="confidence"))
    df = df[~low]

    counts["rows_out"] = len(df)
    return df.reset_index(drop=True), counts, pd.concat(removed, ignore_index=True)


def main() -> int:
    root = data_dir() / "interim" / "points"
    out_root = data_dir() / "processed" / "clean"
    mask = static_mask()
    print(f"static-source mask: {len(mask)} ~1 km cells", flush=True)
    rng = np.random.default_rng(settings()["seeds"]["bootstrap"])
    rows, samples = [], []
    for sensor_dir in sorted(root.iterdir()):
        for year_dir in sorted(sensor_dir.iterdir(), key=lambda p: int(p.name)):
            sensor, year = sensor_dir.name, int(year_dir.name)
            df = points(sensor, year)
            if df.empty:
                continue
            kept, counts, removed = clean(df, mask)
            out = out_root / sensor / f"{year}.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            kept.to_parquet(out, index=False, compression="zstd")
            rows.append({"sensor": sensor, "year": year, **counts})
            if len(removed):
                samples.append(
                    removed.sample(min(len(removed), 50), random_state=int(rng.integers(1 << 31)))
                )
            print(f"ok {sensor} {year}: {counts}", flush=True)
    pd.DataFrame(rows).to_csv(COUNTS, index=False, lineterminator="\n")
    # 20 removed rows for manual review: up to 5 per rule, the rest at random.
    pool = pd.concat(samples, ignore_index=True).drop(columns="_order", errors="ignore")
    picked = pd.concat([g.sample(min(len(g), 5), random_state=1) for _, g in pool.groupby("rule")])
    rest = pool.drop(picked.index).sample(max(0, 20 - len(picked)), random_state=1)
    sample = pd.concat([picked, rest]).head(20)
    sample.to_csv(ROOT / "docs" / "removed-sample.csv", index=False, lineterminator="\n")
    (data_dir() / "S04.done").write_text("ok\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
