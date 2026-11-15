"""S03-S05: holdout drop at import, cleaning rules, gridding and count conservation."""

import datetime as dt
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harmonization import clean, grid, ingest  # noqa: E402


def frame(**cols):
    n = len(next(iter(cols.values())))
    base = {
        "sensor": ["aqua"] * n,
        "product": ["SP"] * n,
        "latitude": [36.0] * n,
        "longitude": [-120.0] * n,
        "acq_date": [dt.date(2016, 7, 1)] * n,
        "acq_time": [1330] * n,
        "confidence": ["80"] * n,
        "frp": [12.0] * n,
        "scan": [1.0] * n,
        "track": [1.0] * n,
        "daynight": ["D"] * n,
        "type": [0] * n,
    }
    base.update(cols)
    return pd.DataFrame(base)


def test_holdout_viirs_dropped_modis_kept():
    df = frame(
        sensor=["snpp", "aqua", "snpp", "noaa20"],
        latitude=[-15.0, -15.0, 36.0, 30.0],
        longitude=[130.0, 130.0, -120.0, 76.0],
    )
    kept, dropped = ingest.drop_holdout_viirs(df)
    assert dropped == 2
    assert kept["sensor"].tolist() == ["aqua", "snpp"]


def test_cleaning_rules_in_order():
    df = frame(
        product=["NRT", "SP", "SP", "SP", "SP", "NRT"],
        latitude=[36.0, 36.0, 36.1, 36.2, 36.3, 40.0],
        type=[-1, 0, 2, 0, 0, -1],
        confidence=["80", "80", "80", "10", "30", "80"],
    )
    mask = {int(clean.mask_key(np.array([40.0]), np.array([-120.0]), 0.01)[0])}
    kept, counts, removed = clean.clean(df, mask)
    assert counts["removed_duplicate"] == 1  # the NRT copy of the first SP record
    assert counts["removed_type"] == 1
    assert counts["removed_nrt_static_mask"] == 1
    assert counts["removed_confidence"] == 1  # confidence 10 < 30; 30 is kept
    assert counts["rows_out"] == 2 and (kept["product"] == "SP").all()
    assert len(removed) == 4


def test_viirs_confidence():
    df = frame(sensor=["snpp"] * 3, confidence=["l", "n", "h"], latitude=[1.0, 2.0, 3.0])
    kept, counts, _ = clean.clean(df, set())
    assert counts["removed_confidence"] == 1 and sorted(kept["confidence"]) == ["h", "n"]


def test_cell_index_edges():
    i, j = grid.cell_index(np.array([-90.0, 0.0, 0.24, 90.0]), np.array([-180.0, 0.0, 0.25, 180.0]))
    assert i.tolist() == [0, 360, 360, 719]
    assert j.tolist() == [0, 720, 721, 1439]


def test_aggregate_conserves_counts():
    rng = np.random.default_rng(0)
    n = 5000
    pts = pd.DataFrame(
        {
            "latitude": rng.uniform(-30, -10, n),
            "longitude": rng.uniform(20, 35, n),
            "acq_date": pd.to_datetime("2016-01-01")
            + pd.to_timedelta(rng.integers(0, 366, n), "D"),
            "daynight": rng.choice(["D", "N"], n),
            "frp": rng.gamma(2, 10, n),
            "scan": rng.uniform(1, 2, n),
            "track": rng.uniform(1, 2, n),
        }
    )
    agg = grid.aggregate(pts, modis=True)
    assert agg["count"].sum() == n
    assert (agg["count_day"] + agg["count_night"] == agg["count"]).all()
    assert (agg["fire_days"] <= agg["count"]).all()
    assert agg["low_frp_share"].between(0, 1).all()


def test_neighbour_counts_wrap_longitude():
    counts = pd.DataFrame(
        {"lat_idx": [100, 100], "lon_idx": [0, 1439], "month": ["2016-01"] * 2, "count": [3, 5]}
    )
    cells = pd.DataFrame({"lat_idx": [100], "lon_idx": [0]})
    nbr = grid.neighbour_counts(counts, cells)
    assert nbr.loc[(nbr["lat_idx"] == 100) & (nbr["lon_idx"] == 0), "nbr_count"].item() == 5


def processed():
    data = os.environ.get("INSPIRATIO_DATA_DIR")
    path = Path(data) / "processed" / "grid" / "counts.parquet" if data else None
    return path if path and path.exists() else None


@pytest.mark.skipif(processed() is None, reason="needs the processed data (S05)")
def test_grid_total_equals_clean_total():
    counts = pd.read_parquet(processed(), columns=["sensor", "count"])
    clean_counts = pd.read_csv(ROOT / "docs" / "cleaning-counts.csv")
    expected = clean_counts.groupby("sensor")["rows_out"].sum()
    got = counts.groupby("sensor")["count"].sum()
    assert got.to_dict() == expected.to_dict()


@pytest.mark.skipif(processed() is None, reason="needs the processed data (S05)")
def test_dense_regions_zero_vs_missing():
    dense = pd.read_parquet(processed().with_name("regions.parquet"))
    hold = dense["role"] == "holdout"
    assert dense.loc[hold, ["snpp_count", "noaa20_count"]].isna().all().all()
    locked = dense["snpp_status"] == "locked"
    assert dense.loc[locked, "snpp_count"].isna().all()
    ok = dense["aqua_status"] == "complete"
    assert dense.loc[ok, "aqua_count"].notna().all()
