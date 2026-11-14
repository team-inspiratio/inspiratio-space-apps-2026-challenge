"""S01 pre-registration: regions, holdout lock, scoring rectangles and settings stay consistent."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import guardrails  # noqa: E402

from harmonization.config import regions, settings  # noqa: E402


def overlap(a, b):
    return (
        a["west"] <= b["east"]
        and b["west"] <= a["east"]
        and (a["south"] <= b["north"] and b["south"] <= a["north"])
    )


def test_regions_on_grid_and_disjoint():
    regs = regions()
    assert {r["role"] for r in regs} == {"train", "holdout"}
    assert len([r for r in regs if r["role"] == "holdout"]) == 3
    for r in regs:
        for k in ("west", "south", "east", "north"):
            assert (r[k] / 0.25).is_integer()
        assert 5 <= r["east"] - r["west"] <= 10.5 and 5 <= r["north"] - r["south"] <= 10.5
    train = [r for r in regs if r["role"] == "train"]
    holdout = [r for r in regs if r["role"] == "holdout"]
    assert not any(overlap(t, h) for t in train for h in holdout)


def test_in_holdout_scalars_and_arrays():
    assert guardrails.in_holdout(-15.0, 130.0)  # Top End, Australia
    assert guardrails.in_holdout(60.0, 100.0)  # central Siberia
    assert guardrails.in_holdout(30.0, 76.0)  # Punjab
    assert guardrails.in_holdout(-10.0, 125.0)  # box corner counts as holdout
    assert not guardrails.in_holdout(36.0, -120.0)  # California
    lat = np.array([-15.0, 36.0, 60.0, 0.0])
    lon = np.array([130.0, -120.0, 100.0, 0.0])
    assert guardrails.in_holdout(lat, lon).tolist() == [True, False, True, False]


def test_rectangles():
    rect = pd.read_csv(ROOT / "config" / "rectangles.csv")
    sc = settings()["scoring"]
    assert rect["rect_id"].is_unique
    assert rect["side_deg"].between(sc["rect_side_deg"]["min"], sc["rect_side_deg"]["max"]).all()
    assert np.allclose(rect["east"] - rect["west"], rect["north"] - rect["south"])
    assert ((rect[["west", "south", "east", "north"]] / 0.25) % 1 == 0).all().all()
    demo = rect[rect["set"] == "demo"]
    assert (demo.groupby("region").size() == sc["rect_per_demo_region"]).all()
    for r in regions():
        mine = demo[demo["region"] == r["name"]]
        assert (mine["role"] == r["role"]).all()
        assert (mine["west"] >= r["west"]).all() and (mine["east"] <= r["east"]).all()
        assert (mine["south"] >= r["south"]).all() and (mine["north"] <= r["north"]).all()
    gfed = rect[rect["set"] == "gfed"]
    assert gfed["region"].nunique() == 14
    assert (gfed.groupby("region").size() == sc["rect_per_gfed_region"]).all()
    holdouts = [r for r in regions() if r["role"] == "holdout"]
    for row in gfed.itertuples():
        assert not any(overlap(row._asdict(), h) for h in holdouts)


def test_splits_match_plan():
    s = settings()["splits"]
    assert s["train"] == {"start": "2016-01", "end": "2021-06"}
    assert s["validation"] == {"start": "2014-01", "end": "2015-12"}
    assert s["aux_train"] == {"start": "2018-01", "end": "2021-06"}
    assert s["aux_validation"] == {"start": "2016-01", "end": "2017-12"}
    assert s["test1"]["start"] == "2012-02" and s["test1"]["end"] == "2013-12"
    assert s["test2"]["end"] == "2021-06"
    assert s["locked_snpp_years"] == [2012, 2013]
