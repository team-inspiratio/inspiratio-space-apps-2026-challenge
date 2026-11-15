"""Stage G (docs/decisions/0013): the global rerun changes scale, not results.

- ratios fitted on per-cell sums equal series_v1's ratios on the rows;
- predicting each distinct feature row once and broadcasting equals predicting every row;
- the source masks are those of series_v1.build;
- (with the data folder) the global cells keep the holdout boxes holdout and every rectangle
  complete.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harmonization import harmonize, prepare, series_global, series_v1  # noqa: E402
from tests.test_series import tiny_grid  # noqa: E402


def grid_str() -> pd.DataFrame:
    df = tiny_grid()
    df["region"] = df["region"].astype(str)
    return df


def assert_same_ratios(a: dict, b: dict) -> None:
    pd.testing.assert_frame_equal(a["cell"], b["cell"])
    pd.testing.assert_series_equal(a["pooled"], b["pooled"])
    pd.testing.assert_series_equal(a["region_month"], b["region_month"])
    assert a["fallbacks"] == b["fallbacks"]


def test_ratios_from_sums_equal_ratios_from_rows():
    df = grid_str()
    for col in ("terra_count", "aqua_count", "snpp_count", "noaa20_count"):
        df[col] = np.round(df[col])  # FIRMS counts are whole numbers
    half = len(df) // 2  # two "bands"
    sums = pd.concat([series_global.bridge_sums(df[:half]), series_global.bridge_sums(df[half:])])
    assert_same_ratios(series_global.bridge_from(sums), series_v1.bridge_ratios(df))
    rows = df[
        (df["role"] == "train").to_numpy()
        & series_v1.span(df, series_v1.CONT_FIT)
        & series_v1.ok(df, "snpp")
        & series_v1.ok(df, "noaa20")
    ]
    direct = harmonize.m1s_ratios(rows, series_v1.LAM, a_col="noaa20_count", v_col="snpp_count")
    assert_same_ratios(series_global.cont_from(series_global.cont_sums(df)), direct)


def test_compact_broadcast_is_exact():
    df = grid_str()
    zero = df.index % 3 == 0  # many rows without any MODIS fire: identical features
    for s in ("terra", "aqua"):
        df.loc[zero, [f"{s}_count", f"{s}_nbr_count", f"{s}_fire_days"]] = 0.0
        df.loc[zero, f"{s}_no_detection"] = 1.0
        for f in ("frp_median", "frp_p75", "low_frp_share", "pixel_area_mean", "night_share"):
            df.loc[zero, f"{s}_{f}"] = np.nan
    df["lat"] = 10.125
    cfg = {**series_v1.frozen_config()["config"], "rounds": {"clf": 5, "reg": 5}}
    train = df[series_v1.ok(df, "snpp") & (df["role"] == "train")].reset_index(drop=True)
    x = series_global.as_float(harmonize.lgb_inputs(train, cfg))
    models = harmonize.refit_models(cfg, x, train["snpp_count"].to_numpy(float), cfg["rounds"])
    feats = prepare.feature_table(df)
    rep, inv = series_global.compact(feats)
    assert len(rep) < len(feats)
    direct = harmonize.models_predict(models, feats, cfg)
    assert np.array_equal(harmonize.models_predict(models, rep, cfg)[inv], direct)


def test_float_block_gives_the_same_model():
    df = grid_str()
    cfg = {**series_v1.frozen_config()["config"], "rounds": {"clf": 5, "reg": 5}}
    train = df[series_v1.ok(df, "snpp") & (df["role"] == "train")].reset_index(drop=True)
    y = train["snpp_count"].to_numpy(float)
    a = harmonize.refit_models(cfg, harmonize.lgb_inputs(train, cfg), y, cfg["rounds"])
    b = harmonize.refit_models(
        cfg, series_global.as_float(harmonize.lgb_inputs(train, cfg)), y, cfg["rounds"]
    )
    feats = prepare.feature_table(df)
    assert np.array_equal(
        harmonize.models_predict(a, feats, cfg), harmonize.models_predict(b, feats, cfg)
    )


def test_masks_are_the_v1_sources():
    df = grid_str()
    mk = series_global.masks(df)
    src = np.where(
        mk["snpp_ok"],
        "snpp",
        np.where(mk["n20_ok"], "noaa20_scaled", np.where(mk["use_terra"], "bridge", "aqua")),
    )
    s = pd.Series(src, index=pd.MultiIndex.from_frame(df[["region", "month"]]))
    ca = s.loc["california"].groupby(level=0).first()
    assert ca["2001-03"] == "bridge" and ca["2010-06"] == "aqua" and ca["2012-06"] == "aqua"
    assert ca["2015-06"] == "snpp" and ca["2026-05"] == "noaa20_scaled"
    assert set(s.loc["north_australia"]) <= {"aqua", "bridge"}


def test_global_cells():
    from harmonization import global_grid
    from harmonization.config import regions

    try:
        cells = global_grid.global_cells()
    except (OSError, SystemExit, FileNotFoundError):
        pytest.skip("needs the GFED file and counts in the data folder")
    assert not cells.duplicated(["lat_idx", "lon_idx"]).any()
    have = cells[["lat_idx", "lon_idx"]]
    for r in regions():
        b = global_grid.box_cells([r])
        got = b.merge(cells, on=["lat_idx", "lon_idx"], how="left")
        assert got["role"].notna().all()  # every box is complete
        assert (got["role"] == ("holdout" if r["role"] == "holdout" else "train")).all()
        if r["role"] == "holdout":
            assert (got["region"] == r["name"]).all()
    rc = prepare.rectangle_cells(have, role="train", sets=("demo", "gfed"))
    n_rect = prepare.rectangles()
    assert rc["rect_id"].nunique() == int((n_rect["role"] == "train").sum())
    assert set(cells.loc[cells["role"] == "train", "region"]) <= set(series_global.GFED_NAMES)
