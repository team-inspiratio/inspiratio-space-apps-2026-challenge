"""S07 judge, part 2: score a method on the two validation windows (frozen after S07).

uv run python -m harmonization.evaluate --method m1s --param lam=20

A method is a function fit(train_table) -> predict, and predict(feature_table) -> one estimate
per row. The training table has labels; the feature table is prepare.feature_table(): cell key
and MODIS features only, never a VIIRS, month or year column (tests/test_judge.py proves it).

Metrics (docs/preregistration.md sections 2-3), all on the random rectangles of config/
rectangles.csv whose cells are all in the scored cells; rectangle value = sum of its cells:
  male         primary score: mean |ln(H+1) - ln(V+1)| over rectangle-months with V >= 10,
               first within each region x calendar year, then equal weight over those units
  male_all     the same over every usable rectangle-month (V >= 0)
  zero_ge1/5   share of rectangle-months with V = 0 where H >= 1 / H >= 5
  low_mae      mean |H - V| over rectangle-months with 1 <= V <= 9
  total_bias   sum H / sum V - 1 over all cells of a region, per region x year (absolute
               difference when sum V = 0)
  season_corr  per region, Pearson r of the 12 calendar-month means of the region totals
Missing and partial months are excluded (prepare.usable); `excluded_share` reports how many.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable

import numpy as np
import pandas as pd
from scipy import sparse

from harmonization import prepare
from harmonization.config import settings

Predict = Callable[[pd.DataFrame], np.ndarray]
Fit = Callable[[pd.DataFrame], Predict]


def rect_month_sums(
    table: pd.DataFrame, est: np.ndarray, label: str, rect_cells: pd.DataFrame
) -> pd.DataFrame:
    """Rectangle x month sums of the estimate H and the label V over usable cell-months."""
    t = table.assign(_h=est)
    t = t[t["usable"].to_numpy()]
    cells = t[prepare.KEY].drop_duplicates().sort_values(prepare.KEY).reset_index(drop=True)
    cells["_c"] = np.arange(len(cells))
    t = t.merge(cells, on=prepare.KEY, how="left")
    months = np.sort(t["month"].unique())
    m_idx = np.searchsorted(months, t["month"].to_numpy())
    shape = (len(cells), len(months))
    h = sparse.csr_matrix((t["_h"].to_numpy(float), (t["_c"].to_numpy(), m_idx)), shape=shape)
    v = sparse.csr_matrix((t[label].to_numpy(float), (t["_c"].to_numpy(), m_idx)), shape=shape)
    rc = rect_cells.merge(cells, on=prepare.KEY, how="inner")
    rects = rc[["rect_id", "rect_region"]].drop_duplicates().sort_values("rect_id")
    r_idx = np.searchsorted(rects["rect_id"].to_numpy(), rc["rect_id"].to_numpy())
    member = sparse.csr_matrix(
        (np.ones(len(rc)), (r_idx, rc["_c"].to_numpy())), shape=(len(rects), len(cells))
    )
    hs, vs = (member @ h).toarray(), (member @ v).toarray()
    return pd.DataFrame(
        {
            "rect_id": np.repeat(rects["rect_id"].to_numpy(), len(months)),
            "region": np.repeat(rects["rect_region"].to_numpy(), len(months)),
            "month": np.tile(months, len(rects)),
            "H": hs.ravel(),
            "V": vs.ravel(),
        }
    )


def unit_male(rm: pd.DataFrame) -> pd.DataFrame:
    """MALE per region x calendar year unit (preregistration section 2)."""
    err = np.abs(np.log1p(rm["H"].to_numpy()) - np.log1p(rm["V"].to_numpy()))
    d = rm.assign(err=err, year=rm["month"].str[:4])
    g = d.groupby(["region", "year"], sort=True)["err"]
    return pd.DataFrame({"male": g.mean(), "n": g.size()}).reset_index()


def region_totals(table: pd.DataFrame, est: np.ndarray, label: str) -> pd.DataFrame:
    t = table.assign(H=est, V=table[label])[table["usable"].to_numpy()]
    return t.groupby(["region", "month"], sort=True)[["H", "V"]].sum().reset_index()


def score(table: pd.DataFrame, est: np.ndarray, rect_cells: pd.DataFrame, label: str) -> dict:
    """All metrics for one window. `table` has KEY, region, month, `label` and `usable`."""
    est = np.asarray(est, dtype=float)
    if est.shape != (len(table),):
        raise ValueError(f"expected {len(table)} estimates, got shape {est.shape}")
    ok = table["usable"].to_numpy()
    if not np.isfinite(est[ok]).all() or (est[ok] < 0).any():
        raise ValueError("estimates must be finite and non-negative on usable rows")
    est = np.where(ok, est, 0.0)
    min_v = settings()["scoring"]["male_min_viirs"]
    rm = rect_month_sums(table, est, label, rect_cells)
    all_months = table["month"].nunique()
    used_months = table.loc[ok, "month"].nunique()
    units = unit_male(rm[rm["V"] >= min_v])
    units_all = unit_male(rm)
    v, h = rm["V"].to_numpy(), rm["H"].to_numpy()
    zero, low = v == 0, (v >= 1) & (v <= 9)

    tot = region_totals(table, est, label)
    year_tot = tot.assign(year=tot["month"].str[:4]).groupby(["region", "year"])[["H", "V"]].sum()
    year_tot["bias"] = np.where(
        year_tot["V"] > 0, year_tot["H"] / year_tot["V"].where(year_tot["V"] > 0) - 1, np.nan
    )
    year_tot["abs_diff_if_v0"] = np.where(year_tot["V"] > 0, np.nan, year_tot["H"] - year_tot["V"])
    season = {}
    for region, g in tot.assign(cal=tot["month"].str[5:7]).groupby("region"):
        curve = g.groupby("cal")[["H", "V"]].mean()
        ok_curve = len(curve) >= 3 and curve["H"].std() > 0 and curve["V"].std() > 0
        season[region] = float(np.corrcoef(curve["H"], curve["V"])[0, 1]) if ok_curve else None
    by_region = units.groupby("region")["male"].mean()
    return {
        "male": float(units["male"].mean()) if len(units) else None,
        "male_all": float(units_all["male"].mean()) if len(units_all) else None,
        "n_primary": int((v >= min_v).sum()),
        "n_all": int(len(rm)),
        "n_rectangles": int(rm["rect_id"].nunique()),
        "excluded_share": float(1 - used_months / all_months) if all_months else None,
        "zero_ge1": float((h[zero] >= 1).mean()) if zero.any() else None,
        "zero_ge5": float((h[zero] >= 5).mean()) if zero.any() else None,
        "low_mae": float(np.abs(h[low] - v[low]).mean()) if low.any() else None,
        "total_bias_mean_abs": float(np.nanmean(np.abs(year_tot["bias"])))
        if year_tot["bias"].notna().any()
        else None,
        "season_corr_mean": float(np.mean([s for s in season.values() if s is not None]))
        if any(s is not None for s in season.values())
        else None,
        "male_by_region": {k: float(x) for k, x in by_region.items()},
        "season_corr": season,
        "total_bias": [
            {
                "region": r,
                "year": y,
                "H": float(row.H),
                "V": float(row.V),
                "bias": None if np.isnan(row.bias) else float(row.bias),
                "abs_diff_if_v0": None
                if np.isnan(row.abs_diff_if_v0)
                else float(row.abs_diff_if_v0),
            }
            for (r, y), row in year_tot.iterrows()
        ],
        "units": units.to_dict(orient="records"),
    }


def evaluate(
    fit: Fit,
    df: pd.DataFrame | None = None,
    windows=tuple(prepare.WINDOWS),
    rect_sets: tuple[str, ...] = ("demo",),
) -> dict:
    """Fit and score a method on each validation window; `combined` = equal-weight mean MALE."""
    df = prepare.load_grid() if df is None else df
    cells = df.loc[df["role"] == "train", prepare.KEY].drop_duplicates()
    rect_cells = prepare.rectangle_cells(cells, sets=rect_sets)
    out: dict = {}
    for name in windows:
        train, ev = prepare.window(df, name)
        predict = fit(train.copy())
        rows = ev[ev["usable"].to_numpy()].reset_index(drop=True)
        est = np.asarray(predict(prepare.feature_table(rows)), dtype=float)
        out[name] = score(rows, est, rect_cells, prepare.LABEL)
        out[name]["excluded_share"] = float(1 - rows["month"].nunique() / ev["month"].nunique())
    males = [out[w]["male"] for w in windows]
    out["combined_male"] = float(np.mean(males)) if None not in males else None
    return out


def bootstrap_diff(a: dict, b: dict, windows=tuple(prepare.WINDOWS)) -> dict:
    """Block bootstrap of MALE(b) - MALE(a) over region x year units, windows weighted equally.

    Positive values mean `a` is better. 2000 resamples with replacement of the units of each
    window, seed seeds.bootstrap (preregistration section 3). No p-values.
    """
    rng = np.random.default_rng(settings()["seeds"]["bootstrap"])
    reps = 2000
    point, draws = [], np.zeros((reps, len(windows)))
    for k, w in enumerate(windows):
        cols = ["region", "year", "male", "n"]
        ua = pd.DataFrame(a[w]["units"], columns=cols).set_index(["region", "year"])["male"]
        ub = pd.DataFrame(b[w]["units"], columns=cols).set_index(["region", "year"])["male"]
        ua, ub = ua.align(ub, join="inner")
        if ua.empty:
            return {"diff": None, "se": None, "ci95": None, "resamples": reps}
        d = (ub - ua).to_numpy()
        point.append(d.mean())
        idx = rng.integers(0, len(d), size=(reps, len(d)))
        draws[:, k] = d[idx].mean(axis=1)
    comb = draws.mean(axis=1)
    return {
        "diff": float(np.mean(point)),
        "se": float(comb.std(ddof=1)),
        "ci95": [float(np.percentile(comb, 2.5)), float(np.percentile(comb, 97.5))],
        "resamples": reps,
    }


def main() -> int:
    from harmonization import harmonize

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--method", default="m1s", choices=sorted(harmonize.METHODS))
    p.add_argument("--param", action="append", default=[], help="key=value, e.g. lam=20")
    args = p.parse_args()
    params = {k: float(v) for k, v in (x.split("=", 1) for x in args.param)}
    res = evaluate(lambda t: harmonize.METHODS[args.method](t, **params))
    for w in prepare.WINDOWS:
        res[w].pop("units")
        res[w].pop("total_bias")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
