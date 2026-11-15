"""Harmonization methods: M0, M1s, QM (S08) and LightGBM M3 (S10). The only file the S10 AI
experiments may change (plan section 5).

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
  LGB  LightGBM on the MODIS features of config/features.json only (never the cell key, year,
       region or any VIIRS column): count objective (Tweedie or Poisson), monotone increasing
       in the MODIS counts, shallow trees with large leaves, deterministic, fixed seed. The
       number of rounds is chosen inside the training table on its earliest months (same
       direction as the backcast), then the model is refitted on the whole training table.
       Optional Optuna search of numeric parameters uses that same inner split, never the
       validation windows (docs/decisions/0006).
"""

from __future__ import annotations

from collections.abc import Callable

import lightgbm as lgb
import numpy as np
import pandas as pd

from harmonization import evaluate, prepare
from harmonization.config import settings

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


# --- LightGBM (M3) -------------------------------------------------------------------------
# Structural choices live in LGB; the S10 experiment loop edits them (and the code below).
LGB: dict = {
    "objective": "tweedie",  # "tweedie" | "poisson"
    "variance_power": 1.3,
    "num_leaves": 31,
    "min_data_in_leaf": 50,
    "learning_rate": 0.05,
    "lambda_l2": 0.0,
    "feature_fraction": 1.0,
    "max_rounds": 3000,
    "early_stopping": 100,
    "inner_months": 24,  # earliest training months held out to choose the number of rounds
    "monotone": ("aqua_count", "terra_count"),  # increasing constraint (plan section 2)
    "drop": (
        "terra_no_detection",
        "aqua_no_detection",
    ),  # features of config/features.json left out
    "derived": (),  # extra inputs computed from the features only (DERIVED)
    "optuna_trials": 15,  # 0 = fixed parameters above
    "zero_rule": "cell_and_nbr",  # None | "cell" | "cell_and_nbr": estimate 0 without MODIS fire
    "zero_floor": 0.0,  # in cells without MODIS fire, estimates below this become 0
    "own0_scale": 1.0,  # estimates in cells without MODIS fire are multiplied by this first
    "two_stage": True,  # classifier "any VIIRS fire?" then a count model on fire cells
    "p_fire": 0.5,  # two-stage: cells with P(fire) below this get 0
}
THREADS = 8  # fixed: LightGBM results depend on the thread count (docs/decisions/0006)

DERIVED: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "modis_count": lambda x: x["aqua_count"] + x["terra_count"],
    "log_aqua": lambda x: np.log1p(x["aqua_count"]),
    "nbr_total": lambda x: x["aqua_nbr_count"] + x["terra_nbr_count"],
    "fire_days_max": lambda x: np.maximum(x["aqua_fire_days"], x["terra_fire_days"]),
}
MONOTONE_DERIVED = ("modis_count", "log_aqua")


def lgb_inputs(x: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Model inputs: the allowed features minus `drop`, plus derived ones. Never the cell key."""
    feats = prepare.feature_table(x).drop(columns=prepare.KEY)
    for name in cfg["derived"]:
        feats[name] = DERIVED[name](feats)
    return feats.drop(columns=list(cfg["drop"]))


def zero_mask(x: pd.DataFrame, rule: str | None) -> np.ndarray:
    """Rows forced to 0: no MODIS detection in the cell (and, for cell_and_nbr, its neighbours)."""
    if rule is None:
        return np.zeros(len(x), bool)
    m = (x["aqua_count"] == 0).to_numpy() & (x["terra_count"] == 0).to_numpy()
    if rule == "cell_and_nbr":
        m &= (x["aqua_nbr_count"] == 0).to_numpy() & (x["terra_nbr_count"] == 0).to_numpy()
    return m


def lgb_predict(booster: lgb.Booster, x: pd.DataFrame, cfg: dict, n: int | None = None):
    est = booster.predict(lgb_inputs(x, cfg), num_iteration=n)
    est = np.where(zero_mask(x, cfg["zero_rule"]), 0.0, est)
    own0 = zero_mask(x, "cell")
    est = np.where(own0, cfg["own0_scale"] * est, est)
    return np.where(own0 & (est < cfg["zero_floor"]), 0.0, est)


def lgb_params(cfg: dict, cols: list[str]) -> dict:
    mono = set(cfg["monotone"]) | set(MONOTONE_DERIVED)
    p = {
        "objective": cfg["objective"],
        "num_leaves": int(cfg["num_leaves"]),
        "min_data_in_leaf": int(cfg["min_data_in_leaf"]),
        "learning_rate": cfg["learning_rate"],
        "lambda_l2": cfg["lambda_l2"],
        "feature_fraction": cfg["feature_fraction"],
        "feature_fraction_seed": settings()["seeds"]["lightgbm"],
        "monotone_constraints": [1 if c in mono else 0 for c in cols],
        "monotone_constraints_method": "advanced",
        "deterministic": True,
        "force_col_wise": True,
        "seed": settings()["seeds"]["lightgbm"],
        "num_threads": THREADS,
        "verbose": -1,
    }
    if cfg["objective"] == "tweedie":
        p["tweedie_variance_power"] = cfg["variance_power"]
    return p


def inner_split(train: pd.DataFrame, months: int) -> tuple[np.ndarray, np.ndarray]:
    """(fit rows, held-out rows): hold out the earliest `months` training months (backcast)."""
    ms = np.sort(train["month"].unique())
    held = train["month"].isin(ms[:months]).to_numpy()
    return ~held, held


def lgb_rounds(cfg: dict, x: pd.DataFrame, y: np.ndarray, fit_rows, held_rows) -> lgb.Booster:
    params = lgb_params(cfg, list(x.columns))
    d_fit = lgb.Dataset(x[fit_rows], y[fit_rows], free_raw_data=False)
    d_held = lgb.Dataset(x[held_rows], y[held_rows], reference=d_fit, free_raw_data=False)
    return lgb.train(
        params,
        d_fit,
        num_boost_round=int(cfg["max_rounds"]),
        valid_sets=[d_held],
        callbacks=[lgb.early_stopping(int(cfg["early_stopping"]), verbose=False)],
    )


def fit_models(cfg: dict, x: pd.DataFrame, y: np.ndarray, fit_rows, held_rows) -> dict:
    """Boosters early-stopped on the inner split. Two-stage: a binary classifier for V > 0 and
    a count model fitted on the cell-months with V > 0 only."""
    if not cfg["two_stage"]:
        return {"reg": lgb_rounds(cfg, x, y, fit_rows, held_rows)}
    pos = y > 0
    clf = lgb_rounds({**cfg, "objective": "binary"}, x, pos.astype(float), fit_rows, held_rows)
    reg = lgb_rounds(cfg, x, y, fit_rows & pos, held_rows & pos)
    return {"clf": clf, "reg": reg}


def refit_models(cfg: dict, x: pd.DataFrame, y: np.ndarray, rounds: dict) -> dict:
    """Refit on the whole training table with the inner-split numbers of rounds."""
    if not cfg["two_stage"]:
        return {
            "reg": lgb.train(lgb_params(cfg, list(x.columns)), lgb.Dataset(x, y), rounds["reg"])
        }
    pos = y > 0
    clf_params = lgb_params({**cfg, "objective": "binary"}, list(x.columns))
    clf = lgb.train(clf_params, lgb.Dataset(x, pos.astype(float)), rounds["clf"])
    reg = lgb.train(lgb_params(cfg, list(x.columns)), lgb.Dataset(x[pos], y[pos]), rounds["reg"])
    return {"clf": clf, "reg": reg}


def models_predict(models: dict, x: pd.DataFrame, cfg: dict) -> np.ndarray:
    """Estimates; early-stopped boosters predict with their best iteration."""
    if "clf" not in models:
        return lgb_predict(models["reg"], x, cfg)
    feats = lgb_inputs(x, cfg)
    p_fire = models["clf"].predict(feats)
    return np.where(p_fire >= cfg["p_fire"], models["reg"].predict(feats), 0.0)


def inner_score(train: pd.DataFrame, held_rows: np.ndarray, est: np.ndarray) -> dict:
    """Frozen judge metrics on the held-out training months (training labels only)."""
    t = train[held_rows].reset_index(drop=True).assign(usable=True)
    rect = prepare.rectangle_cells(t[prepare.KEY].drop_duplicates())
    return evaluate.score(t, est, rect, prepare.LABEL)


def inner_objective(s: dict, ref: dict) -> float:
    """Inner MALE, penalised by how far the preregistered guardrails (section 4 items 3-4) are
    exceeded against M1s fitted on the same inner split."""
    excess = (
        max(0.0, s["zero_ge1"] - ref["zero_ge1"] - 0.05)
        + max(0.0, s["zero_ge5"] - ref["zero_ge5"] - 0.02)
        + max(0.0, s["low_mae"] / ref["low_mae"] - 1.10)
        + sum(max(0.0, m / ref["male_by_region"][r] - 1.05) for r, m in s["male_by_region"].items())
    )
    return s["male"] + (1.0 + 10.0 * excess if excess > 0 else 0.0)


def tune(cfg: dict, train, x, y, fit_rows, held_rows) -> dict:
    """Optuna search of the numeric parameters on the inner split (seeded, sequential)."""
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    held = train[held_rows].reset_index(drop=True)
    m1s = fit_m1s(train[fit_rows].reset_index(drop=True), 20.0)
    ref = inner_score(train, held_rows, m1s(prepare.feature_table(held)))

    def objective(trial: optuna.Trial) -> float:
        c = dict(cfg)
        c["num_leaves"] = trial.suggest_int("num_leaves", 15, 31)
        c["min_data_in_leaf"] = trial.suggest_int("min_data_in_leaf", 50, 500, log=True)
        c["lambda_l2"] = trial.suggest_float("lambda_l2", 1e-3, 30.0, log=True)
        c["feature_fraction"] = trial.suggest_float("feature_fraction", 0.5, 1.0)
        if c["objective"] == "tweedie":
            c["variance_power"] = trial.suggest_float("variance_power", 1.1, 1.9)
        if c["two_stage"]:
            c["p_fire"] = trial.suggest_float("p_fire", 0.2, 0.9)
        else:
            c["zero_floor"] = trial.suggest_float("zero_floor", 0.0, 1.0)
            c["own0_scale"] = trial.suggest_float("own0_scale", 0.02, 1.0, log=True)
            c["zero_rule"] = trial.suggest_categorical("zero_rule", ["cell_and_nbr", "none"])
            c["zero_rule"] = None if c["zero_rule"] == "none" else c["zero_rule"]
        models = fit_models(c, x, y, fit_rows, held_rows)
        est = models_predict(models, held, c)
        return inner_objective(inner_score(train, held_rows, est), ref)

    sampler = optuna.samplers.TPESampler(seed=settings()["seeds"]["lightgbm"])
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(objective, n_trials=int(cfg["optuna_trials"]))
    best = {**cfg, **study.best_params}
    if best.get("zero_rule") == "none":
        best["zero_rule"] = None
    return best


def fit_lgb(train: pd.DataFrame, **overrides) -> Predict:
    cfg = {**LGB, **overrides}
    train = train.reset_index(drop=True)
    x = lgb_inputs(train, cfg)
    y = train[V].to_numpy(float)
    fit_rows, held_rows = inner_split(train, int(cfg["inner_months"]))
    if cfg["optuna_trials"]:
        cfg = tune(cfg, train, x, y, fit_rows, held_rows)
    inner = fit_models(cfg, x, y, fit_rows, held_rows)
    rounds = {k: max(m.best_iteration, 1) for k, m in inner.items()}
    models = refit_models(cfg, x, y, rounds)
    booster = models["reg"]

    def predict(feats: pd.DataFrame) -> np.ndarray:
        return models_predict(models, feats, cfg)

    predict.booster = booster  # type: ignore[attr-defined]
    predict.models = models  # type: ignore[attr-defined]
    predict.config = {**cfg, "rounds": rounds}  # type: ignore[attr-defined]
    return predict


METHODS: dict[str, Callable[..., Predict]] = {
    "m0": fit_m0,
    "m1s": fit_m1s,
    "qm": fit_qm,
    "lgb": fit_lgb,
}
LAMBDAS = (0.0, 5.0, 20.0, 50.0, 100.0)  # M1s grid, chosen on the validation windows (S08)


def fit(train: pd.DataFrame) -> Predict:
    """The selected and frozen method (S11, docs/decisions/0008): LightGBM E028 = fit_lgb with
    the LGB configuration above. Frozen with this file; M1s stays available as fit_m1s."""
    return fit_lgb(train)
