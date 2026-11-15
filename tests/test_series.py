"""S09 dataset v0: source flags follow docs/decisions/0005 item 5, observed months are kept."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harmonization import grid, prepare, series  # noqa: E402


def tiny_grid() -> pd.DataFrame:
    """Two California cells and one north Australia cell, every month, real sensor status."""
    rng = np.random.default_rng(1)
    cells = grid.region_cells()
    cells = pd.concat(
        [
            cells[cells["region"] == "california"].head(2),
            cells[cells["region"] == "north_australia"].head(1),
        ]
    )
    df = cells.merge(pd.DataFrame({"month": grid.month_range()}), how="cross")
    df["lat"] = -90 + (df["lat_idx"] + 0.5) * 0.25
    df["cal_month"] = df["month"].str[5:7].astype(int)
    st = grid.month_status().pivot(index="month", columns="sensor", values="status")
    for s in ("terra", "aqua", "snpp", "noaa20"):
        df[f"{s}_status"] = df["month"].map(st[s])
    for f in prepare.features():
        if f not in ("lat", "cal_month"):
            df[f] = rng.random(len(df))
    df["terra_count"] = rng.poisson(4, len(df)).astype(float)
    on = df["aqua_status"] != "not_operating"
    df["aqua_count"] = np.where(on, rng.poisson(5, len(df)), np.nan)
    v_on = df["snpp_status"].isin(["complete", "partial"]) & (df["role"] == "train")
    df["snpp_count"] = np.where(v_on, 6 * df["aqua_count"].fillna(0), np.nan)
    n_on = df["noaa20_status"].isin(["complete", "partial"]) & (df["role"] == "train")
    df["noaa20_count"] = np.where(n_on, df["snpp_count"].fillna(30), np.nan)
    df.loc[df["role"] == "holdout", "snpp_status"] = "holdout_locked"
    df.loc[df["role"] == "holdout", "noaa20_status"] = "holdout_locked"
    return df


def test_sources_and_observed_months():
    out, meta = series.build(tiny_grid())
    src = out.set_index(["region", "month"])["source"].astype(str)
    ca = src.loc["california"].groupby(level=0).first()
    assert ca["2001-03"] == "m1s_terra_bridge"
    assert ca["2010-06"] == "m1s_aqua"
    assert ca["2012-06"] == "m1s_aqua"  # locked S-NPP year: never observed here
    assert ca["2015-06"] == "snpp"
    assert ca["2026-05"] == "noaa20_scaled"  # S-NPP missing all month
    assert set(src.loc["north_australia"]) <= {"m1s_aqua", "m1s_terra_bridge"}
    obs = out[out["source"] == "snpp"]
    assert (obs["est"] == obs["snpp_count"]).all()
    assert out["est"].notna().all() and (out["est"] >= 0).all()
    assert out.loc[out["role"] == "holdout", "snpp_count"].isna().all()
    assert meta["lambda"] == series.LAM
