"""S06 data health check (proposal A5): the four figures plus numbers for reports/findings.md.

uv run python -m harmonization.explore

Isolation (plan section 4, proposal A5): training regions only; VIIRS only from 2014-01. Holdout
regions and 2012-2013 VIIRS are never read or drawn (they are not on this machine anyway).
Ratios are region-month totals over cells where both sensors have a complete month.
"""

from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from harmonization.config import ROOT, data_dir  # noqa: E402

FIG = ROOT / "reports" / "figures"
VIIRS_FROM = "2014-01"
COLORS = {"terra": "#9e9e9e", "aqua": "#1f77b4", "snpp": "#d62728", "noaa20": "#ff7f0e"}
LABELS = {"terra": "Terra MODIS", "aqua": "Aqua MODIS", "snpp": "S-NPP VIIRS", "noaa20": "NOAA-20"}


def load() -> pd.DataFrame:
    df = pd.read_parquet(data_dir() / "processed" / "grid" / "regions.parquet")
    df = df[df["role"] == "train"].copy()
    for s in ("snpp", "noaa20"):
        early = df["month"] < VIIRS_FROM
        df.loc[early, f"{s}_count"] = np.nan
    df["date"] = pd.to_datetime(df["month"])
    return df


def complete(df: pd.DataFrame, *sensors: str) -> pd.Series:
    ok = pd.Series(True, index=df.index)
    for s in sensors:
        ok &= (df[f"{s}_status"] == "complete") & df[f"{s}_count"].notna()
    return ok


def monthly(df: pd.DataFrame, sensors: tuple[str, ...], by: str = "region") -> pd.DataFrame:
    sub = df[complete(df, *sensors)]
    return sub.groupby([by, "date"])[[f"{s}_count" for s in sensors]].sum().reset_index()


def fig_series(df: pd.DataFrame) -> dict:
    regions = sorted(df["region"].unique())
    fig, axes = plt.subplots(len(regions), 1, figsize=(12, 3.2 * len(regions)), sharex=True)
    stats = {}
    for ax, reg in zip(axes, regions, strict=True):
        d = df[df["region"] == reg]
        for s in ("terra", "aqua", "snpp", "noaa20"):
            m = d[complete(d, s)].groupby("date")[f"{s}_count"].sum()
            ax.plot(m.index, m.to_numpy(), lw=1, color=COLORS[s], label=LABELS[s])
            stats[f"{reg}_{s}_mean_monthly"] = float(m.mean()) if len(m) else None
        ax.set_yscale("symlog", linthresh=10)
        ax.set_title(reg)
        ax.set_ylabel("detections / month")
    axes[0].legend(ncol=4, fontsize=8)
    fig.suptitle("Training regions: monthly fire detections (VIIRS from 2014-01 only)")
    fig.tight_layout()
    fig.savefig(FIG / "a5-1-monthly-series.png", dpi=110)
    plt.close(fig)
    return stats


def fig_ratio_time(df: pd.DataFrame) -> dict:
    m = monthly(df, ("snpp", "aqua"))
    m = m[m["aqua_count"] >= 50]
    m["ratio"] = m["snpp_count"] / m["aqua_count"]
    fig, ax = plt.subplots(figsize=(12, 4))
    stats = {}
    for reg, d in m.groupby("region"):
        ax.plot(d["date"], d["ratio"], lw=1, marker=".", label=reg)
        before = d[(d["date"] >= "2014-01") & (d["date"] < "2021-07")]["ratio"]
        after = d[d["date"] >= "2021-07"]["ratio"]
        stats[reg] = {
            "median_2014_2021h1": float(before.median()),
            "median_2021h2_on": float(after.median()) if len(after) else None,
            "trend_per_year_2014_2021h1": float(
                np.polyfit(
                    (d.loc[before.index, "date"] - pd.Timestamp("2014-01-01")).dt.days / 365.25,
                    np.log(before),
                    1,
                )[0]
            )
            if len(before) > 12
            else None,
        }
    ax.axvline(pd.Timestamp("2021-07-01"), color="k", ls="--", lw=0.8)
    ax.text(pd.Timestamp("2021-08-01"), ax.get_ylim()[1] * 0.9, "Aqua drift starts", fontsize=8)
    ax.set_yscale("log")
    ax.set_ylabel("S-NPP / Aqua (region-month totals)")
    ax.set_title("S-NPP to Aqua ratio over time (months with >= 50 Aqua detections)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "a5-2-ratio-over-time.png", dpi=110)
    plt.close(fig)
    return stats


def fig_ratio_lat_pixel(df: pd.DataFrame) -> dict:
    sub = df[complete(df, "snpp", "aqua") & (df["date"] < "2021-07")].copy()
    sub["lat_band"] = (np.floor(sub["lat"] / 2) * 2).astype(int)
    by_lat = sub.groupby(["region", "lat_band"])[["snpp_count", "aqua_count"]].sum()
    by_lat = by_lat[by_lat["aqua_count"] >= 200]
    by_lat["ratio"] = by_lat["snpp_count"] / by_lat["aqua_count"]
    px = sub[sub["aqua_count"] > 0].copy()
    px["px_bin"] = pd.cut(px["aqua_pixel_area_mean"], [1, 1.25, 1.5, 2, 3, 4, 6, 10])
    by_px = px.groupby("px_bin", observed=True)[["snpp_count", "aqua_count"]].sum()
    by_px["ratio"] = by_px["snpp_count"] / by_px["aqua_count"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.2))
    for reg, d in by_lat.reset_index().groupby("region"):
        a1.plot(d["lat_band"] + 1, d["ratio"], marker="o", label=reg)
    a1.set_xlabel("latitude (2 deg bands, centre)")
    a1.set_ylabel("S-NPP / Aqua")
    a1.set_title("Ratio by latitude, 2014-01..2021-06")
    a1.legend(fontsize=8)
    a2.bar(range(len(by_px)), by_px["ratio"], color="#1f77b4")
    a2.set_xticks(range(len(by_px)), [str(i) for i in by_px.index], rotation=30, fontsize=8)
    a2.set_xlabel("mean Aqua pixel area in the cell-month (km^2)")
    a2.set_title("Ratio by Aqua pixel size (cell-months with Aqua > 0)")
    fig.tight_layout()
    fig.savefig(FIG / "a5-3-ratio-latitude-pixel.png", dpi=110)
    plt.close(fig)
    return {
        "by_latitude": {f"{r}|{b}": float(v) for (r, b), v in by_lat["ratio"].items()},
        "by_pixel_area": {str(k): float(v) for k, v in by_px["ratio"].items()},
    }


def fig_n20(df: pd.DataFrame) -> dict:
    m = monthly(df, ("noaa20", "snpp"))
    m = m[m["snpp_count"] >= 50]
    m["ratio"] = m["noaa20_count"] / m["snpp_count"]
    fig, ax = plt.subplots(figsize=(12, 4))
    stats = {}
    for reg, d in m.groupby("region"):
        ax.plot(d["date"], d["ratio"], lw=1, marker=".", label=reg)
        stats[reg] = {
            "median": float(d["ratio"].median()),
            "p10": float(d["ratio"].quantile(0.1)),
            "p90": float(d["ratio"].quantile(0.9)),
            "n_months": int(len(d)),
        }
    ax.axhline(1, color="k", lw=0.8)
    ax.set_ylabel("NOAA-20 / S-NPP")
    ax.set_title("NOAA-20 to S-NPP ratio (region-month totals, months with >= 50 S-NPP)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "a5-4-noaa20-snpp.png", dpi=110)
    plt.close(fig)
    return stats


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    df = load()
    stats = {
        "series": fig_series(df),
        "snpp_aqua_over_time": fig_ratio_time(df),
        "snpp_aqua_lat_pixel": fig_ratio_lat_pixel(df),
        "noaa20_snpp": fig_n20(df),
    }
    out = ROOT / "reports" / "a5-stats.json"
    out.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2)[:4000])
    (data_dir() / "S06.done").write_text("ok\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
