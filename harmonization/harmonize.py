"""S08 baselines: M0, M1s and QM. The only file the S10 AI experiments may change (plan section 5).

Every method is fit(train_table, **params) -> predict, and predict(feature_table) returns one
VIIRS-scale estimate per row. predict() only ever gets prepare.feature_table(): the cell key
(lat_idx, lon_idx) and the MODIS features of config/features.json. The training table also has
`region`, `month` and the S-NPP label `snpp_count`; they are used for fitting only.

  M0   direct splice: H = Aqua count (what you get by joining MODIS before 2012 to VIIRS after)
  M1s  shrunk ratio (proposal "候选模型"): H = k[g, c] * A with
           k[g, c] = (sum_y V[g, c, y] + lam * k[R, c]) / (sum_y A[g, c, y] + lam)
       g cell, c calendar month, R the cell's training region; cells not seen in training (new
       regions) get the ratio pooled over all training regions for that calendar month
  QM   empirical quantile mapping per calendar month, pooled over the training regions:
       H = F_V^-1(F_A(A)) with mid-ranks for ties (docs/decisions/0005)
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

A, V = "aqua_count", "snpp_count"
KEY = ["lat_idx", "lon_idx"]
Predict = Callable[[pd.DataFrame], np.ndarray]


def ratio(v, a):
    """sum V / sum A, NaN when there is no MODIS detection to divide by."""
    if np.isscalar(a):
        return v / a if a > 0 else np.nan
    return v / a.where(a > 0)


def fit_m0(train: pd.DataFrame) -> Predict:
    def predict(x: pd.DataFrame) -> np.ndarray:
        return x[A].to_numpy(float)

    return predict


def m1s_ratios(train: pd.DataFrame, lam: float, a_col: str = A, v_col: str = V) -> dict:
    """Ratio tables of M1s. Fallbacks when a denominator is 0 (recorded in `fallbacks`):
    region x calendar month -> region (all months) -> all training regions (all months)."""
    t = train[KEY + ["region", "cal_month", a_col, v_col]]
    glob = ratio(float(t[v_col].sum()), float(t[a_col].sum()))
    reg = t.groupby("region")[[v_col, a_col]].sum()
    k_r = ratio(reg[v_col], reg[a_col]).fillna(glob)
    rc = t.groupby(["region", "cal_month"])[[v_col, a_col]].sum()
    k_rc = ratio(rc[v_col], rc[a_col])
    fallbacks = {"region_month_to_region": int(k_rc.isna().sum())}
    k_rc = k_rc.fillna(pd.Series(rc.index.get_level_values("region").map(k_r), index=rc.index))
    pooled = t.groupby("cal_month")[[v_col, a_col]].sum()
    k_c = ratio(pooled[v_col], pooled[a_col])
    fallbacks["pooled_month_to_global"] = int(k_c.isna().sum())
    k_c = k_c.fillna(glob).reindex(range(1, 13)).fillna(glob)
    gc = t.groupby(KEY + ["region", "cal_month"])[[v_col, a_col]].sum().reset_index()
    prior = k_rc.reindex(pd.MultiIndex.from_frame(gc[["region", "cal_month"]])).to_numpy()
    num = gc[v_col].to_numpy() + lam * prior
    den = gc[a_col].to_numpy() + lam
    k_g = np.where(den > 0, num / np.where(den > 0, den, 1), prior)
    fallbacks["cell_month_to_region_month"] = int((den <= 0).sum())
    cell = gc[KEY + ["cal_month"]].assign(k=k_g)
    return {"cell": cell, "pooled": k_c, "region_month": k_rc, "fallbacks": fallbacks}


def apply_ratios(r: dict, x: pd.DataFrame, a_col: str = A) -> np.ndarray:
    k = x[KEY + ["cal_month"]].merge(r["cell"], on=KEY + ["cal_month"], how="left")["k"]
    k = k.fillna(x["cal_month"].map(r["pooled"]).reset_index(drop=True)).to_numpy(float)
    return k * x[a_col].to_numpy(float)


def fit_m1s(train: pd.DataFrame, lam: float = 20.0) -> Predict:
    r = m1s_ratios(train, lam)

    def predict(x: pd.DataFrame) -> np.ndarray:
        return apply_ratios(r, x.reset_index(drop=True))

    predict.ratios = r  # type: ignore[attr-defined]
    return predict


def quantile_map(a_train: np.ndarray, v_train: np.ndarray, a: np.ndarray) -> np.ndarray:
    """F_V^-1(F_A(a)) with mid-rank F_A; above the training maximum of A, scale the top
    quantile of V by a / max(A) (multiplicative extrapolation)."""
    a_sorted, v_sorted = np.sort(a_train), np.sort(v_train)
    n = len(a_sorted)
    below = np.searchsorted(a_sorted, a, side="left")
    upto = np.searchsorted(a_sorted, a, side="right")
    p = (below + 0.5 * (upto - below)) / n
    h = np.quantile(v_sorted, np.clip(p, 0, 1))
    top = a_sorted[-1]
    over = a > top
    if over.any() and top > 0:
        h[over] = v_sorted[-1] * a[over] / top
    return h


def fit_qm(train: pd.DataFrame) -> Predict:
    groups = {
        c: (g[A].to_numpy(float), g[V].to_numpy(float)) for c, g in train.groupby("cal_month")
    }
    pooled = (train[A].to_numpy(float), train[V].to_numpy(float))

    def predict(x: pd.DataFrame) -> np.ndarray:
        out = np.full(len(x), np.nan)
        cal = x["cal_month"].to_numpy()
        a = x[A].to_numpy(float)
        for c in np.unique(cal):
            m = cal == c
            a_tr, v_tr = groups.get(int(c), pooled)
            out[m] = quantile_map(a_tr, v_tr, a[m])
        return out

    return predict


METHODS: dict[str, Callable[..., Predict]] = {"m0": fit_m0, "m1s": fit_m1s, "qm": fit_qm}
LAMBDAS = (0.0, 5.0, 20.0, 50.0, 100.0)  # M1s grid, chosen on the validation windows (S08)


def fit(train: pd.DataFrame) -> Predict:
    """Current default method (S08: M1s; S10 may replace it)."""
    return fit_m1s(train)
