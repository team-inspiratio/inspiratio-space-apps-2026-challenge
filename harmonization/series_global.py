"""Stage G: the global rerun with the frozen model settings (task card G-global, ADR 0013).

  uv run python -X utf8 -m harmonization.series_global scores     # validation windows by region
  uv run python -X utf8 -m harmonization.series_global inputs     # model rows, ratios, dedup
  uv run python -X utf8 -m harmonization.series_global resample deploy [--part k --of K]
  uv run python -X utf8 -m harmonization.series_global resample main|aux [--part k --of K]
  uv run python -X utf8 -m harmonization.series_global calibrate  # interval scale (windows)
  uv run python -X utf8 -m harmonization.series_global build      # <data>/processed/global-v1/
  uv run python -X utf8 -m harmonization.series_global package    # CSV, docs, SHA256SUMS only

Same procedure as S11/S12 (harmonization/freeze.py, series_v1.py) on the global table of
harmonization/global_grid.py; nothing is tuned, selected or tested again:
  - model: E028 with the frozen parameters and numbers of rounds of results/freeze.json
    (validation windows: the window's own frozen configuration), refitted without tuning or
    early stopping on the global training cells (role `train`); holdout cells never train;
  - scores: the frozen judge (evaluate.score) on the validation windows, on the demo and GFED
    rectangles of the training cells, by region; M1s (lam 20), QM and M0 fitted on the same
    rows, and the S11 window model (trained on the three demo regions) as a reference;
  - intervals: the 100 sealed year-block draws (seeds.resampling), cell-level 5 %/95 %
    quantiles, region totals widened by an interval scale found with the frozen formula
    (freeze.interval_scale) on the global validation windows;
  - sources, bridge and continuation exactly as series_v1.build.
Rows whose input features are identical get identical estimates, so each distinct feature row
is predicted once and the result broadcast (`compact`); `inputs` checks the broadcast is exact.
"""

from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from harmonization import evaluate, freeze, global_grid, grid, harmonize, prepare, series_v1
from harmonization.config import ROOT, data_dir, regions, settings

VERSION = "global-v1"
# Year-block resamples per set (deploy, main, aux): the first 50 of the sealed S11 draws
# (freeze.RESAMPLES = 100), for run time; ADR 0013 item 5 addendum. Prefix of the same seed,
# so draw b is identical to S11 draw b (checked against freeze.json in `resample`).
RESAMPLES = 50
METHODS = ("e028_global", "m1s", "qm", "m0", "e028_s11")
GFED_NAMES = {
    "BONA": "Boreal North America",
    "TENA": "Temperate North America",
    "CEAM": "Central America",
    "NHSA": "Northern Hemisphere South America",
    "SHSA": "Southern Hemisphere South America",
    "EURO": "Europe",
    "MIDE": "Middle East",
    "NHAF": "Northern Hemisphere Africa",
    "SHAF": "Southern Hemisphere Africa",
    "BOAS": "Boreal Asia",
    "CEAS": "Central Asia",
    "SEAS": "Southeast Asia",
    "EQAS": "Equatorial Asia",
    "AUST": "Australia and New Zealand",
}
WINDOW_MONTHS = ("2014-01", "2021-06")  # both validation windows and test_train
LABEL = prepare.LABEL


def work(*parts: str) -> Path:
    d = data_dir() / "global" / Path(*parts) if parts else data_dir() / "global"
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_root() -> Path:
    d = data_dir() / "processed" / VERSION
    d.mkdir(parents=True, exist_ok=True)
    return d


def window_cols() -> list[str]:
    status = ["snpp_status", "aqua_status", "terra_status"]
    return prepare.KEY + ["region", "role", "month"] + prepare.features() + [LABEL] + status


def window_table() -> pd.DataFrame:
    """Training-cell rows of 2014-01..2021-06 (every validation window and test_train)."""
    return global_grid.load(months=WINDOW_MONTHS, columns=window_cols(), role="train")


def as_float(x: pd.DataFrame) -> pd.DataFrame:
    """One float64 block. LightGBM turns a mixed frame into float64 anyway (same values), and
    one block lets row resampling and training avoid extra copies."""
    return x.astype(np.float64)


def compact(feats: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """(distinct feature rows, index of each row's distinct row). Exactness is checked."""
    f = prepare.features()
    h = pd.util.hash_pandas_object(feats[f], index=False).to_numpy()
    _, first, inv = np.unique(h, return_index=True, return_inverse=True)
    rep = feats.iloc[first].reset_index(drop=True)
    a = feats[f].to_numpy(float)
    b = rep[f].to_numpy(float)[inv]
    if not ((a == b) | (np.isnan(a) & np.isnan(b))).all():
        raise SystemExit("feature-row hash collision: compact() would not be exact")
    return rep, inv.astype(np.int64)


# --- validation windows ---------------------------------------------------------------------
def score_methods(rows: pd.DataFrame, est: dict, rect: dict) -> dict:
    out = {}
    for name, e in est.items():
        out[name] = {}
        for scope, rc in rect.items():
            s = evaluate.score(rows, e, rc, LABEL)
            out[name][scope] = s
    return out


def scores() -> dict:
    """Validation-window scores of the global E028 and the baselines, by region."""
    demo = prepare.load_grid()
    res: dict = {}
    for w in prepare.WINDOWS:
        t0 = time.time()
        df = window_table()
        cells = df[prepare.KEY].drop_duplicates()
        rect = {
            "all": prepare.rectangle_cells(cells, sets=("demo", "gfed")),
            "demo": prepare.rectangle_cells(cells, sets=("demo",)),
            "gfed": prepare.rectangle_cells(cells, sets=("gfed",)),
        }
        train, ev = prepare.window(df, w)
        del df
        rows = ev[ev["usable"].to_numpy()].reset_index(drop=True)
        excluded = float(1 - rows["month"].nunique() / ev["month"].nunique())
        del ev
        feats = prepare.feature_table(rows)
        cfg = series_v1.window_config(w)
        est = {}
        models = harmonize.refit_models(
            cfg,
            as_float(harmonize.lgb_inputs(train, cfg)),
            train[LABEL].to_numpy(float),
            cfg["rounds"],
        )
        est["e028_global"] = harmonize.models_predict(models, feats, cfg)
        del models
        est["m1s"] = harmonize.fit_m1s(train, 20.0)(feats)
        est["qm"] = harmonize.fit_qm(train)(feats)
        est["m0"] = harmonize.fit_m0(train)(feats)
        n_train = len(train)
        del train
        demo_train = prepare.window(demo, w)[0]
        est["e028_s11"] = harmonize.models_predict(freeze.fixed_fit(cfg, demo_train), feats, cfg)
        res[w] = {
            "train_rows": n_train,
            "eval_rows": int(len(rows)),
            "excluded_share": excluded,
            "rectangles": {k: int(v["rect_id"].nunique()) for k, v in rect.items()},
            "methods": score_methods(rows, est, rect),
        }
        print(f"{w}: scored in {time.time() - t0:.0f} s", flush=True)
    summary = summarise(res)
    path = work() / "scores_full.json"
    path.write_text(json.dumps(res, default=float) + "\n", encoding="utf-8")
    write_report(summary)
    (data_dir() / "G_scores.done").write_text("ok\n")
    return summary


KEEP = (
    "male",
    "male_all",
    "n_primary",
    "n_rectangles",
    "zero_ge1",
    "zero_ge5",
    "low_mae",
    "total_bias_mean_abs",
    "season_corr_mean",
    "male_by_region",
    "season_corr",
)


def summarise(res: dict) -> dict:
    windows = list(prepare.WINDOWS)
    out: dict = {"windows": {}, "combined": {}, "bootstrap_vs_m1s": {}}
    for w in windows:
        out["windows"][w] = {
            k: res[w][k] for k in ("train_rows", "eval_rows", "excluded_share", "rectangles")
        }
        out["windows"][w]["methods"] = {
            m: {scope: {k: s[k] for k in KEEP} for scope, s in res[w]["methods"][m].items()}
            for m in METHODS
        }
        out["windows"][w]["total_bias"] = {
            m: res[w]["methods"][m]["all"]["total_bias"] for m in METHODS
        }
    for m in METHODS:
        out["combined"][m] = {}
        for scope in ("all", "demo", "gfed"):
            ss = [res[w]["methods"][m][scope] for w in windows]
            regs = sorted(set().union(*[s["male_by_region"] for s in ss]))
            out["combined"][m][scope] = {
                "male": float(np.mean([s["male"] for s in ss])),
                "male_by_region": {
                    r: float(
                        np.mean([s["male_by_region"][r] for s in ss if r in s["male_by_region"]])
                    )
                    for r in regs
                },
            }
    for m in METHODS:
        if m == "m1s":
            continue
        out["bootstrap_vs_m1s"][m] = {}
        for scope in ("all", "demo", "gfed"):
            a = {w: res[w]["methods"]["m1s"][scope] for w in windows}
            b = {w: res[w]["methods"][m][scope] for w in windows}
            out["bootstrap_vs_m1s"][m][scope] = evaluate.bootstrap_diff(a, b)
    fz = series_v1.frozen_config()
    out["demo_s11"] = {
        w: {
            "e028_s11_on_demo_cells": fz["validation_windows"][w]["score"],
            "male_by_region": fz["validation_windows"][w]["male_by_region"],
        }
        for w in windows
    }
    return out


def fmt(v, d: int = 3) -> str:
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{d}f}"


def write_report(s: dict) -> None:
    (ROOT / "reports" / "global-scores.json").write_text(
        json.dumps(s, indent=1, default=float) + "\n", encoding="utf-8", newline="\n"
    )
    names = {
        "e028_global": "E028 global retrain",
        "m1s": "M1s λ=20",
        "qm": "QM",
        "m0": "M0",
        "e028_s11": "E028 (S11, trained on the 3 demo regions only; reference)",
    }
    c = s["combined"]
    L = [
        "# Global validation scores (stage G)",
        "",
        "> Generated by `uv run python -X utf8 -m harmonization.series_global scores`; method in "
        "`docs/decisions/0013`. Frozen grading function `evaluate.score`, frozen E028 parameters "
        "and numbers of trees; only the two validation windows are used (main window: train "
        "2016-01–2021-06, evaluate 2014–2015; auxiliary window: train 2018-01–2021-06, "
        "evaluate 2016–2017). **No model is re-selected and the test set is not touched**: these "
        "scores are only reported, and the test scores remain S11's `reports/final-test.md`.",
        "",
        "## 1. Overall scores "
        "(MALE averaged over the two windows with equal weights; lower is better)",
        "",
        "| Method | All rectangles (demo + GFED) | GFED rectangles only | Demo rectangles only |",
        "|---|---:|---:|---:|",
    ]
    for m in METHODS:
        L.append(
            f"| {names[m]} | {fmt(c[m]['all']['male'])} | {fmt(c[m]['gfed']['male'])} | "
            f"{fmt(c[m]['demo']['male'])} |"
        )
    fz = s["demo_s11"]
    demo_ref = np.mean([fz[w]["e028_s11_on_demo_cells"]["male"] for w in fz])
    L += [
        "",
        "Reference: the combined MALE of E028 in S10/S11 on the demo regions (trained and scored "
        f"on the cells of the 3 demo regions only) is {demo_ref:.4f}.",
        "",
        "MALE difference from M1s (method − M1s, negative means better than M1s; "
        '"region × year" block resampling 2000 times):',
        "",
        "| Method | Scope | Difference | Standard error | 95% interval |",
        "|---|---|---:|---:|---|",
    ]
    for m, by in s["bootstrap_vs_m1s"].items():
        for scope, b in by.items():
            ci = b["ci95"]
            L.append(
                f"| {names[m]} | {scope} | {fmt(b['diff'])} | {fmt(b['se'])} | "
                f"{fmt(ci[0]) if ci else '–'} to {fmt(ci[1]) if ci else '–'} |"
            )
    L += [
        "",
        "## 2. By region (MALE averaged over the two windows)",
        "",
        "GFED regions use their 150 random rectangles; demo regions use their own 200 "
        'rectangles each. The "S11 demo training" column for the demo regions is the score '
        "computed on the demo regions at the S11 freeze (`results/freeze.json`), i.e. the "
        "original demo-region result.",
        "",
        "| Region | "
        + " | ".join(names[m] for m in METHODS)
        + " | S11 demo training (original result) |",
        "|---|" + "---:|" * (len(METHODS) + 1),
    ]
    regs = sorted(c["e028_global"]["all"]["male_by_region"], key=lambda r: (r.islower(), r))
    for r in regs:
        vals = [fmt(c[m]["all"]["male_by_region"].get(r)) for m in METHODS]
        old = [fz[w]["male_by_region"].get(r) for w in fz]
        old_v = fmt(float(np.mean(old))) if all(v is not None for v in old) else "–"
        label = f"{r} ({GFED_NAMES[r]})" if r in GFED_NAMES else r
        L.append(f"| {label} | " + " | ".join(vals) + f" | {old_v} |")
    L += [
        "",
        "## 3. Auxiliary metrics (all rectangles, listed separately for each window)",
        "",
        "| Window | Method | Zero hotspots Ĥ≥1 | Zero hotspots Ĥ≥5 | 1–9 hotspots MAE "
        "| Region-year total bias (mean absolute) | Seasonal corr. |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for w, ws in s["windows"].items():
        for m in METHODS:
            a = ws["methods"][m]["all"]
            L.append(
                f"| {w} | {names[m]} | {fmt(a['zero_ge1'])} | {fmt(a['zero_ge5'])} | "
                f"{fmt(a['low_mae'], 2)} | {fmt(a['total_bias_mean_abs'])} | "
                f"{fmt(a['season_corr_mean'])} |"
            )
    L += [
        "",
        "## 4. Size",
        "",
        "| Window | Training rows | Evaluation rows | Share of months excluded for missing data "
        "| Rectangles (all / GFED / demo) |",
        "|---|---:|---:|---:|---|",
    ]
    for w, ws in s["windows"].items():
        r = ws["rectangles"]
        L.append(
            f"| {w} | {ws['train_rows']:,} | {ws['eval_rows']:,} | {ws['excluded_share']:.3f} | "
            f"{r['all']} / {r['gfed']} / {r['demo']} |"
        )
    L.append("")
    (ROOT / "reports" / "global-scores.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


# --- deploy inputs ----------------------------------------------------------------------------
def masks(x: pd.DataFrame) -> dict:
    """Source masks of series_v1.build."""
    ok = series_v1.ok
    is_train = (x["role"] == "train").to_numpy()
    aqua_ok, terra_ok = ok(x, "aqua"), ok(x, "terra")
    use_terra = (~aqua_ok & terra_ok) | x["aqua_count"].isna().to_numpy()
    snpp_ok = is_train & ok(x, "snpp")
    n20_ok = is_train & ~snpp_ok & ok(x, "noaa20")
    return {
        "is_train": is_train,
        "aqua_ok": aqua_ok,
        "terra_ok": terra_ok,
        "use_terra": use_terra,
        "snpp_ok": snpp_ok,
        "n20_ok": n20_ok,
        "model_rows": ~snpp_ok & ~n20_ok,
    }


SUM_KEY = prepare.KEY + ["region", "cal_month"]


def ratio_sums() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cell x calendar-month sums behind the bridge (Terra -> Aqua, every cell) and the
    continuation (NOAA-20 -> S-NPP, training cells) ratios. m1s_ratios only ever sums its
    rows, so the sums give exactly the ratios of series_v1 (counts are whole numbers)."""
    b_parts, c_parts = [], []
    for k in band_ids():
        x = global_grid.load(band=k)
        b_parts.append(bridge_sums(x))
        c_parts.append(cont_sums(x))
    return pd.concat(b_parts, ignore_index=True), pd.concat(c_parts, ignore_index=True)


def band_ids() -> list[int]:
    return sorted(int(p.stem[5:]) for p in global_grid.out_dir().glob("band_*.parquet"))


def bridge_sums(x: pd.DataFrame) -> pd.DataFrame:
    """The rows of series_v1.bridge_ratios, summed per cell x calendar month."""
    m = series_v1.span(x, series_v1.BRIDGE_FIT) & series_v1.ok(x, "terra") & series_v1.ok(x, "aqua")
    return x[m].groupby(SUM_KEY)[["terra_count", "aqua_count"]].sum().reset_index()


def cont_sums(x: pd.DataFrame) -> pd.DataFrame:
    """The rows of the continuation fit in series_v1.build, summed per cell x calendar month."""
    m = (
        (x["role"] == "train").to_numpy()
        & series_v1.span(x, series_v1.CONT_FIT)
        & series_v1.ok(x, "snpp")
        & series_v1.ok(x, "noaa20")
    )
    return x[m].groupby(SUM_KEY)[["noaa20_count", "snpp_count"]].sum().reset_index()


def bridge_from(sums: pd.DataFrame) -> dict:
    return harmonize.m1s_ratios(sums, series_v1.LAM, a_col="terra_count", v_col="aqua_count")


def cont_from(sums: pd.DataFrame) -> dict:
    return harmonize.m1s_ratios(sums, series_v1.LAM, a_col="noaa20_count", v_col="snpp_count")


def model_features(x: pd.DataFrame, mk: dict, bridge: dict) -> pd.DataFrame:
    """Model inputs of the model rows (Terra-made Aqua inputs where use_terra), as in
    series_v1.build."""
    feats = prepare.feature_table(x)
    use_terra = mk["use_terra"]
    if use_terra.any():
        t_feats = prepare.feature_table(series_v1.terra_inputs(x[use_terra], bridge))
        for c in feats.columns:
            feats[c] = feats[c].astype(float)
            feats.loc[use_terra, c] = t_feats[c].to_numpy(float)
    return feats[mk["model_rows"]].reset_index(drop=True)


def unit_names(cells: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Region names (GFED regions, then holdout regions) and box names (config/regions.json)."""
    regs = sorted(r for r in cells["region"].unique() if r in GFED_NAMES)
    regs += [r["name"] for r in regions() if r["role"] == "holdout"]
    return regs, [r["name"] for r in regions()]


def box_codes(box: pd.Series, boxes: list[str]) -> np.ndarray:
    """Index of each cell's box in `boxes`; -1 for cells outside every box (box == "")."""
    return pd.Categorical(box.where(box.isin(boxes)), categories=boxes).codes.astype(np.int8)


def inputs() -> dict:
    """Ratios, the deduplicated model rows of every band and the row bookkeeping."""
    t0 = time.time()
    bsum, csum = ratio_sums()
    bsum.to_parquet(work("inputs") / "bridge_sums.parquet", index=False)
    csum.to_parquet(work("inputs") / "cont_sums.parquet", index=False)
    bridge = bridge_from(bsum)
    cells = global_grid.load_cells()
    regs, boxes = unit_names(cells)
    months = grid.month_range()
    reps, info = [], {"bands": {}, "regions": regs, "boxes": boxes, "months": months}
    arrays: dict[str, list] = {k: [] for k in ("inv", "lat", "lon", "mon", "reg", "box")}
    offset = 0
    for k in band_ids():
        x = global_grid.load(band=k)
        mk = masks(x)
        feats = model_features(x, mk, bridge)
        rep, inv = compact(feats)
        rows = x[mk["model_rows"]].reset_index(drop=True)
        box = rows[prepare.KEY].merge(cells[prepare.KEY + ["box"]], on=prepare.KEY, how="left")
        arrays["inv"].append(inv + offset)
        arrays["lat"].append(rows["lat_idx"].to_numpy(np.int16))
        arrays["lon"].append(rows["lon_idx"].to_numpy(np.int16))
        arrays["mon"].append(np.searchsorted(months, rows["month"].to_numpy()).astype(np.int16))
        arrays["reg"].append(pd.Categorical(rows["region"], categories=regs).codes.astype(np.int8))
        arrays["box"].append(box_codes(box["box"], boxes))
        reps.append(rep)
        offset += len(rep)
        info["bands"][k] = {
            "rows": int(len(x)),
            "model_rows": int(len(feats)),
            "distinct": len(rep),
        }
        print(
            f"band {k:02d}: {len(x)} rows, {len(feats)} model rows, {len(rep)} distinct "
            f"({time.time() - t0:.0f} s)",
            flush=True,
        )
    rep = pd.concat(reps, ignore_index=True)
    rep.to_parquet(work("inputs") / "distinct.parquet", index=False)
    np.savez(work("inputs") / "rows.npz", **{k: np.concatenate(v) for k, v in arrays.items()})
    info["model_rows"] = int(sum(b["model_rows"] for b in info["bands"].values()))
    info["distinct"] = int(len(rep))
    (work("inputs") / "inputs.json").write_text(json.dumps(info, indent=1) + "\n", "utf-8")
    return info


# --- resamples --------------------------------------------------------------------------------
def setup(window: str) -> tuple[dict, pd.DataFrame, np.ndarray, pd.Series, dict]:
    """(config, model inputs, label, months) of the training rows, and what to predict."""
    df = window_table()
    if window == "deploy":
        cfg = series_v1.frozen_config()["config"]
        train = freeze.training_table(df, "test")
        del df
        target = {"feats": pd.read_parquet(work("inputs") / "distinct.parquet")}
        ref = series_v1.frozen_config()["resamples"]["years_drawn"]
    else:
        cfg = series_v1.window_config(window)
        train, ev = prepare.window(df, window)
        del df
        rows = ev[ev["usable"].to_numpy()].reset_index(drop=True)
        del ev
        rep, inv = compact(prepare.feature_table(rows))
        regs = sorted(rows["region"].unique())
        mon = sorted(rows["month"].unique())
        g = pd.Categorical(rows["region"], categories=regs).codes.astype(np.int64) * len(mon)
        g += np.searchsorted(mon, rows["month"].to_numpy())
        target = {
            "feats": rep,
            "inv": inv,
            "group": g,
            "regions": regs,
            "months": mon,
            "V": np.bincount(g, rows[LABEL].to_numpy(float), len(regs) * len(mon)),
        }
        meta = json.loads((data_dir() / "s11" / f"{window}.json").read_text(encoding="utf-8"))
        ref = meta["draws"]
    x = as_float(harmonize.lgb_inputs(train, cfg))
    y = train[LABEL].to_numpy(float)
    months = train["month"].reset_index(drop=True)
    target["ref_draws"] = ref
    return cfg, x, y, months, target


def resample(window: str, part: int = 0, of: int = 1, n: int = RESAMPLES, max_new: int = 0) -> None:
    """Fit and save the draws of one part; finished draws are skipped, so a rerun resumes.
    `max_new` > 0 stops after that many new draws (a fresh process then starts with a clean
    heap; long runs grew in committed memory)."""
    t0 = time.time()
    d = work("resamples", window)
    todo = [b for b in range(-1, n) if (b + 1) % of == part]
    names = ["est.npy" if b < 0 else f"rs_{b:03d}.npy" for b in todo]
    if (d / "meta.json").exists() and all((d / f).exists() for f in names):
        print(f"{window}: all {len(todo)} draws of part {part}/{of} already done")
        return
    cfg, x, y, months, target = setup(window)
    draws = freeze.year_blocks(months, n, settings()["seeds"]["resampling"])
    if [d[0] for d in draws] != target["ref_draws"][:n]:
        raise SystemExit("resample draws differ from the sealed S11 draws")
    if window != "deploy":
        np.save(d / "V.npy", target["V"])
        (d / "groups.json").write_text(
            json.dumps({"regions": target["regions"], "months": target["months"]}) + "\n", "utf-8"
        )
    new = 0
    for b in todo:
        path = d / ("est.npy" if b < 0 else f"rs_{b:03d}.npy")
        if path.exists():
            continue
        if max_new and new >= max_new:
            print(f"{window}: stopping after {new} new draws (--max-new)", flush=True)
            return
        if b < 0:
            models = harmonize.refit_models(cfg, x, y, cfg["rounds"])
        else:
            idx = draws[b][1]
            models = harmonize.refit_models(cfg, x.iloc[idx], y[idx], cfg["rounds"])
        p = harmonize.models_predict(models, target["feats"], cfg)
        if window == "deploy":
            arr = p if b < 0 else p.astype(np.float32)
        else:
            arr = np.bincount(target["group"], p[target["inv"]], len(target["V"]))
        tmp = path.with_suffix(".tmp.npy")
        np.save(tmp, arr)
        tmp.replace(path)
        print(f"{window}: {path.name} ({time.time() - t0:.0f} s)", flush=True)
        new += 1
        del models, p, arr
        gc.collect()
    meta = {
        "window": window,
        "train_rows": int(len(x)),
        "config": freeze.plain(cfg),
        "draws": [d_[0] for d_ in draws],
        "threads": harmonize.THREADS,
    }
    (d / "meta.json").write_text(json.dumps(meta, indent=1) + "\n", "utf-8")


def window_totals(w: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list, list]:
    d = work("resamples", w)
    g = json.loads((d / "groups.json").read_text(encoding="utf-8"))
    rs = np.stack([np.load(d / f"rs_{b:03d}.npy") for b in range(RESAMPLES)], axis=1)
    return np.load(d / "V.npy"), np.load(d / "est.npy"), rs, g["regions"], g["months"]


def calibrate() -> dict:
    """The frozen calibration (freeze.calibration) on the global validation windows: region x
    month totals of the GFED regions, raw coverage and the pooled interval scale."""
    parts, out = [], {}
    for w in prepare.WINDOWS:
        v, e, rs, regs, mon = window_totals(w)
        lo, hi = np.percentile(rs, 5, axis=1), np.percentile(rs, 95, axis=1)
        out[w] = {
            "region_months": int(len(v)),
            "coverage_raw": float(freeze.covered(v, e, lo, hi, 1.0).mean()),
        }
        parts.append((v, e, lo, hi))
    v, e, lo, hi = (np.concatenate(p) for p in zip(*parts, strict=True))
    scale, cov = freeze.interval_scale(v, e, lo, hi)
    out["pooled"] = {
        "region_months": int(len(v)),
        "coverage_raw": float(freeze.covered(v, e, lo, hi, 1.0).mean()),
        "interval_scale": scale,
        "coverage_calibrated": cov,
    }
    for w, p in zip(prepare.WINDOWS, parts, strict=True):
        out[w]["coverage_calibrated"] = float(freeze.covered(*p, scale).mean())
    (work() / "calibration.json").write_text(json.dumps(out, indent=1) + "\n", "utf-8")
    print(json.dumps(out, indent=1))
    return out


# --- dataset ----------------------------------------------------------------------------------
REGION_BOXES = {r["name"]: r for r in regions()}


def unit_meta(name: str, cells: pd.DataFrame) -> dict:
    """label, role, bbox of a region or box for the front-end file."""
    if name in REGION_BOXES:
        r = REGION_BOXES[name]
        return {
            "name": name,
            "label": r["label"],
            "role": r["role"],
            "bbox": [r["west"], r["south"], r["east"], r["north"]],
        }
    cell = settings()["grid"]["cell_deg"]
    c = cells[cells["region"] == name]
    bbox = [
        -180 + float(c["lon_idx"].min()) * cell,
        -90 + float(c["lat_idx"].min()) * cell,
        -180 + float(c["lon_idx"].max() + 1) * cell,
        -90 + float(c["lat_idx"].max() + 1) * cell,
    ]
    return {
        "name": name,
        "label": f"GFED4.1s basis region {name} ({GFED_NAMES[name]}), without the holdout boxes",
        "role": "train",
        "bbox": bbox,
    }


def build(n: int = RESAMPLES, bands: list[int] | None = None, root: Path | None = None) -> dict:
    """The global dataset. `n`, `bands` and `root` exist for a dry run on a few bands
    (no recount, scale 1 when no calibration yet); the release uses the defaults."""
    t0 = time.time()
    full_run = bands is None and n == RESAMPLES
    fz = series_v1.frozen_config()
    info = json.loads((work("inputs") / "inputs.json").read_text(encoding="utf-8"))
    regs, boxes, months = info["regions"], info["boxes"], info["months"]
    cells = global_grid.load_cells()
    rows = dict(np.load(work("inputs") / "rows.npz"))
    all_bands = band_ids()
    bands = all_bands if bands is None else bands
    if bands != all_bands:
        sizes = [info["bands"][str(k)]["model_rows"] for k in all_bands]
        starts = np.concatenate([[0], np.cumsum(sizes)])
        pick = [np.arange(starts[i], starts[i + 1]) for i, k in enumerate(all_bands) if k in bands]
        rows = {key: v[np.concatenate(pick)] for key, v in rows.items()}
    rd = work("resamples", "deploy")
    est_c = np.load(rd / "est.npy")
    rs_c = np.stack([np.load(rd / f"rs_{b:03d}.npy") for b in range(n)], axis=1)
    lo_c = np.percentile(rs_c, 5, axis=1)
    hi_c = np.percentile(rs_c, 95, axis=1)
    print(f"cell quantiles of {len(rs_c)} distinct rows ({time.time() - t0:.0f} s)", flush=True)

    # resampled totals per region x month and box x month (model rows only)
    G, B = len(regs) * len(months), len(boxes) * len(months)
    g_reg = rows["reg"].astype(np.int64) * len(months) + rows["mon"]
    in_box = rows["box"] >= 0
    g_box = rows["box"][in_box].astype(np.int64) * len(months) + rows["mon"][in_box]
    rs_reg, rs_box = np.zeros((G, n)), np.zeros((B, n))
    for b in range(n):
        full = rs_c[rows["inv"], b].astype(float)
        rs_reg[:, b] = np.bincount(g_reg, full, G)
        rs_box[:, b] = np.bincount(g_box, full[in_box], B)
    has_reg = np.bincount(g_reg, minlength=G) > 0
    has_box = np.bincount(g_box, minlength=B) > 0
    del rs_c

    cont = cont_from(pd.read_parquet(work("inputs") / "cont_sums.parquet"))
    sp_last = settings()["api_2026"]["sp_last_day"]
    root = root or out_root()
    (root / "frontend").mkdir(parents=True, exist_ok=True)
    writer = None
    keep: dict[str, list] = {
        k: [] for k in ("lat", "lon", "mon", "reg", "box", "est", "m0", "a", "t", "v")
    }
    tot_parts, obs_parts, pos = [], [], 0
    checks = {"observed_rows": 0, "observed_equal": True}
    reg_cat = pd.CategoricalDtype(regs + ["_none"])
    gfed_cat = pd.CategoricalDtype(sorted(GFED_NAMES))
    for k in bands:
        x = global_grid.load(band=k)
        mk = masks(x)
        nm = int(mk["model_rows"].sum())
        sel = slice(pos, pos + nm)
        pos += nm
        inv = rows["inv"][sel]
        n20 = np.zeros(len(x))
        if mk["n20_ok"].any():
            n20[mk["n20_ok"]] = harmonize.apply_ratios(
                cont, x[mk["n20_ok"]].reset_index(drop=True), "noaa20_count"
            )
        est = np.where(mk["snpp_ok"], x[LABEL].to_numpy(float), n20)
        est[mk["model_rows"]] = est_c[inv]
        lo, hi = est.copy(), est.copy()
        lo[mk["model_rows"]] = lo_c[inv]
        hi[mk["model_rows"]] = hi_c[inv]
        source = np.where(
            mk["snpp_ok"],
            "snpp",
            np.where(
                mk["n20_ok"],
                "noaa20_scaled",
                np.where(mk["use_terra"], "model_terra_bridge", "model_aqua"),
            ),
        )
        viirs = mk["snpp_ok"] | mk["n20_ok"]
        m = x["month"].to_numpy()
        nrt = np.where(viirs, m > sp_last["VIIRS"][:7], m > sp_last["MODIS"][:7])
        input_complete = viirs | np.where(mk["use_terra"], mk["terra_ok"], mk["aqua_ok"])
        raw_modis = x["aqua_count"].fillna(x["terra_count"]).to_numpy(float)
        m0 = np.where(m < "2012-02", raw_modis, np.where(mk["snpp_ok"], est, np.nan))
        meta_cells = x[prepare.KEY].merge(
            cells[prepare.KEY + ["gfed_region", "box"]], on=prepare.KEY, how="left"
        )
        out = pd.DataFrame(
            {
                "lat_idx": x["lat_idx"].astype("int16"),
                "lon_idx": x["lon_idx"].astype("int16"),
                "region": pd.Categorical(x["region"], dtype=reg_cat),
                "gfed_region": pd.Categorical(meta_cells["gfed_region"], dtype=gfed_cat),
                "role": x["role"],
                "month": x["month"],
                "est": est.astype("float32"),
                "lo_90": lo.astype("float32"),
                "hi_90": hi.astype("float32"),
                "source": pd.Categorical(source, categories=series_v1.SOURCES),
                "nrt": nrt,
                "input_complete": input_complete,
                "est_m0": m0.astype("float32"),
                "aqua_count": x["aqua_count"].astype("float32"),
                "terra_count": x["terra_count"].astype("float32"),
                "snpp_count": np.where(mk["is_train"], x[LABEL], np.nan).astype("float32"),
            }
        )
        if out["est"].isna().any() or (out["est"] < 0).any():
            raise SystemExit("cell-months without a valid estimate")
        obs = (out["source"] == "snpp").to_numpy()
        checks["observed_rows"] += int(obs.sum())
        checks["observed_equal"] &= bool((out["est"][obs] == out["snpp_count"][obs]).all())
        if not checks["observed_equal"]:
            raise SystemExit("observed S-NPP months must equal the observation")
        obs_parts.append(
            out[obs].groupby(["region", "month"], observed=True)["est"].sum().astype(float)
        )
        table = pa.Table.from_pandas(out, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(
                root / f"dataset_{VERSION}.parquet", table.schema, compression="zstd"
            )
        writer.write_table(table)
        tot_parts.append(
            out.groupby(["region", "month"], observed=True).agg(
                est=("est", lambda s: s.astype(float).sum()),
                est_m0=("est_m0", lambda s: s.astype(float).sum(min_count=1)),
                aqua_count=("aqua_count", lambda s: s.astype(float).sum(min_count=1)),
                terra_count=("terra_count", lambda s: s.astype(float).sum(min_count=1)),
                snpp_count=("snpp_count", lambda s: s.astype(float).sum(min_count=1)),
                nrt=("nrt", "all"),
                input_complete=("input_complete", "all"),
                sources=("source", lambda s: tuple(sorted(set(s.astype(str))))),
            )
        )
        keep["lat"].append(out["lat_idx"].to_numpy())
        keep["lon"].append(out["lon_idx"].to_numpy())
        keep["mon"].append(np.searchsorted(months, out["month"].to_numpy()).astype(np.int16))
        keep["reg"].append(out["region"].cat.codes.to_numpy())
        keep["box"].append(box_codes(meta_cells["box"], boxes))
        keep["est"].append(out["est"].to_numpy())
        keep["m0"].append(out["est_m0"].to_numpy())
        keep["a"].append(out["aqua_count"].to_numpy())
        keep["t"].append(out["terra_count"].to_numpy())
        keep["v"].append(out["snpp_count"].to_numpy())
        print(f"band {k:02d}: {len(out)} rows ({time.time() - t0:.0f} s)", flush=True)
    writer.close()
    if pos != len(rows["inv"]):
        raise SystemExit("model rows differ from the inputs step")
    arr = {k: np.concatenate(v) for k, v in keep.items()}

    calibrate_on, _, test_cov = series_v1.interval_rule()
    cal_path = work() / "calibration.json"
    if cal_path.exists():
        cal = json.loads(cal_path.read_text(encoding="utf-8"))
    elif not full_run:
        cal = {"pooled": {"interval_scale": 1.0}, "dry_run": True}
    else:
        raise SystemExit("run `calibrate` first")
    scale = cal["pooled"]["interval_scale"]

    def totals(names, codes, rs_t, has, src=None) -> pd.DataFrame:
        parts = []
        for i, name in enumerate(names):
            mask = codes == i
            mon = arr["mon"][mask]
            t = pd.DataFrame({"month": months})
            for col, key in (
                ("est", "est"),
                ("est_m0", "m0"),
                ("aqua_count", "a"),
                ("terra_count", "t"),
                ("snpp_count", "v"),
            ):
                vals = arr[key][mask].astype(float)
                okv = ~np.isnan(vals)
                s = np.bincount(mon[okv], vals[okv], len(months))
                cnt = np.bincount(mon[okv], minlength=len(months))
                t[col] = np.where(cnt > 0, s, np.nan) if col != "est" else s
            sl = slice(i * len(months), (i + 1) * len(months))
            e = t["est"].to_numpy()
            lo, hi = e.copy(), e.copy()
            h = has[sl]
            lo[h] = np.percentile(rs_t[sl][h], 5, axis=1)
            hi[h] = np.percentile(rs_t[sl][h], 95, axis=1)
            if calibrate_on:
                lo = np.maximum(0.0, e - scale * (e - lo))
                hi = e + scale * (hi - e)
            t["lo_90"], t["hi_90"] = lo, hi
            t.insert(0, "region", name)
            parts.append(t)
        return pd.concat(parts, ignore_index=True)

    tot_reg = totals(regs, arr["reg"], rs_reg, has_reg)
    tot_box = totals(boxes, arr["box"], rs_box, has_box)
    flags = (
        pd.concat(tot_parts)
        .groupby(level=[0, 1], observed=True)
        .agg(
            nrt=("nrt", "all"),
            input_complete=("input_complete", "all"),
            sources=("sources", lambda s: tuple(sorted(set().union(*s)))),
        )
    )
    if (flags["sources"].map(len) > 1).any():
        raise SystemExit("more than one source in a region-month")
    flags["source"] = flags["sources"].map(lambda s: s[0])
    flags = flags.drop(columns="sources").reset_index()
    tot_reg = tot_reg.merge(flags, on=["region", "month"], how="left")
    # a box is one holdout region, or training cells of one or more regions; training cells
    # share the sensor status of every month, so their regions' flags must agree
    box_flags = []
    for name in boxes:
        reg = cells.loc[cells["box"] == name, "region"].unique()
        f = (
            flags[flags["region"].isin(reg)]
            .groupby("month", as_index=False)
            .agg(
                nrt=("nrt", "all"),
                input_complete=("input_complete", "all"),
                source=("source", lambda s: s.iloc[0] if s.nunique() == 1 else None),
            )
        )
        if f["source"].isna().any():
            raise SystemExit(f"box {name}: its regions disagree on a month's source")
        box_flags.append(f.assign(region=name))
    tot_box = tot_box.merge(pd.concat(box_flags), on=["region", "month"], how="left")
    cols = [
        "region",
        "month",
        "est",
        "lo_90",
        "hi_90",
        "est_m0",
        "source",
        "nrt",
        "input_complete",
        "aqua_count",
        "terra_count",
        "snpp_count",
    ]
    tot_reg, tot_box = tot_reg[cols], tot_box[cols]
    est_direct = pd.concat(tot_parts).groupby(level=[0, 1], observed=True)["est"].sum()
    idx = pd.MultiIndex.from_frame(tot_reg[["region", "month"]])
    direct = est_direct.reindex(idx).fillna(0).to_numpy(float)
    if not np.allclose(tot_reg["est"].to_numpy(float), direct, rtol=1e-6, atol=1e-6):
        bad = np.flatnonzero(~np.isclose(tot_reg["est"].to_numpy(float), direct, 1e-6, 1e-6))
        print(tot_reg.iloc[bad[:5]][["region", "month", "est"]], direct[bad[:5]])
        raise SystemExit("region totals disagree")

    obs_tot = pd.concat(obs_parts).groupby(level=[0, 1]).sum()
    rec = recount(obs_tot, cells) if full_run else {"skipped": "dry run on a band subset"}
    if rec.get("mismatches"):
        raise SystemExit(f"observed S-NPP months differ from the cleaned observations: {rec}")
    meta = {
        "version": VERSION,
        "scope": "global (config/regions-global.json): GFED4.1s basis regions; the holdout boxes "
        "of config/regions.json are separate regions and never trained on",
        "model": "LightGBM E028 (two-stage), frozen parameters and rounds of results/freeze.json, "
        "refitted on the global training cells 2014-01..2021-06 (docs/decisions/0013)",
        "freeze": "results/freeze.json",
        "freeze_commit": fz["code_commit"],
        "training": {
            "cells": "every global cell with role train",
            "months": ["2014-01", "2021-06"],
            "rows": (
                json.loads((rd / "meta.json").read_text("utf-8"))["train_rows"]
                if (rd / "meta.json").exists()
                else None
            ),
        },
        "inputs": fz["inputs"],
        "rounds": fz["rounds"],
        "resamples": n,
        "interval": {
            "calibrated": calibrate_on,
            "interval_scale": scale,
            "scale_from": "global validation windows (docs/decisions/0013)",
            "validation_coverage": cal,
            "s11_test_region_month_coverage_raw": test_cov,
        },
        "bridge_fit": series_v1.BRIDGE_FIT,
        "continuation_fit": series_v1.CONT_FIT,
        "lambda": series_v1.LAM,
        "rows": int(len(arr["est"])),
        "cells": int(len(cells)),
        "acceptance_recount": rec,
        "checks": checks,
        "test_scores": "none for this version: the only test is S11 (reports/final-test.md, "
        "three-region model); global validation scores in reports/global-scores.md",
    }
    tot_reg.to_csv(
        root / f"region_totals_{VERSION}.csv", index=False, lineterminator="\n", float_format="%.6g"
    )
    tot_box.to_csv(
        root / f"box_totals_{VERSION}.csv", index=False, lineterminator="\n", float_format="%.6g"
    )
    write_frontend(arr, cells, regs, boxes, months, tot_reg, tot_box, meta, root)
    write_resamples20(rows, months, min(series_v1.FRONTEND_RESAMPLES, n), root)
    (root / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", "utf-8", newline="\n")
    lines = package(root)
    if full_run:
        (data_dir() / "G_build.done").write_text("ok\n")
    print(f"built in {time.time() - t0:.0f} s")
    print("\n".join(lines))
    return meta


def recount(obs: pd.Series, cells: pd.DataFrame) -> dict:
    """Acceptance (task card): region x month totals of every observed S-NPP month, recounted
    straight from the cleaned S-NPP points (S04), equal the dataset exactly."""
    files = sorted((data_dir() / "processed" / "clean" / "snpp").glob("*.parquet"))
    if not files:
        return {"skipped": "no cleaned S-NPP points in this data folder (data-v0 release)"}
    regs = sorted(obs.index.get_level_values(0).unique())
    code = np.full(grid.NLAT * grid.NLON, -1, np.int64)
    tr = cells[cells["region"].isin(regs) & (cells["role"] == "train")]
    code[tr["lat_idx"].to_numpy() * grid.NLON + tr["lon_idx"].to_numpy()] = pd.Categorical(
        tr["region"], categories=regs
    ).codes
    months = grid.month_range()
    first = pd.Period(months[0], "M")
    counts = np.zeros(len(regs) * len(months), np.int64)
    for f in files:
        t = pq.read_table(f, columns=["latitude", "longitude", "acq_date"]).to_pandas()
        i, j = grid.cell_index(t["latitude"].to_numpy(), t["longitude"].to_numpy())
        r = code[i.astype(np.int64) * grid.NLON + j]
        d = pd.to_datetime(t["acq_date"])
        m = (d.dt.year.to_numpy() - first.year) * 12 + d.dt.month.to_numpy() - first.month
        ok = (r >= 0) & (m >= 0) & (m < len(months))
        counts += np.bincount(r[ok] * len(months) + m[ok], minlength=len(counts))
        print(f"recount {f.stem}: {len(t)} points", flush=True)
    rec = pd.Series(
        counts, index=pd.MultiIndex.from_product([regs, months], names=["region", "month"])
    )
    got = rec.reindex(obs.index).fillna(0).to_numpy(float)
    diff = np.abs(got - obs.to_numpy(float))
    return {
        "region_months": int(len(obs)),
        "months": [
            str(obs.index.get_level_values(1).min()),
            str(obs.index.get_level_values(1).max()),
        ],
        "points": int(obs.sum()),
        "mismatches": int((diff > 0).sum()),
        "max_abs_diff": float(diff.max()) if len(diff) else 0.0,
    }


def r2(a) -> list:
    return [None if np.isnan(v) else round(float(v), 2) for v in np.asarray(a, dtype=float)]


def write_frontend(arr, cells, regs, boxes, months, tot_reg, tot_box, meta, root) -> None:
    """One gzip JSON per region and per box in the v1 format (docs/data-interface.md
    section 3), plus frontend/index.json listing them."""
    root = root / "frontend"
    index = []
    for kind, names, codes, tot in (
        ("region", regs, arr["reg"], tot_reg),
        ("box", boxes, arr["box"], tot_box),
    ):
        for i, name in enumerate(names):
            if kind == "box" and name in regs:
                continue  # holdout boxes are regions already
            mask = codes == i
            mon = arr["mon"][mask]
            if not (mon.reshape(-1, len(months)) == np.arange(len(months))).all():
                raise SystemExit(f"{name}: rows are not cell x month ordered")
            lat = arr["lat"][mask][:: len(months)]
            lon = arr["lon"][mask][:: len(months)]
            est = arr["est"][mask].reshape(-1, len(months))
            t = tot[tot["region"] == name].set_index("month").reindex(months)
            um = unit_meta(name, cells)
            data = {
                "version": VERSION,
                "region": name,
                "label": um["label"],
                "role": um["role"],
                "bbox": um["bbox"],
                "cell_deg": settings()["grid"]["cell_deg"],
                "months": months,
                "month_source": t["source"].tolist(),
                "month_nrt": [bool(v) for v in t["nrt"]],
                "month_input_complete": [bool(v) for v in t["input_complete"]],
                "cells": {
                    "lat_idx": lat.astype(int).tolist(),
                    "lon_idx": lon.astype(int).tolist(),
                },
                "est": [r2(row) for row in est],
                "totals": {
                    k: r2(t[k])
                    for k in (
                        "est",
                        "lo_90",
                        "hi_90",
                        "est_m0",
                        "aqua_count",
                        "terra_count",
                        "snpp_count",
                    )
                },
                "model": meta,
            }
            raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
            fname = f"{name}.json.gz"
            with gzip.GzipFile(root / fname, "wb", mtime=0) as f:
                f.write(raw)
            index.append({**um, "kind": kind, "file": fname, "cells": int(len(lat))})
            print(f"frontend {fname}: {len(lat)} cells", flush=True)
    text = json.dumps({"version": VERSION, "units": index}, indent=1) + "\n"
    (root / "index.json").write_text(text, "utf-8", newline="\n")


def write_resamples20(rows: dict, months: list[str], n: int, root: Path) -> int:
    """Non-zero cell estimates of the first 20 resamples (model rows), like resamples20_v1."""
    rd = work("resamples", "deploy")
    path = root / f"resamples{series_v1.FRONTEND_RESAMPLES}_{VERSION}.parquet"
    writer, total = None, 0
    mon_names = np.array(months)
    for b in range(n):
        full = np.load(rd / f"rs_{b:03d}.npy")[rows["inv"]]
        nz = full > 0
        t = pa.table(
            {
                "lat_idx": rows["lat"][nz],
                "lon_idx": rows["lon"][nz],
                "month": pa.array(mon_names[rows["mon"][nz]]),
                "resample": np.full(int(nz.sum()), b, np.int8),
                "value": full[nz].astype(np.float32),
            }
        )
        if writer is None:
            writer = pq.ParquetWriter(path, t.schema, compression="zstd")
        writer.write_table(t)
        total += int(nz.sum())
    writer.close()
    print(f"resamples20: {total} rows", flush=True)
    return total


DOCS = ("data-interface-global.md", "data-card.md", "anomaly-cases.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def package(root: Path | None = None) -> list[str]:
    """CSV of the dataset (as series_v1.package, one row group at a time), the documents,
    then SHA256SUMS of every file. Same input -> same bytes."""
    root = root or out_root()
    pf = pq.ParquetFile(root / f"dataset_{VERSION}.parquet")
    with (
        gzip.GzipFile(root / f"dataset_{VERSION}.csv.gz", "wb", mtime=0) as gz,
        io.TextIOWrapper(gz, encoding="utf-8", newline="\n") as f,
    ):
        for g in range(pf.num_row_groups):
            pf.read_row_group(g).to_pandas().to_csv(
                f, index=False, header=g == 0, lineterminator="\n", float_format="%.6g"
            )
    for name in DOCS:
        text = (ROOT / "docs" / name).read_text(encoding="utf-8").replace("\r\n", "\n")
        (root / name).write_text(text, "utf-8", newline="\n")
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    lines = [f"{sha256(p)}  {p.name}" for p in files]  # release assets are flat
    (root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", "utf-8", newline="\n")
    return lines


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for c in ("scores", "inputs", "calibrate", "build", "package"):
        sub.add_parser(c)
    r = sub.add_parser("resample")
    r.add_argument("window", choices=["deploy", *prepare.WINDOWS])
    r.add_argument("--part", type=int, default=0)
    r.add_argument("--of", type=int, default=1)
    r.add_argument("-n", type=int, default=RESAMPLES)
    r.add_argument("--max-new", type=int, default=0)
    a = p.parse_args()
    if a.cmd == "scores":
        s = scores()
        print(json.dumps({m: s["combined"][m]["all"]["male"] for m in METHODS}, indent=1))
    elif a.cmd == "inputs":
        print(json.dumps({k: v for k, v in inputs().items() if k != "bands"}, indent=1))
    elif a.cmd == "resample":
        resample(a.window, a.part, a.of, a.n, a.max_new)
    elif a.cmd == "calibrate":
        calibrate()
    elif a.cmd == "build":
        build()
    else:
        print("\n".join(package()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
