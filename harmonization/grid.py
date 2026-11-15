"""S05 gridding and features: 0.25 deg cell x calendar month (UTC) x sensor.

uv run python -m harmonization.grid

Outputs in <data>/processed/grid/:
  counts.parquet       sparse global table, one row per (sensor, cell, month) with >= 1 point:
                       count, day/night counts, and for MODIS the per-cell-month FRP and pixel
                       statistics used as features
  month_status.parquet per sensor and month: complete / partial / missing / not_operating /
                       locked, from the FIRMS missing-data list (docs/firms-missing-data.csv)
  regions.parquet      dense table (every cell x month, 2000-11..2026-10) for the cells of
                       config/regions.json: MODIS features + VIIRS labels. 0 means "no detection
                       recorded"; months that are missing, not operated or locked are NaN, never 0.
                       Holdout cells carry no VIIRS label at all (dropped at import).
Cell index: lat_idx = floor((lat + 90) / 0.25), lon_idx = floor((lon + 180) / 0.25) (0 at the
south-west corner). Feature names are listed in config/features.json.
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from harmonization.config import ROOT, data_dir, regions, settings

MODIS = ("terra", "aqua")
VIIRS = ("snpp", "noaa20")
NLAT, NLON = 720, 1440
MISSING_NAMES = {
    "terra": "Terra (MODIS)",
    "aqua": "Aqua (MODIS)",
    "snpp": "Suomi NPP (VIIRS)",
    "noaa20": "NOAA-20 (VIIRS)",
}
FEATURES = [  # per MODIS sensor s, plus cell latitude and calendar month
    "count",
    "frp_median",
    "frp_p75",
    "low_frp_share",
    "pixel_area_mean",
    "night_share",
    "fire_days",
    "nbr_count",
    "no_detection",
]


def cell_index(lat: np.ndarray, lon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    cell = settings()["grid"]["cell_deg"]
    i = np.clip(np.floor((np.asarray(lat) + 90) / cell).astype(np.int32), 0, NLAT - 1)
    j = np.clip(np.floor((np.asarray(lon) + 180) / cell).astype(np.int32), 0, NLON - 1)
    return i, j


def aggregate(points: pd.DataFrame, modis: bool) -> pd.DataFrame:
    """Per (cell, month) counts; MODIS also gets FRP / pixel statistics."""
    i, j = cell_index(points["latitude"].to_numpy(), points["longitude"].to_numpy())
    date = pd.to_datetime(points["acq_date"])
    low = settings()["quality_control"]["low_frp_mw"]
    df = pd.DataFrame(
        {
            "lat_idx": i,
            "lon_idx": j,
            "month": date.dt.strftime("%Y-%m").to_numpy(),
            "night": (points["daynight"].to_numpy() == "N"),
            "day": date.dt.day.to_numpy(),
            "frp": points["frp"].to_numpy(),
            "low": points["frp"].to_numpy() < low,
            "area": (points["scan"] * points["track"]).to_numpy(),
        }
    )
    g = df.groupby(["lat_idx", "lon_idx", "month"], sort=True)
    out = g.agg(count=("night", "size"), count_night=("night", "sum"))
    out["count_day"] = out["count"] - out["count_night"]
    if modis:
        more = g.agg(
            frp_median=("frp", "median"),
            low_frp_share=("low", "mean"),
            pixel_area_mean=("area", "mean"),
            fire_days=("day", "nunique"),
        )
        more["frp_p75"] = g["frp"].quantile(0.75)
        out = out.join(more)
        out["night_share"] = out["count_night"] / out["count"]
    return out.reset_index()


def month_range() -> list[str]:
    g = settings()["grid"]
    return [
        p.strftime("%Y-%m") for p in pd.period_range(g["start_month"], g["end_month"], freq="M")
    ]


def month_status() -> pd.DataFrame:
    """Status of each sensor-month from operating dates, locked years and the missing-data list."""
    sens = settings()["sensors"]
    locked = set(settings()["splits"]["locked_snpp_years"])
    miss = pd.read_csv(ROOT / "docs" / "firms-missing-data.csv")
    rows = []
    for sensor in MODIS + VIIRS:
        first = pd.Timestamp(sens[sensor]["first_day"])
        last = pd.Timestamp(sens[sensor].get("last_day", "2100-01-01"))
        missing_days = set(
            pd.to_datetime(miss.loc[miss["sensor"] == MISSING_NAMES[sensor], "date"])
        )
        for m in month_range():
            p = pd.Period(m, "M")
            days = pd.date_range(p.start_time, p.end_time.normalize(), freq="D")
            operating = [d for d in days if first <= d <= last]
            n_missing = sum(d in missing_days for d in operating) + len(days) - len(operating)
            if sensor == "snpp" and p.year in locked:
                status = "locked"
            elif not operating:
                status = "not_operating"
            elif n_missing == 0:
                status = "complete"
            elif n_missing == len(days):
                status = "missing"
            else:
                status = "partial"
            rows.append({"sensor": sensor, "month": m, "status": status, "days_missing": n_missing})
    return pd.DataFrame(rows)


def region_cells() -> pd.DataFrame:
    cell = settings()["grid"]["cell_deg"]
    parts = []
    for r in regions():
        i0, i1 = round((r["south"] + 90) / cell), round((r["north"] + 90) / cell)
        j0, j1 = round((r["west"] + 180) / cell), round((r["east"] + 180) / cell)
        ii, jj = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1), indexing="ij")
        parts.append(
            pd.DataFrame(
                {
                    "lat_idx": ii.ravel(),
                    "lon_idx": jj.ravel(),
                    "region": r["name"],
                    "role": r["role"],
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def neighbour_counts(counts: pd.DataFrame, cells: pd.DataFrame) -> pd.DataFrame:
    """Sum of the 8 neighbours' counts for every (cell in `cells`, month); longitude wraps."""
    want = cells["lat_idx"].to_numpy() * NLON + cells["lon_idx"].to_numpy()
    parts = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == dj == 0:
                continue
            shifted = counts[["lat_idx", "lon_idx", "month", "count"]].copy()
            shifted["lat_idx"] = shifted["lat_idx"] - di
            shifted["lon_idx"] = (shifted["lon_idx"] - dj) % NLON
            key = shifted["lat_idx"].to_numpy() * NLON + shifted["lon_idx"].to_numpy()
            parts.append(shifted[np.isin(key, want)])
    nbr = pd.concat(parts).groupby(["lat_idx", "lon_idx", "month"])["count"].sum()
    return nbr.rename("nbr_count").reset_index()


def build_counts() -> pd.DataFrame:
    root = data_dir() / "processed" / "clean"
    parts = []
    for sensor in MODIS + VIIRS:
        for f in sorted((root / sensor).glob("*.parquet")):
            pts = pd.read_parquet(
                f, columns=["latitude", "longitude", "acq_date", "daynight", "frp", "scan", "track"]
            )
            agg = aggregate(pts, sensor in MODIS)
            agg.insert(0, "sensor", sensor)
            parts.append(agg)
            print(f"  {sensor} {f.stem}: {len(pts)} points -> {len(agg)} cell-months", flush=True)
    counts = pd.concat(parts, ignore_index=True)
    # A month can straddle two yearly files only if a file holds another year's dates; re-merge.
    if counts.duplicated(["sensor", "lat_idx", "lon_idx", "month"]).any():
        raise SystemExit("cell-month split across files; check year partitioning")
    return counts


def dense_regions(
    counts: pd.DataFrame, status: pd.DataFrame, cells: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Dense cell x month table of `cells` (lat_idx, lon_idx, region, role); default: the cells
    of config/regions.json. Stage G passes the global cells (harmonization/global_grid.py)."""
    cells = region_cells() if cells is None else cells
    months = month_range()
    cell = settings()["grid"]["cell_deg"]
    base = cells.merge(pd.DataFrame({"month": months}), how="cross")
    base["lat"] = -90 + (base["lat_idx"] + 0.5) * cell
    base["cal_month"] = base["month"].str[5:7].astype(int)
    key = ["lat_idx", "lon_idx", "month"]
    st = status.pivot(index="month", columns="sensor", values="status")
    for sensor in MODIS + VIIRS:
        c = counts[counts["sensor"] == sensor].drop(columns="sensor")
        cols = ["count", "count_day", "count_night"]
        if sensor in MODIS:
            nb = neighbour_counts(c, cells)
            c = c.merge(nb, on=key, how="outer")
            cols += [f for f in FEATURES if f not in ("count", "no_detection")]
        sub = base[key].merge(c[key + [x for x in cols if x in c]], on=key, how="left")
        for x in ("count", "count_day", "count_night", "nbr_count", "fire_days"):
            if x in sub:
                sub[x] = sub[x].fillna(0)
        ok = base["month"].map(st[sensor]).isin(["complete", "partial"]).to_numpy()
        if sensor in VIIRS:
            ok = ok & (base["role"] == "train").to_numpy()  # holdout VIIRS never stored
        for x in cols:
            if x in sub:
                base[f"{sensor}_{x}"] = np.where(ok, sub[x].to_numpy(), np.nan)
        if sensor in MODIS:
            base[f"{sensor}_no_detection"] = np.where(ok, base[f"{sensor}_count"] == 0, np.nan)
        base[f"{sensor}_status"] = base["month"].map(st[sensor])
        if sensor in VIIRS:
            base.loc[base["role"] == "holdout", f"{sensor}_status"] = "holdout_locked"
    return base


def write_feature_list() -> None:
    names = ["lat", "cal_month"] + [f"{s}_{f}" for s in MODIS for f in FEATURES]
    out = {
        "_comment": "Model inputs (S05). MODIS only plus latitude and calendar month; no year, "
        "region name or VIIRS information (AGENTS.md red line 3, checked by CI).",
        "features": names,
    }
    path = ROOT / "config" / "features.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    out = data_dir() / "processed" / "grid"
    out.mkdir(parents=True, exist_ok=True)
    counts = build_counts()
    counts.to_parquet(out / "counts.parquet", index=False, compression="zstd")
    status = month_status()
    status.to_parquet(out / "month_status.parquet", index=False)
    status.to_csv(ROOT / "docs" / "month-status.csv", index=False, lineterminator="\n")
    dense = dense_regions(counts, status)
    dense.to_parquet(out / "regions.parquet", index=False, compression="zstd")
    write_feature_list()
    totals = counts.groupby("sensor")["count"].sum()
    print("cell counts per sensor:", totals.to_dict())
    (data_dir() / "S05.done").write_text("ok\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
