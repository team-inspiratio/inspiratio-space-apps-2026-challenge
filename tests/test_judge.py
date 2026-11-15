"""S07 judge: predict() never sees VIIRS or year, dummy methods score sensibly, runs are
bit-identical, and the final test builds its answer key with the frozen pipeline code."""

import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harmonization import evaluate, final_test, grid, harmonize, prepare  # noqa: E402


@pytest.fixture(scope="module")
def synthetic() -> pd.DataFrame:
    """California cells, 2014-01..2021-06, V = 5 x Aqua exactly; 2016-02 Terra partial."""
    rng = np.random.default_rng(0)
    cells = grid.region_cells()
    cells = cells[cells["region"] == "california"]
    months = [m for m in grid.month_range() if "2014-01" <= m <= "2021-06"]
    df = cells.merge(pd.DataFrame({"month": months}), how="cross")
    df["lat"] = -90 + (df["lat_idx"] + 0.5) * 0.25
    df["cal_month"] = df["month"].str[5:7].astype(int)
    for f in prepare.features():
        if f not in ("lat", "cal_month"):
            df[f] = rng.random(len(df))
    df["aqua_count"] = rng.poisson(3, len(df)).astype(float)
    df["snpp_count"] = 5 * df["aqua_count"]
    df["snpp_status"] = "complete"
    df["aqua_status"] = "complete"
    df["terra_status"] = np.where(df["month"] == "2016-02", "partial", "complete")
    df["noaa20_count"] = df["snpp_count"]
    return df


def test_predict_sees_only_key_and_modis_features(synthetic):
    seen = []

    def fit(train):
        assert "snpp_count" in train  # the training table has labels
        assert train["month"].between("2016-01", "2021-06").all()

        def predict(x):
            seen.append(list(x.columns))
            return np.zeros(len(x))

        return predict

    evaluate.evaluate(fit, synthetic)
    assert len(seen) == 2
    for cols in seen:
        assert cols == prepare.KEY + prepare.features()
        assert not any(c.startswith(("snpp", "noaa20")) for c in cols)
        assert "month" not in cols and "year" not in cols and "region" not in cols


def test_partial_months_excluded(synthetic):
    train, ev = prepare.window(synthetic, "aux")
    assert "2016-02" not in set(ev.loc[ev["usable"], "month"])
    train, _ = prepare.window(synthetic, "main")
    assert "2016-02" not in set(train["month"])


def test_dummies_score_sensibly(synthetic):
    zero = evaluate.evaluate(lambda t: lambda x: np.zeros(len(x)), synthetic)
    modis = evaluate.evaluate(harmonize.fit_m0, synthetic)
    m1s = evaluate.evaluate(harmonize.fit_m1s, synthetic)
    assert m1s["combined_male"] < 1e-9  # the exact ratio is learnt
    assert m1s["combined_male"] < modis["combined_male"] < zero["combined_male"]
    assert modis["main"]["male"] == pytest.approx(np.log(5), abs=0.1)
    assert zero["main"]["total_bias_mean_abs"] == pytest.approx(1.0)
    assert m1s["main"]["n_rectangles"] == 200


def test_runs_are_bit_identical(synthetic):
    a = json.dumps(evaluate.evaluate(harmonize.fit_qm, synthetic), sort_keys=True)
    b = json.dumps(evaluate.evaluate(harmonize.fit_qm, synthetic), sort_keys=True)
    assert a == b


def test_bootstrap_diff_sign(synthetic):
    m1s = evaluate.evaluate(harmonize.fit_m1s, synthetic)
    m0 = evaluate.evaluate(harmonize.fit_m0, synthetic)
    d = evaluate.bootstrap_diff(m1s, m0)
    assert d["diff"] > 0 and d["ci95"][0] > 0 and d["se"] >= 0


def test_score_rejects_bad_estimates(synthetic):
    _, ev = prepare.window(synthetic, "main")
    rc = prepare.rectangle_cells(ev[prepare.KEY].drop_duplicates())
    with pytest.raises(ValueError):
        evaluate.score(ev, -np.ones(len(ev)), rc, prepare.LABEL)
    with pytest.raises(ValueError):
        evaluate.score(ev, np.zeros(3), rc, prepare.LABEL)


def fake_zip(path: Path, rows: list[dict]) -> None:
    cols = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,"
        "confidence,version,bright_ti5,frp,daynight,type"
    )
    buf = io.StringIO()
    buf.write(cols + "\n")
    for r in rows:
        buf.write(
            f"{r['lat']},{r['lon']},330,0.4,0.4,{r['date']},{r['time']},N,VIIRS,"
            f"{r.get('conf', 'n')},2,290,5.0,D,{r.get('type', 0)}\n"
        )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("viirs-snpp_2016_Somewhere.csv", buf.getvalue())


def test_final_test_answer_key_and_grade(tmp_path):
    # 12 detections in one California cell (one low confidence, one duplicate), 3 in one
    # north Australia cell; everything else is a recorded zero.
    rows = [
        {"lat": 36.1 + 0.001 * k, "lon": -119.9, "date": "2013-07-15", "time": 1000 + k}
        for k in range(10)
    ]
    rows += [{"lat": 36.1, "lon": -119.9, "date": "2013-07-15", "time": 1000}]  # duplicate
    rows += [{"lat": 36.2, "lon": -119.9, "date": "2013-07-16", "time": 900, "conf": "l"}]
    rows += [{"lat": -15.1, "lon": 130.1, "date": "2016-08-10", "time": 400 + k} for k in range(3)]
    fake_zip(tmp_path / "a.zip", rows)
    key = final_test.answer_key(tmp_path)
    i, j = grid.cell_index(np.array([36.1, -15.1]), np.array([-119.9, 130.1]))
    ca = key[(key.lat_idx == i[0]) & (key.lon_idx == j[0]) & (key.month == "2013-07")]
    au = key[(key.lat_idx == i[1]) & (key.lon_idx == j[1]) & (key.month == "2016-08")]
    assert ca["snpp_count"].item() == 10 and au["snpp_count"].item() == 3
    assert ca["snpp_status"].item() == "complete"  # the dev-side "locked" flag is resolved
    assert key["snpp_count"].sum() == 13

    sub = key[prepare.KEY + ["month"]].copy()
    sub["est_final"] = key["snpp_count"].fillna(0).to_numpy()
    sub["est_m1s"] = 0.0
    res = final_test.grade(sub, key)
    s1 = res["test1"]["scores"]
    assert s1["est_final"]["male"] == 0.0
    assert s1["est_m1s"]["male"] > 0
    assert res["test1"]["differences"]["est_final_vs_est_m1s"]["diff"] > 0
    assert res["test2"]["scores"]["est_final"]["male_all"] == 0.0
    with pytest.raises(SystemExit):
        final_test.grade(sub.iloc[:-5000], key)  # an incomplete submission is refused


def test_kappa():
    a = np.array([0, 1, 2, 1, 1])
    k, cm = final_test.kappa(a, a)
    assert k == 1.0 and np.trace(np.array(cm)) == 5


def test_anomaly_class_mid_rank():
    ref = np.array([[1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10, np.nan]] * 3)
    cls = final_test.anomaly_class(np.array([0.0, 5.5, 11.0]), ref)
    assert cls.tolist() == [0, 1, 2]
