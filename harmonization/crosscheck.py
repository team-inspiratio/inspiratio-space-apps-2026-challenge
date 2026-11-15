"""S02 acceptance: random days, FIRMS API vs yearly package, row by row.

uv run python -m harmonization.crosscheck      # writes docs/crosscheck-api-vs-yearly.csv

Days are drawn with a fixed seed from 2025 (both products exist; no locked year). Holdout VIIRS
rows are removed from both sides in memory before comparing, and nothing is written but counts.
Rows are matched on (satellite, date, time, latitude, longitude rounded to 1e-4 deg).
"""

from __future__ import annotations

import datetime as dt
import sys
import zipfile

import numpy as np
import pandas as pd

from harmonization.config import ROOT, data_dir, in_holdout
from harmonization.download import api_day

OUT = ROOT / "docs" / "crosscheck-api-vs-yearly.csv"
PAIRS = [("MODIS_SP", "modis"), ("VIIRS_SNPP_SP", "viirs-snpp"), ("VIIRS_NOAA20_SP", "viirs-jpss1")]
YEAR = 2025


def keys(df: pd.DataFrame) -> pd.Series:
    t = pd.to_numeric(df["acq_time"]).astype(int).astype(str)
    return (
        df["satellite"].astype(str)
        + "|"
        + df["acq_date"].astype(str)
        + "|"
        + t
        + "|"
        + df["latitude"].round(4).astype(str)
        + "|"
        + df["longitude"].round(4).astype(str)
    )


def strip_holdout(df: pd.DataFrame, viirs: bool) -> pd.DataFrame:
    if not viirs or df.empty:
        return df
    return df[~np.asarray(in_holdout(df["latitude"].to_numpy(), df["longitude"].to_numpy()))]


def yearly_rows(prefix: str, days: set[str]) -> pd.DataFrame:
    path = data_dir() / "raw" / "firms_yearly" / f"{prefix}_{YEAR}_all_countries.zip"
    parts = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if not info.filename.endswith(".csv") or info.file_size == 0:
                continue
            for chunk in pd.read_csv(z.open(info), chunksize=1_000_000, dtype={"acq_time": str}):
                parts.append(chunk[chunk["acq_date"].isin(days)])
    return pd.concat(parts, ignore_index=True)


def main() -> int:
    rng = np.random.default_rng(20251)
    offsets = rng.choice(365, size=4, replace=False)
    days = sorted(dt.date(YEAR, 1, 1) + dt.timedelta(days=int(o)) for o in offsets)
    rows = []
    for source, prefix in PAIRS:
        viirs = source.startswith("VIIRS")
        yearly = strip_holdout(yearly_rows(prefix, {d.isoformat() for d in days}), viirs)
        for day in days:
            api = strip_holdout(api_day(source, day), viirs)
            y = yearly[yearly["acq_date"] == day.isoformat()]
            ka, ky = set(keys(api)), set(keys(y))
            both = ka & ky
            # Columns that must agree on matched rows
            m = api.assign(k=keys(api)).merge(y.assign(k=keys(y)), on="k", suffixes=("_a", "_y"))
            same = {
                c: float((m[f"{c}_a"].astype(str) == m[f"{c}_y"].astype(str)).mean())
                for c in ("confidence", "frp", "daynight", "type")
                if f"{c}_a" in m
            }
            rows.append(
                {
                    "source": source,
                    "day": day.isoformat(),
                    "api_rows": len(api),
                    "yearly_rows": len(y),
                    "matched": len(both),
                    "api_only": len(ka - ky),
                    "yearly_only": len(ky - ka),
                    "duplicate_keys_yearly": int(len(y) - len(ky)),
                    **{f"agree_{c}": v for c, v in same.items()},
                }
            )
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False, lineterminator="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
