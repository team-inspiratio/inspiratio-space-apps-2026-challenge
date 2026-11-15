"""S10 LightGBM: only allowed inputs, never the cell key; deterministic; non-negative."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harmonization import harmonize, prepare  # noqa: E402


def synthetic(n_cells: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    months = [f"{y}-{m:02d}" for y in range(2016, 2019) for m in range(1, 13)]
    cells = pd.DataFrame({"lat_idx": 400 + np.arange(n_cells) // 10, "lon_idx": np.arange(n_cells)})
    df = cells.merge(pd.DataFrame({"month": months}), how="cross")
    df["region"] = "california"
    df["lat"] = -90 + (df["lat_idx"] + 0.5) * 0.25
    df["cal_month"] = df["month"].str[5:7].astype(int)
    for f in prepare.features():
        if f not in ("lat", "cal_month"):
            df[f] = rng.random(len(df))
    df["aqua_count"] = rng.poisson(3, len(df)).astype(float)
    df["terra_count"] = rng.poisson(2, len(df)).astype(float)
    df["snpp_count"] = rng.poisson(4 * df["aqua_count"] + 0.2).astype(float)
    return df


def test_lgb_ignores_cell_key_and_is_deterministic():
    df = synthetic()
    cfg = {"max_rounds": 60, "early_stopping": 10, "min_data_in_leaf": 20, "optuna_trials": 0}
    p1 = harmonize.fit_lgb(df.copy(), **cfg)
    p2 = harmonize.fit_lgb(df.copy(), **cfg)
    x = prepare.feature_table(df)
    a = p1(x)
    assert np.array_equal(a, p2(x))
    shuffled = x.assign(lat_idx=x["lat_idx"].to_numpy()[::-1], lon_idx=0)
    assert np.array_equal(a, p1(shuffled))
    assert np.isfinite(a).all() and (a >= 0).all()
    used = p1.booster.feature_name()
    assert not set(used) & {"lat_idx", "lon_idx", "month", "year", "region"}
    assert not any(c.startswith(("snpp", "noaa20")) for c in used)
