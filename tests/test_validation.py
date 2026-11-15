"""S13 era-shift classifier (harmonization.validation.drift_fit) on synthetic rows: it must see a
planted shift, report about 0.5 when there is none, and never use anything but model inputs."""

import numpy as np
import pandas as pd

from harmonization import prepare, validation


def rows(shift: float, n_per_year: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    years = [str(y) for y in [*range(2003, 2012), *range(2014, 2022)]]
    parts = []
    for y in years:
        new = int(y) >= 2014
        d = {c: rng.random(n_per_year) for c in prepare.features()}
        d["aqua_count"] = rng.poisson(5 + (shift if new else 0), n_per_year).astype(float)
        d["lat_idx"] = rng.integers(0, 720, n_per_year)
        d["lon_idx"] = rng.integers(0, 1440, n_per_year)
        d["region"] = np.where(rng.random(n_per_year) < 0.5, "a", "b")
        d["year"] = y
        d["era_new"] = int(new)
        parts.append(pd.DataFrame(d))
    return pd.concat(parts, ignore_index=True)


def test_drift_sees_a_planted_shift():
    res = validation.drift_fit(rows(shift=6.0), validation.frozen_cfg())
    assert res["auc"] > 0.8
    assert set(res["auc_by_region"]) == {"a", "b"}
    assert len(res["auc_by_fold"]) == 5
    assert max(res["single_feature_auc"], key=res["single_feature_auc"].get) == "aqua_count"


def test_drift_reports_chance_without_a_shift():
    res = validation.drift_fit(rows(shift=0.0), validation.frozen_cfg())
    assert 0.4 < res["auc"] < 0.6


def test_drift_uses_model_inputs_only():
    res = validation.drift_fit(rows(shift=0.0), validation.frozen_cfg())
    used = set(res["gain_share_pct"])
    assert used <= set(prepare.features())
    assert not used & {"lat_idx", "lon_idx", "year", "region", "era_new"}
