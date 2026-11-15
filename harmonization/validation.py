"""S13 validation report (D1): the numbers and the six core figures of reports/validation.md.

  uv run python -X utf8 -m harmonization.validation drift     # era-shift classifier (~5 min)
  uv run python -X utf8 -m harmonization.validation gfed      # GFED4.1s plausibility check
  uv run python -X utf8 -m harmonization.validation figures   # tables and figures
  uv run python -X utf8 -m harmonization.validation all

Everything here comes after the final test (S11) and changes nothing in the model, the data or
the scores. Sources, all already in the repository or the data directory:
  validation scores   reports/scores-v1.json (M0, M1s, QM), reports/scores-s10.json (E028)
  test scores         results/final-test/scores.json (written by the grader, never edited)
  final series        <data>/processed/v1 (S12, harmonization.series_v1)
  frozen model        results/freeze.json, refitted with harmonization.freeze.fixed_fit
The machine still has no 2012-2013 S-NPP and no holdout VIIRS; test-period VIIRS appears only as
the region-year totals the grader reported. Choices the task card leaves open are recorded in
docs/decisions/0010.

drift  (preregistration section 8) LightGBM classifier on the frozen model's 18 MODIS inputs,
       2002-2011 (label 0) against 2014-2021 (label 1), 5-fold cross-validation grouped by
       calendar year; rows = training-region cell-months with both MODIS sensors complete and at
       least one MODIS detection (the rows the model's estimate depends on). Out-of-fold AUC,
       gain importance, and the AUC of each input alone. No input is removed to lower the AUC.
gfed   (section 6) detections per km2 of GFED4.1s burned area, per training region and year:
       the harmonized series (v1), the direct splice (Aqua as is) and, for 2012-2013, the
       grader's observed S-NPP totals over the same months.
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import cache

import matplotlib
import matplotlib.dates
import matplotlib.ticker

matplotlib.use("Agg")
import h5py  # noqa: E402
import lightgbm as lgb  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

from harmonization import freeze, harmonize, prepare  # noqa: E402
from harmonization.config import ROOT, data_dir, regions, settings  # noqa: E402

OUT = ROOT / "reports" / "validation.json"
FIG = ROOT / "reports" / "figures"
ERA_OLD, ERA_NEW = ("2002-07", "2011-12"), ("2014-01", "2021-12")
ERA_CONTROL = ("2022-01", "2026-10")
GFED_YEARS = range(2003, 2017)  # whole Aqua years with GFED4.1s burned area (the 2017+ beta
# files carry emissions only, no burned_area group)
TRAIN = ("california", "cordoba", "southern_africa")
HOLD = ("north_australia", "central_siberia", "indo_gangetic")
NAMES = {
    "california": "California",
    "cordoba": "Córdoba",
    "southern_africa": "Southern Africa",
    "north_australia": "N. Australia (holdout)",
    "central_siberia": "C. Siberia (holdout)",
    "indo_gangetic": "Indo-Gangetic (holdout)",
}
C_OBS, C_LGB, C_M1S, C_QM, C_M0 = "#222222", "#2a78d6", "#eb6834", "#9b59b6", "#9a9a95"
SEED = settings()["seeds"]["lightgbm"]


def load(path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def results() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}


def save(key: str, value) -> None:
    res = results()
    res[key] = value
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def style(ax, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(color="#e6e6e3", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def frozen_cfg() -> dict:
    cfg = load("results/freeze.json")["config"]
    return {**cfg, "monotone": tuple(cfg["monotone"]), "drop": tuple(cfg["drop"])}


@cache
def grid() -> pd.DataFrame:
    return prepare.load_grid()


# --- drift: era-shift classifier (preregistration section 8) -------------------------------
def drift_rows(df: pd.DataFrame, role: str, new: tuple[str, str] = ERA_NEW) -> pd.DataFrame:
    """Cell-months of one role in the two eras, both MODIS sensors complete, any detection."""
    m = df["month"]
    era_old = (m >= ERA_OLD[0]) & (m <= ERA_OLD[1])
    era_new = (m >= new[0]) & (m <= new[1])
    ok = (df["aqua_status"] == "complete") & (df["terra_status"] == "complete")
    fire = (df["aqua_count"] + df["terra_count"]) > 0
    keep = (df["role"] == role) & (era_old | era_new) & ok
    out = df[keep.to_numpy()].copy()
    out["era_new"] = era_new[keep].astype(int).to_numpy()
    out["year"] = out["month"].str[:4]
    out["fire"] = fire[keep].to_numpy()
    return out.reset_index(drop=True)


def drift_fit(rows: pd.DataFrame, cfg: dict) -> dict:
    """5-fold CV grouped by calendar year (years assigned to folds round-robin, sorted)."""
    x = harmonize.lgb_inputs(rows, cfg)
    y = rows["era_new"].to_numpy()
    years = np.sort(rows["year"].unique())
    fold_of = {yr: i % 5 for i, yr in enumerate(years)}
    fold = rows["year"].map(fold_of).to_numpy()
    params = {
        "objective": "binary",
        "num_leaves": 31,
        "min_data_in_leaf": 200,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "feature_fraction_seed": SEED,
        "deterministic": True,
        "force_col_wise": True,
        "seed": SEED,
        "num_threads": harmonize.THREADS,
        "verbose": -1,
    }
    oof = np.zeros(len(rows))
    gain = pd.Series(0.0, index=x.columns)
    per_fold, per_region = [], {r: [] for r in rows["region"].unique()}
    region = rows["region"].to_numpy()
    for k in range(5):
        te = fold == k
        booster = lgb.train(params, lgb.Dataset(x[~te], y[~te]), num_boost_round=300)
        oof[te] = booster.predict(x[te])
        gain += pd.Series(booster.feature_importance("gain"), index=booster.feature_name())
        if len(np.unique(y[te])) == 2:
            per_fold.append(float(roc_auc_score(y[te], oof[te])))
        for r in per_region:
            m = te & (region == r)
            if len(np.unique(y[m])) == 2:
                per_region[r].append(float(roc_auc_score(y[m], oof[m])))
    gain = (100 * gain / gain.sum()).sort_values(ascending=False)
    single = {}
    for c in x.columns:
        v = x[c].to_numpy(float)
        v = np.where(np.isnan(v), -1.0, v)  # "no detection" sorts below every real value
        a = roc_auc_score(y, v)
        single[c] = float(max(a, 1 - a))
    return {
        "rows": int(len(rows)),
        "rows_old": int((y == 0).sum()),
        "rows_new": int((y == 1).sum()),
        # primary: mean of the per-fold AUCs. The pooled out-of-fold AUC mixes predictions of
        # five models whose base rates differ by fold, which biases it towards (or below) 0.5.
        "auc": float(np.mean(per_fold)),
        "auc_by_fold": per_fold,
        "auc_pooled_oof": float(roc_auc_score(y, oof)),
        "auc_by_region": {r: float(np.mean(v)) for r, v in sorted(per_region.items()) if v},
        "fold_years": {str(k): [yr for yr in years if fold_of[yr] == k] for k in range(5)},
        "gain_share_pct": {k: round(float(v), 2) for k, v in gain.items()},
        "single_feature_auc": dict(sorted(single.items(), key=lambda kv: -kv[1])),
        "oof": oof,
    }


def yearly_means(rows: pd.DataFrame, cols: list[str]) -> dict:
    """Per calendar year: mean of each input over the rows (fire rows), for the trend figure."""
    g = rows.groupby("year")[cols].mean()
    return {c: {yr: float(v) for yr, v in g[c].items()} for c in cols}


def drift() -> dict:
    df = grid()
    cfg = frozen_cfg()
    out: dict = {"eras": {"old": ERA_OLD, "new": ERA_NEW, "control": ERA_CONTROL}}
    for role in ("train", "holdout"):
        rows = drift_rows(df, role)
        fire = rows[rows["fire"]].reset_index(drop=True)
        res = drift_fit(fire, cfg)
        res.pop("oof")
        top = list(res["single_feature_auc"])[:6]
        cols = list(dict.fromkeys(top + ["aqua_count", "terra_count"]))
        res["yearly_means_fire_rows"] = yearly_means(fire, cols)
        res["share_rows_with_detection"] = {
            "old": float(rows.loc[rows["era_new"] == 0, "fire"].mean()),
            "new": float(rows.loc[rows["era_new"] == 1, "fire"].mean()),
        }
        # feature groups, diagnosis only: which sensor's inputs carry the separation
        groups = {
            "aqua_only": [c for c in res["gain_share_pct"] if c.startswith("aqua_")],
            "terra_only": [c for c in res["gain_share_pct"] if c.startswith("terra_")],
            "lat_month_only": ["lat", "cal_month"],
        }
        res["auc_by_input_group"] = {}
        for name, cols in groups.items():
            keep_drop = [c for c in res["gain_share_pct"] if c not in cols]
            sub = drift_fit(fire, {**cfg, "drop": tuple(cfg["drop"]) + tuple(keep_drop)})
            res["auc_by_input_group"][name] = sub["auc"]
        # positive control, diagnosis only: the same classifier against 2022-2026, when Terra and
        # Aqua are known to drift (reports/findings.md items 4 and 7); shows it can see a shift
        ctl_rows = drift_rows(df, role, ERA_CONTROL)
        ctl = drift_fit(ctl_rows[ctl_rows["fire"]].reset_index(drop=True), cfg)
        res["control_2022_2026"] = {
            k: ctl[k] for k in ("auc", "auc_by_fold", "auc_by_region", "rows_new")
        }
        res["control_2022_2026"]["top_gain"] = dict(list(ctl["gain_share_pct"].items())[:6])
        res["control_2022_2026"]["top_single"] = dict(list(ctl["single_feature_auc"].items())[:6])
        out[role] = res
        print(
            f"drift {role}: AUC {res['auc']:.3f} (control {ctl['auc']:.3f}), {res['rows']} rows",
            flush=True,
        )
    save("drift", out)
    return out


# --- gfed: detections per burned area (preregistration section 6) --------------------------
def gfed_region_ba() -> pd.DataFrame:
    """GFED4.1s burned area (km2) per region and month, cells of config/regions.json."""
    raw = data_dir() / "raw" / "gfed"
    cell = settings()["grid"]["cell_deg"]
    rows = []
    for year in GFED_YEARS:
        with h5py.File(raw / f"GFED4.1s_{year}.hdf5", "r") as f:
            area_km2 = f["ancill/grid_cell_area"][:] / 1e6
            for r in regions():
                # GFED rows run north to south from 89.875; columns west to east from -179.875
                i0, i1 = round((90 - r["north"]) / cell), round((90 - r["south"]) / cell)
                j0, j1 = round((r["west"] + 180) / cell), round((r["east"] + 180) / cell)
                for mo in range(1, 13):
                    bf = f[f"burned_area/{mo:02d}/burned_fraction"][i0:i1, j0:j1]
                    ba = float((bf * area_km2[i0:i1, j0:j1]).sum())
                    rows.append({"region": r["name"], "month": f"{year}-{mo:02d}", "ba_km2": ba})
    return pd.DataFrame(rows)


def grader_months() -> dict:
    """Months the grader counted in test 1 per training region and year: the set of months
    whose summed submission estimate reproduces the grader's total H (one excluded month at
    most, preregistration section 2 excludes missing and partial months)."""
    sub = pd.read_parquet(
        ROOT / "results" / "submission.parquet", columns=[*prepare.KEY, "month", "est_final"]
    )
    cells = grid()[[*prepare.KEY, "region", "role"]].drop_duplicates(prepare.KEY)
    sub = sub.merge(cells, on=prepare.KEY)
    sub = sub[sub["role"] == "train"]
    mon = sub.groupby(["region", "month"])["est_final"].sum()
    sc = load("results/final-test/scores.json")["test1"]["scores"]["est_final"]["total_bias"]
    out = {}
    for t in sc:
        m = mon.loc[t["region"]]
        m = m[m.index.str[:4] == t["year"]]
        months = list(m.index)
        if abs(m.sum() - t["H"]) <= 1e-6 * max(1.0, t["H"]):
            out[(t["region"], t["year"])] = months
            continue
        for drop in months:
            if abs(m.drop(drop).sum() - t["H"]) <= 1e-6 * max(1.0, t["H"]):
                out[(t["region"], t["year"])] = [x for x in months if x != drop]
                break
        else:
            raise SystemExit(f"cannot match the grader's months for {t['region']} {t['year']}")
    return out


def gfed() -> dict:
    ba = gfed_region_ba()
    v1 = pd.read_csv(data_dir() / "processed" / "v1" / "region_totals_v1.csv")
    tab = v1.merge(ba, on=["region", "month"], how="inner")
    tab["year"] = tab["month"].str[:4]
    out: dict = {"years": [GFED_YEARS.start, GFED_YEARS.stop - 1], "regions": {}}
    gm = grader_months()
    sc = {
        (t["region"], t["year"]): t
        for t in load("results/final-test/scores.json")["test1"]["scores"]["est_final"][
            "total_bias"
        ]
    }
    for r in TRAIN + HOLD:
        g = tab[tab["region"] == r]
        yr = g.groupby("year")[["est", "est_m0", "ba_km2"]].sum()
        src = g.groupby("year")["source"].agg(lambda s: s.value_counts().index[0])
        d = {
            "per_year": {
                y: {
                    "ba_km2": float(row.ba_km2),
                    "harmonized_per_km2": float(row.est / row.ba_km2) if row.ba_km2 > 0 else None,
                    "splice_per_km2": float(row.est_m0 / row.ba_km2) if row.ba_km2 > 0 else None,
                    "main_source": str(src[y]),
                }
                for y, row in yr.iterrows()
            }
        }
        for y in ("2012", "2013"):
            if (r, y) in sc:
                months = gm[(r, y)]
                b = float(g.loc[g["month"].isin(months), "ba_km2"].sum())
                d["per_year"][y]["grader_obs_per_km2"] = sc[(r, y)]["V"] / b if b > 0 else None
                d["per_year"][y]["grader_est_per_km2"] = sc[(r, y)]["H"] / b if b > 0 else None
                d["per_year"][y]["grader_months"] = len(months)

        def mean(key, y0, y1, d=d):
            v = [
                p[key]
                for y, p in d["per_year"].items()
                if y0 <= int(y) <= y1 and p.get(key) is not None
            ]
            return float(np.mean(v)) if v else None

        d["mean_2003_2011"] = {
            "harmonized": mean("harmonized_per_km2", 2003, 2011),
            "splice": mean("splice_per_km2", 2003, 2011),
        }
        d["mean_2014_2016"] = {
            "harmonized": mean("harmonized_per_km2", 2014, 2016),
            "splice": mean("splice_per_km2", 2014, 2016),
        }
        d["mean_2012_2013_grader_obs"] = mean("grader_obs_per_km2", 2012, 2013)
        out["regions"][r] = d
        print(f"gfed {r}: {d['mean_2003_2011']} / {d['mean_2014_2016']}", flush=True)
    save("gfed", out)
    return out


# --- score tables (no new scoring: collected from the judge's outputs) ---------------------
def run_key(runs: dict, prefix: str) -> str:
    """Keys of scores-v1.json carry a Greek lambda; match on the ASCII part."""
    hits = [k for k in runs if k.startswith(prefix) and (prefix != "M1s" or k.endswith("=20"))]
    if len(hits) != 1:
        raise SystemExit(f"ambiguous or missing run {prefix}: {hits}")
    return hits[0]


METRICS = (
    "male",
    "male_all",
    "zero_ge1",
    "zero_ge5",
    "low_mae",
    "total_bias_mean_abs",
    "season_corr_mean",
)


def score_tables() -> dict:
    v1 = load("reports/scores-v1.json")
    s10 = load("reports/scores-s10.json")["top3"]
    e028 = next(t for t in s10 if t["exp_id"] == "E028")
    ft = load("results/final-test/scores.json")
    runs = v1["runs"]
    methods = {
        "E028": {w: e028["windows"][w] for w in ("main", "aux")},
        "M1s": {w: runs[run_key(runs, "M1s")][w] for w in ("main", "aux")},
        "QM": {w: runs[run_key(runs, "QM")][w] for w in ("main", "aux")},
        "M0": {w: runs[run_key(runs, "M0")][w] for w in ("main", "aux")},
    }
    cols = {"E028": "est_final", "M1s": "est_m1s", "QM": "est_qm", "M0": "est_m0"}
    for m, c in cols.items():
        for t in ("test1", "test2"):
            methods[m][t] = ft[t]["scores"][c]
    table = {
        m: {w: {k: r.get(k) for k in (*METRICS, "male_by_region")} for w, r in ws.items()}
        for m, ws in methods.items()
    }
    diffs = {
        "validation_combined": {
            "vs_M1s": {k: -v if isinstance(v, float) else v for k, v in e028["vs_m1s"].items()},
            "vs_QM": {k: -v if isinstance(v, float) else v for k, v in e028["vs_qm"].items()},
        },
        "test1": {
            "vs_M1s": ft["test1"]["differences"]["est_final_vs_est_m1s"],
            "vs_QM": ft["test1"]["differences"]["est_final_vs_est_qm"],
        },
        "test2": {
            "vs_M1s": ft["test2"]["differences"]["est_final_vs_est_m1s"],
            "vs_QM": ft["test2"]["differences"]["est_final_vs_est_qm"],
        },
    }
    for d in diffs["validation_combined"].values():  # S10 reports E028 - M1s; flip to M1s - E028
        d["ci95"] = sorted(-x for x in d["ci95"])
        d["se"] = abs(d["se"])
    out = {
        "methods": table,
        "combined_validation_male": {
            "E028": e028["combined_male"],
            "M1s": load("reports/scores-s10.json")["m1s_combined"],
            "QM": load("reports/scores-s10.json")["qm_combined"],
        },
        "diff_positive_means_E028_better": diffs,
        "selection": e028["selection"],
        "kappa": {
            t: {
                m: ft[t]["anomaly_agreement"][c]["kappa"]
                for m, c in (("E028", "est_final"), ("M1s", "est_m1s"))
            }
            for t in ("test1", "test2")
        },
        "coverage": {t: ft[t]["coverage"] for t in ("test1", "test2")},
    }
    return out


# --- figures -----------------------------------------------------------------------------
def month_axis(months) -> pd.DatetimeIndex:
    return pd.to_datetime(pd.Series(list(months)) + "-15")


def fig1_problem(df: pd.DataFrame) -> dict:
    """The problem: Aqua then S-NPP, joined as is, in one training region."""
    r = "southern_africa"
    g = df[df["region"] == r]
    aqua = g[g["aqua_status"] == "complete"].groupby("month")["aqua_count"].sum()
    snpp = g[g["snpp_status"] == "complete"].groupby("month")["snpp_count"].sum()
    aqua = aqua[aqua.index >= "2002-07"]
    both = aqua.index.intersection(snpp.index)
    both = both[(both >= "2014-01") & (both <= "2021-12")]
    yr = pd.DataFrame({"a": aqua[both], "v": snpp[both]}).groupby(lambda m: m[:4]).sum()
    factor = (yr["v"] / yr["a"]).agg(["min", "max"]).to_dict()
    splice = pd.concat([aqua[aqua.index < "2012-02"], snpp[snpp.index >= "2012-02"]])
    every = pd.period_range(splice.index.min(), splice.index.max(), freq="M").strftime("%Y-%m")
    splice = splice.reindex(every)  # months without a value break the line instead of bridging
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(
        month_axis(splice.index),
        splice.to_numpy(),
        color=C_OBS,
        lw=1.3,
        label="direct splice: Aqua MODIS until 2012-01, S-NPP VIIRS after",
    )
    ax.plot(
        month_axis(aqua.index),
        aqua.to_numpy(),
        color=C_M0,
        lw=0.9,
        ls="--",
        label="Aqua MODIS (continues, for comparison)",
    )
    ax.axvline(pd.Timestamp("2012-02-01"), color="#c0392b", lw=1.2)
    ax.text(
        pd.Timestamp("2012-04-01"),
        0.97,
        "sensor switch\n2012-02",
        color="#c0392b",
        transform=ax.get_xaxis_transform(),
        va="top",
        fontsize=8,
    )
    ax.axvspan(pd.Timestamp("2012-02-01"), pd.Timestamp("2013-12-31"), color="#f2f2ef", lw=0)
    ax.text(
        pd.Timestamp("2012-12-15"),
        0.03,
        "2012-13 S-NPP\nkept off this machine\n(final test)",
        transform=ax.get_xaxis_transform(),
        ha="center",
        fontsize=6.5,
        color="#666",
    )
    ax.set_yscale("log")
    ax.set_ylim(10, None)
    style(ax, "", "fire detections per month")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title(
        f"Joining MODIS to VIIRS as is makes fire activity jump {factor['min']:.1f}-"
        f"{factor['max']:.1f}x at 2012 (Southern Africa; same fires, two sensors)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(FIG / "d1-1-problem.png", dpi=130)
    plt.close(fig)
    return {"region": r, "snpp_over_aqua_yearly_2014_2021": factor}


def fig2_test_totals() -> dict:
    """Test years: yearly totals from the grader, true VIIRS against E028 and M1s."""
    ft = load("results/final-test/scores.json")
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    out = {}
    for ax, r in zip(axes.ravel(), TRAIN + HOLD, strict=True):
        t = "test1" if r in TRAIN else "test2"
        rows = {
            m: {d["year"]: d for d in ft[t]["scores"][c]["total_bias"] if d["region"] == r}
            for m, c in (("E028", "est_final"), ("M1s", "est_m1s"))
        }
        years = sorted(rows["E028"])
        x = np.arange(len(years))
        v = np.array([rows["E028"][y]["V"] for y in years]) / 1e3
        h = np.array([rows["E028"][y]["H"] for y in years]) / 1e3
        m = np.array([rows["M1s"][y]["H"] for y in years]) / 1e3
        w = 0.27
        ax.bar(x - w, v, w, color=C_OBS, label="true S-NPP VIIRS (grader)")
        ax.bar(x, h, w, color=C_LGB, label="LightGBM E028 (MODIS inputs only)")
        ax.bar(x + w, m, w, color=C_M1S, label="M1s ratio baseline")
        ax.set_xticks(x, [y[2:] if len(years) > 2 else y for y in years], fontsize=8)
        style(ax, "", "detections per year (thousands)" if r in (TRAIN[0], HOLD[0]) else "")
        bias_l = float(np.mean(np.abs(h / v - 1)))
        bias_m = float(np.mean(np.abs(m / v - 1)))
        ax.set_title(
            f"{NAMES[r]}\nmean |yearly total bias| E028 {100 * bias_l:.0f}%,"
            f" M1s {100 * bias_m:.0f}%",
            fontsize=9,
        )
        out[r] = {"test": t, "mean_abs_bias_E028": bias_l, "mean_abs_bias_M1s": bias_m}
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, frameon=False, fontsize=8, ncol=3, loc="lower center")
    fig.suptitle(
        "Locked test years, yearly totals from MODIS inputs alone: E028 is within 9% of true VIIRS"
        " in the training regions and N. Australia (to 2019),\nbut 14-45% too low in C. Siberia"
        " and the Indo-Gangetic plain (test 1 = training regions 2012-13, 2012 = Feb-Dec;"
        " test 2 = holdout regions 2012-21)",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "d1-2-test-totals.png", dpi=130)
    plt.close(fig)
    return out


def fig3_scores(tab: dict) -> None:
    windows = ("main", "aux", "test1", "test2")
    wlab = {
        "main": "validation main\n2014-15",
        "aux": "validation aux\n2016-17",
        "test1": "test 1: training\nregions 2012-13",
        "test2": "test 2: holdout\nregions 2012-21",
    }
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [3, 2]})
    x = np.arange(len(windows))
    for k, (m, c) in enumerate((("E028", C_LGB), ("M1s", C_M1S), ("QM", C_QM))):
        y = [tab["methods"][m][w]["male"] for w in windows]
        xs = x + (k - 1) * 0.26
        a1.bar(xs, y, 0.26, color=c, label="LightGBM E028" if m == "E028" else m)
        for xi, yi in zip(xs, y, strict=True):
            a1.text(xi, yi + 0.01, f"{yi:.2f}", ha="center", fontsize=7)
    m0 = [tab["methods"]["M0"][w]["male"] for w in windows]
    a1.set_xticks(
        x, [f"{wlab[w]}\n(M0 splice {v:.1f})" for w, v in zip(windows, m0, strict=True)], fontsize=8
    )
    style(a1, "", "MALE (lower is better)")
    a1.legend(frameon=False, fontsize=8, loc="upper left")
    a1.set_title("Primary score in every window (M0 = direct splice, off the scale)", fontsize=9)
    d = tab["diff_positive_means_E028_better"]
    keys = (
        ("validation_combined", "validation\n(both windows)"),
        ("test1", "test 1"),
        ("test2", "test 2"),
    )
    for j, (k, _) in enumerate(keys):
        for i, (ref, c) in enumerate((("vs_M1s", C_M1S), ("vs_QM", C_QM))):
            r = d[k][ref]
            err = [[r["diff"] - r["ci95"][0]], [r["ci95"][1] - r["diff"]]]
            a2.errorbar(
                r["diff"],
                j + (-0.15 if i == 0 else 0.15),
                xerr=err,
                fmt="o",
                color=c,
                capsize=3,
                label=f"MALE({ref[3:]}) - MALE(E028)" if j == 0 else None,
            )
    a2.axvline(0, color="#888", lw=0.8)
    a2.set_yticks(range(len(keys)), [k[1] for k in keys], fontsize=8)
    a2.invert_yaxis()
    style(a2, "difference, 95% year x region block-bootstrap interval", "")
    a2.legend(frameon=False, fontsize=8, loc="upper right")
    a2.set_xlim(0, None)
    a2.set_title("How much better E028 is (positive = better); no interval crosses 0", fontsize=9)
    fig.suptitle(
        "E028 beats the ratio (M1s) and quantile-mapping (QM) baselines in all four windows;"
        " the holdout regions are about 2.5x harder for every method",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(FIG / "d1-3-scores.png", dpi=130)
    plt.close(fig)


PD_GRID = {"lat": np.arange(-40.0, 66.01, 1.0)}
PD_LABEL = {
    "aqua_count": "Aqua detections in the cell-month",
    "aqua_frp_median": "Aqua median FRP of the cell-month (MW)",
    "aqua_pixel_area_mean": "Aqua mean pixel area (km2; large = far off nadir)",
    "lat": "latitude (deg)",
}


def fig4_explain(df: pd.DataFrame) -> dict:
    """Frozen model (refit on 2014-01..2021-06): importance and estimate-per-Aqua-fire curves."""
    cfg = frozen_cfg()
    train = freeze.training_table(df, "test")
    models = freeze.fixed_fit(cfg, train)
    imp = {}
    for k, m in models.items():
        gsh = pd.Series(m.feature_importance("gain"), index=m.feature_name())
        imp[k] = 100 * gsh / gsh.sum()
    imp = pd.DataFrame(imp).fillna(0)
    imp = imp.loc[imp.sum(axis=1).sort_values().index]
    rng = np.random.default_rng(SEED)
    fire = train[train["aqua_count"] > 0].reset_index(drop=True)
    sample = fire.iloc[rng.choice(len(fire), min(8000, len(fire)), replace=False)]
    feats = prepare.feature_table(sample)
    # latitude: partial dependence (one input moved, the rest kept); the others: deciles of the
    # real rows, because moving the count alone makes impossible inputs (fire days > count)
    pdc = {}
    for v in PD_GRID["lat"]:
        x = feats.copy()
        x["lat"] = v
        est = harmonize.models_predict(models, x, cfg)
        pdc.setdefault("grid", []).append(float(v))
        pdc.setdefault("ratio", []).append(float(est.sum() / x["aqua_count"].sum()))
    fire = fire.assign(H=harmonize.models_predict(models, prepare.feature_table(fire), cfg))
    obs = {}
    for col in ("aqua_count", "aqua_frp_median", "aqua_pixel_area_mean"):
        edges = np.unique(np.quantile(fire[col], np.linspace(0, 1, 11)))
        gg = fire.groupby(pd.cut(fire[col], edges, include_lowest=True), observed=True)
        a = gg["aqua_count"].sum()
        obs[col] = pd.DataFrame(
            {"x": gg[col].mean(), "obs": gg["snpp_count"].sum() / a, "model": gg["H"].sum() / a}
        )
    fig = plt.figure(figsize=(13, 7.5))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.15, 1, 1])
    ax0 = fig.add_subplot(gs[:, 0])
    yy = np.arange(len(imp))
    ax0.barh(yy + 0.2, imp["clf"], 0.4, color="#7fb3e8", label="stage 1: any VIIRS fire?")
    ax0.barh(yy - 0.2, imp["reg"], 0.4, color=C_LGB, label="stage 2: how many?")
    ax0.set_yticks(yy, imp.index, fontsize=7.5)
    style(ax0, "share of total gain (%)", "")
    ax0.legend(frameon=False, fontsize=8, loc="lower right")
    ax0.set_title("Inputs the frozen model uses", fontsize=9)
    regs = {r["name"]: r for r in regions()}
    panels = [fig.add_subplot(gs[i, j]) for i in range(2) for j in (1, 2)]
    for ax, col in zip(panels, PD_LABEL, strict=True):
        if col in obs:
            o = obs[col]
            ax.plot(o["x"], o["obs"], "s", ms=5, color=C_OBS, label="observed S-NPP / Aqua")
            ax.plot(o["x"], o["model"], "o-", ms=4, color=C_LGB, lw=1.5, label="model / Aqua")
            ax.set_title("deciles of training rows 2014-21 (in-sample)", fontsize=7.5)
        else:
            ax.plot(
                pdc["grid"], pdc["ratio"], color=C_LGB, lw=2, label="model (partial dependence)"
            )
            ax.set_title("latitude moved, other inputs kept", fontsize=7.5)
        if col in ("aqua_count", "aqua_frp_median"):
            ax.set_xscale("log")
            ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if col == "lat":
            for n, r in regs.items():
                if r["role"] == "train":
                    kw = {"color": "#1baf7a", "alpha": 0.15}
                else:
                    kw = {"facecolor": "none", "edgecolor": "#888", "hatch": "//", "alpha": 0.5}
                ax.axvspan(r["south"], r["north"], lw=0, **kw)
                ax.text(
                    (r["south"] + r["north"]) / 2,
                    0.97,
                    NAMES[n].split(" (")[0],
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="top",
                    fontsize=5.5,
                    rotation=90,
                )
        style(ax, PD_LABEL[col], "VIIRS-scale estimate per Aqua fire")
        ax.legend(frameon=False, fontsize=6.5)
    fig.suptitle(
        "The model is mainly a MODIS-count converter: about 8 VIIRS fires per MODIS fire where"
        " MODIS sees one or two, about 5 in big clusters;\nFRP and pixel size move it by 20-30%"
        " with no simple physical pattern; latitude acts as a region label"
        " (green = training bands, hatched = holdout)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(FIG / "d1-4-explain.png", dpi=130)
    plt.close(fig)
    return {
        "gain_share_pct": {k: imp[k].sort_values(ascending=False).round(2).to_dict() for k in imp},
        "pd_lat": pdc,
        "deciles": {k: v.round(3).to_dict(orient="list") for k, v in obs.items()},
    }


def fig5_series() -> dict:
    v1 = pd.read_csv(data_dir() / "processed" / "v1" / "region_totals_v1.csv")
    fig, axes = plt.subplots(6, 1, figsize=(12, 15), sharex=True)
    out = {}
    for ax, r in zip(axes, TRAIN + HOLD, strict=True):
        g = v1[v1["region"] == r].sort_values("month").reset_index(drop=True)
        t = month_axis(g["month"])
        model = g["source"].str.startswith("model").to_numpy()
        est = g["est"].clip(lower=1).to_numpy()
        lo, hi = g["lo_90"].clip(lower=1).to_numpy(), g["hi_90"].clip(lower=1).to_numpy()
        bridge = g["source"].eq("model_terra_bridge").to_numpy()
        for k, i in enumerate(np.flatnonzero(bridge)):  # each Terra-only month, not one span
            start = pd.Timestamp(g["month"].iloc[i] + "-01")
            ax.axvspan(
                start,
                start + pd.offsets.MonthEnd(1),
                color="#f4e7c5",
                alpha=0.9,
                lw=0,
                label="Terra-only bridge months (low confidence)" if k == 0 else None,
            )
        ax.fill_between(
            t,
            np.where(model, lo, np.nan),
            np.where(model, hi, np.nan),
            color=C_LGB,
            alpha=0.25,
            lw=0,
            label="stability interval (5-95 %, calibrated)",
        )
        ax.plot(t, np.where(model, est, np.nan), color=C_LGB, lw=1, label="model estimate")
        ax.plot(
            t,
            np.where(~model, est, np.nan),
            color=C_OBS,
            lw=1,
            label="observed VIIRS (S-NPP; NOAA-20 scaled in S-NPP gaps)",
        )
        m0 = g["est_m0"].where(g["month"] < "2012-02").clip(lower=1)
        ax.plot(t, m0, color=C_M0, lw=0.8, ls="--", label="MODIS as is (before 2012)")
        ax.axvline(pd.Timestamp("2012-02-01"), color="#c0392b", lw=0.8)
        ax.set_yscale("log")
        ax.set_ylim(1, None)
        style(ax, "", "detections / month")
        ax.set_title(NAMES[r] + ("" if r in TRAIN else ": model estimate every month"), fontsize=9)
        yr = g.assign(y=g["month"].str[:4]).groupby("y")["est"].sum()
        m0y = g.assign(y=g["month"].str[:4]).groupby("y")["est_m0"].sum()
        out[r] = {
            "mean_yearly_2003_2011": float(yr.loc["2003":"2011"].mean()),
            "mean_yearly_2014_2021": float(yr.loc["2014":"2021"].mean()),
            "splice_mean_yearly_2003_2011": float(m0y.loc["2003":"2011"].mean()),
        }
    axes[0].legend(frameon=False, fontsize=7, ncol=3, loc="upper left")
    fig.suptitle(
        "Harmonized history 2000-11 to 2026-10 on the VIIRS scale: no step at 2012, seasons and"
        " year-to-year swings kept",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(FIG / "d1-5-series.png", dpi=130)
    plt.close(fig)
    return out


def fig6_drift(df: pd.DataFrame) -> dict:
    d = results()["drift"]
    ok = (df["aqua_status"] == "complete") & (df["terra_status"] == "complete")
    fire = (df["aqua_count"] + df["terra_count"]) > 0
    g = df[(ok & fire & (df["month"] >= "2002-07")).to_numpy()]
    g = g.assign(year=g["month"].str[:4])
    cols = ("terra_frp_median", "terra_night_share", "aqua_frp_median", "aqua_night_share")
    yearly = {
        role: g[g["role"] == role].groupby("year")[list(cols)].mean()
        for role in ("train", "holdout")
    }
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1, 1.3]})
    labels = TRAIN + HOLD

    def role_of(r):
        return "train" if r in TRAIN else "holdout"

    x = np.arange(len(labels))
    main = [d[role_of(r)]["auc_by_region"][r] for r in labels]
    ctl = [d[role_of(r)]["control_2022_2026"]["auc_by_region"][r] for r in labels]
    a1.bar(x - 0.2, main, 0.4, color=C_LGB, label="2002-11 vs 2014-21 (the question)")
    a1.bar(x + 0.2, ctl, 0.4, color=C_M0, label="2002-11 vs 2022-26 (control: known orbit drift)")
    a1.axhline(0.5, color="#888", lw=0.8)
    a1.set_ylim(0.4, 0.85)
    a1.set_xticks(x, [NAMES[r].replace(" (holdout)", "\n(holdout)") for r in labels], fontsize=7)
    style(a1, "", "classifier AUC (0.5 = cannot tell the eras apart)")
    a1.legend(frameon=False, fontsize=7.5, loc="upper left")
    a1.set_title("Can the MODIS inputs alone tell which era a cell-month is from?", fontsize=9)
    colors = (C_M1S, C_QM, C_LGB, "#1baf7a")
    for role, ls in (("train", "-"), ("holdout", "--")):
        y = yearly[role].loc["2003":]  # 2002 has July-December only
        t = pd.to_datetime(pd.Series(y.index) + "-07-01")
        for c, col in zip(cols, colors, strict=True):
            base = y.loc["2003":"2011", c].mean()
            a2.plot(
                t,
                (y[c] / base).to_numpy(),
                ls=ls,
                color=col,
                lw=1.4,
                label=f"{c} ({'training' if role == 'train' else 'holdout'})",
            )
    for s, e, lab in (
        ("2002-07", "2011-12", "older era"),
        ("2014-01", "2021-12", "newer era"),
        ("2022-01", "2026-10", "control"),
    ):
        a2.axvspan(
            pd.Timestamp(s + "-01"),
            pd.Timestamp(e + "-28"),
            alpha=0.07,
            color="#555" if lab == "control" else C_LGB,
            lw=0,
        )
    a2.axhline(1, color="#888", lw=0.8)
    a2.set_yscale("log", base=2)
    a2.set_yticks([0.5, 0.75, 1, 1.5, 2, 3, 4], ["0.5", "0.75", "1", "1.5", "2", "3", "4"])
    a2.minorticks_off()
    style(a2, "", "yearly mean over fire cell-months / 2003-11 mean")
    a2.legend(frameon=False, fontsize=6.5, ncol=2, loc="upper left")
    a2.set_title("Terra's intensity and night-share inputs move mainly after 2020", fontsize=9)
    fig.suptitle(
        f"Era shift: the MODIS inputs of 2002-11 and 2014-21 are hard to tell apart"
        f" (AUC {d['train']['auc']:.2f} training, {d['holdout']['auc']:.2f} holdout); the same"
        " classifier does see the post-2022 drift",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(FIG / "d1-6-era-shift.png", dpi=130)
    plt.close(fig)
    return {
        role: {c: {k: round(float(v), 4) for k, v in yearly[role][c].items()} for c in cols}
        for role in yearly
    }


def figs_gfed() -> None:
    """Supplement: detections per km2 of GFED4.1s burned area, training regions."""
    gd = results()["gfed"]["regions"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, r in zip(axes, TRAIN, strict=True):
        py = gd[r]["per_year"]
        yrs = sorted(py)
        t = np.array([int(y) for y in yrs])
        harm = np.array([py[y]["harmonized_per_km2"] for y in yrs], float)
        gobs = np.array([py[y].get("grader_obs_per_km2", np.nan) for y in yrs], float)
        splice = np.array(
            [
                py[y]["splice_per_km2"] if int(y) < 2012 or int(y) > 2013 else gobs[i]
                for i, y in enumerate(yrs)
            ],
            float,
        )
        ax.plot(t, splice, "o--", color=C_M0, ms=4, lw=1, label="direct splice (Aqua, then S-NPP)")
        ax.plot(
            t,
            np.where(t <= 2013, harm, np.nan),
            "o-",
            color=C_LGB,
            ms=4,
            label="harmonized: model estimate (2003-13)",
        )
        ax.plot(
            t, np.where(t >= 2014, harm, np.nan), "o-", color=C_OBS, ms=4, label="observed S-NPP"
        )
        ax.plot(
            t,
            gobs,
            "D",
            color=C_OBS,
            mfc="white",
            ms=6,
            label="observed S-NPP 2012-13 (grader totals)",
        )
        ax.axvline(2012, color="#c0392b", lw=0.8)
        style(ax, "", "detections per km2 of GFED burned area")
        ax.set_title(NAMES[r], fontsize=9)
        ax.set_ylim(0, None)
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle(
        "Independent reference (GFED4.1s burned area, 2003-16): after harmonization, detections"
        " per burned km2 keep their level across 2012\n(clearest in Southern Africa and Córdoba;"
        " California is noisy, few burned km2); the direct splice jumps about 5x",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(FIG / "d1-s1-gfed.png", dpi=130)
    plt.close(fig)


def figs_validation_months(df: pd.DataFrame) -> dict:
    """Supplement: validation windows month by month (training regions, VIIRS known here)."""
    tabs = []
    for w in ("main", "aux"):
        v = pd.read_parquet(
            data_dir() / "s11" / f"val_{w}.parquet", columns=["region", "month", "V", "est_final"]
        )
        train, ev = prepare.window(df, w)
        rows = ev[ev["usable"].to_numpy()].reset_index(drop=True)
        m1s = harmonize.fit_m1s(train, 20.0)(prepare.feature_table(rows))
        mt = rows.assign(m1s=m1s).groupby(["region", "month"])["m1s"].sum().reset_index()
        tabs.append(v.merge(mt, on=["region", "month"]))
    tab = pd.concat(tabs)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    out = {}
    for ax, r in zip(axes, TRAIN, strict=True):
        g = tab[tab["region"] == r].sort_values("month")
        t = month_axis(g["month"])
        ax.plot(t, g["V"].to_numpy(), color=C_OBS, lw=1.6, label="true S-NPP")
        ax.plot(t, g["est_final"].to_numpy(), color=C_LGB, lw=1.2, label="E028")
        ax.plot(t, g["m1s"].to_numpy(), color=C_M1S, lw=1.0, ls="--", label="M1s")
        ax.set_yscale("log")
        style(ax, "", "detections / month")
        ax.set_title(NAMES[r], fontsize=9)
        ax.xaxis.set_major_locator(matplotlib.dates.YearLocator())
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))

        def err(col, g=g):
            return float(np.mean(np.abs(np.log1p(g[col]) - np.log1p(g["V"]))))

        out[r] = {
            "region_month_log_err_E028": err("est_final"),
            "region_month_log_err_M1s": err("m1s"),
        }
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle(
        "Validation windows 2014-17, region totals by month: both methods follow true VIIRS;"
        " mean |log error| E028 / M1s = "
        + ", ".join(
            f"{NAMES[r]} {v['region_month_log_err_E028']:.2f} / {v['region_month_log_err_M1s']:.2f}"
            for r, v in out.items()
        )
        + "\n(region totals are easier than the scored 1-5 deg rectangles)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(FIG / "d1-s2-validation-months.png", dpi=130)
    plt.close(fig)
    return out


def figures() -> None:
    df = grid()
    tab = score_tables()
    save("scores", tab)
    save("fig1_problem", fig1_problem(df))
    save("fig2_test_totals", fig2_test_totals())
    fig3_scores(tab)
    save("fig4_explain", fig4_explain(df))
    save("fig5_series", fig5_series())
    save("fig6_drift_yearly", fig6_drift(df))
    figs_gfed()
    save("supp_validation_months", figs_validation_months(df))
    print("figures written to reports/figures/d1-*.png", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("what", choices=["drift", "gfed", "figures", "all"])
    a = p.parse_args()
    if a.what in ("drift", "all"):
        drift()
    if a.what in ("gfed", "all"):
        gfed()
    if a.what in ("figures", "all"):
        figures()
    return 0


if __name__ == "__main__":
    sys.exit(main())
