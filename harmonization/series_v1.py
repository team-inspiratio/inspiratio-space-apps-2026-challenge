"""S12: final dataset v1 with the selected model (LightGBM E028), 2000-11..2026-10, source
flags, stability intervals, front-end files and release checksums.

uv run python -X utf8 -m harmonization.series_v1 terra-check   # Terra-only inputs (validation)
uv run python -X utf8 -m harmonization.series_v1 build         # <data>/processed/v1/
uv run python -X utf8 -m harmonization.series_v1 package       # S14 files only, from the parquet

Model (docs/decisions/0009): the frozen evaluation model of S11 (results/freeze.json, E028
parameters and rounds refitted on the training regions 2014-01..2021-06) is also the production
model, because the 2012-2013 S-NPP years never reach this machine (red line 1). Its 100
year-block resamples (the draws of the sealed submission) give the stability intervals.

Source of every cell-month (`source`):
  snpp                training region, S-NPP complete month: the observed count
  noaa20_scaled       training region, S-NPP not complete but NOAA-20 complete: NOAA-20 x ratio
  model_aqua          otherwise, the model on the MODIS inputs
  model_terra_bridge  Aqua not complete but Terra complete (2000-11..2002-09 and Aqua gaps): the
                      Aqua inputs are made from Terra (counts times the Terra -> Aqua M1s ratio,
                      fitted on MODIS only, every region, docs/decisions/0005 item 6 option B),
                      then the model; low confidence
`nrt` marks values that come from near-real-time data (VIIRS after 2026-07, MODIS after
2026-08, config/settings.yaml api_2026.sp_last_day). `input_complete` is false when the sensor a
value comes from has missing days that month. Holdout regions are model estimates every month.

Intervals: `lo_90`/`hi_90` per cell-month are the 5 % / 95 % quantiles of the 100 resampled
estimates (stability only). Region x month intervals are the quantiles of the resampled region
totals; when the final test says so (docs/decisions/0008 item 5) they are widened around the
estimate by the interval_scale fixed on the validation windows. Observed and NOAA-20 months have
no model interval (lo = hi = est).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import sys

import numpy as np
import pandas as pd

from harmonization import evaluate, freeze, grid, harmonize, prepare
from harmonization.config import ROOT, data_dir, regions, settings

VERSION = "v1"
LAM = 20.0  # M1s lambda for the bridge and continuation ratios (S08)
BRIDGE_FIT = ("2003-01", "2019-12")  # stable Terra/Aqua years (reports/findings.md item 7)
CONT_FIT = ("2018-04", "2026-10")  # full NOAA-20 / S-NPP overlap
SOURCES = ["snpp", "noaa20_scaled", "model_aqua", "model_terra_bridge"]
FRONTEND_RESAMPLES = 20  # resampled versions kept per cell for user-drawn regions (proposal)
COPY = ("frp_median", "frp_p75", "low_frp_share", "pixel_area_mean", "night_share", "fire_days")
SCALED = ("count", "nbr_count")


def ok(df: pd.DataFrame, sensor: str) -> np.ndarray:
    return (df[f"{sensor}_status"] == "complete").to_numpy()


def span(df: pd.DataFrame, s: tuple[str, str]) -> np.ndarray:
    return ((df["month"] >= s[0]) & (df["month"] <= s[1])).to_numpy()


def bridge_ratios(df: pd.DataFrame) -> dict:
    """Terra -> Aqua M1s ratios from MODIS only (no VIIRS), cells of every region."""
    both = df[span(df, BRIDGE_FIT) & ok(df, "terra") & ok(df, "aqua")]
    return harmonize.m1s_ratios(both, LAM, a_col="terra_count", v_col="aqua_count")


def terra_inputs(x: pd.DataFrame, bridge: dict) -> pd.DataFrame:
    """Rows with every Aqua input made from Terra: counts x the cell's Terra -> Aqua ratio,
    the other Aqua features copied from Terra."""
    x = x.reset_index(drop=True).copy()
    k = harmonize.apply_ratios(bridge, x.assign(_one=1.0), a_col="_one")
    for f in SCALED:
        x[f"aqua_{f}"] = k * x[f"terra_{f}"].to_numpy(float)
    for f in COPY:
        x[f"aqua_{f}"] = x[f"terra_{f}"]
    return x


def frozen_config() -> dict:
    return json.loads(freeze.FREEZE.read_text(encoding="utf-8"))


def window_config(window: str) -> dict:
    return frozen_config()["validation_windows"][window]["config"]


def terra_check(df: pd.DataFrame | None = None) -> dict:
    """Validation windows only: score the model with its real inputs, the model with Terra-made
    Aqua inputs (what model_terra_bridge does), and the v0 chain (bridged Terra -> M1s)."""
    df = prepare.load_grid() if df is None else df
    bridge = bridge_ratios(df)
    rc = prepare.rectangle_cells(df.loc[df["role"] == "train", prepare.KEY].drop_duplicates())
    out: dict = {}
    for w in prepare.WINDOWS:
        train, ev = prepare.window(df, w)
        rows = ev[ev["usable"].to_numpy()].reset_index(drop=True)
        cfg = window_config(w)
        models = freeze.fixed_fit(cfg, train)
        m1s = harmonize.fit_m1s(train, LAM)
        t_rows = terra_inputs(rows, bridge)
        est = {
            "model_real_inputs": harmonize.models_predict(models, prepare.feature_table(rows), cfg),
            "model_terra_inputs": harmonize.models_predict(
                models, prepare.feature_table(t_rows), cfg
            ),
            "m1s_terra_chain": m1s(prepare.feature_table(t_rows)),
            "m1s_real_inputs": m1s(prepare.feature_table(rows)),
        }
        out[w] = {}
        for name, e in est.items():
            s = evaluate.score(rows, e, rc, prepare.LABEL)
            keep = ("male", "zero_ge1", "low_mae", "total_bias_mean_abs", "male_by_region")
            out[w][name] = {k: s[k] for k in keep}
    out["combined_male"] = {
        name: float(np.mean([out[w][name]["male"] for w in prepare.WINDOWS]))
        for name in out["main"]
    }
    return out


def interval_rule() -> tuple[bool, float, dict]:
    """docs/decisions/0008 item 5: widen the region intervals by interval_scale when the raw
    region-month coverage of either test is below 80 %."""
    scale = float(frozen_config()["submission"]["interval_scale"])
    res = json.loads((ROOT / "results" / "final-test" / "scores.json").read_text(encoding="utf-8"))
    cov = {s: res[s]["coverage"]["region_month_coverage"] for s in ("test1", "test2")}
    return any(c < 0.80 for c in cov.values()), scale, cov


def resampled(cfg: dict, train: pd.DataFrame, feats: pd.DataFrame, draws: list) -> np.ndarray:
    """Estimates of the model rows under each resample; cached in <data>/s12/ (same draws,
    same inputs -> same file), so a rerun of the build does not refit 100 models."""
    path = data_dir() / "s12" / f"resamples_{len(draws)}.npy"
    digest = hashlib.sha256(pd.util.hash_pandas_object(feats, index=False).to_numpy()).hexdigest()
    tag = path.with_suffix(".sha256")
    if path.exists() and tag.exists() and tag.read_text().strip() == digest:
        return np.load(path)
    rs = np.empty((len(feats), len(draws)), dtype=np.float32)
    for b, (_, idx) in enumerate(draws):
        m = freeze.fixed_fit(cfg, train.iloc[idx].reset_index(drop=True))
        rs[:, b] = harmonize.models_predict(m, feats, cfg)
        print(f"resample {b + 1}/{len(draws)}", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, rs)
    tag.write_text(digest + "\n")
    return rs


def build(
    df: pd.DataFrame, resamples: int = freeze.RESAMPLES, resamples_only: bool = False
) -> tuple[pd.DataFrame, dict]:
    fz = frozen_config()
    cfg = fz["config"]
    train = freeze.training_table(df, "test")
    models = freeze.fixed_fit(cfg, train)
    sub = pd.read_parquet(freeze.SUBMISSION, columns=prepare.KEY + ["month", "est_final"])
    rows = freeze.eval_rows(df, "test")
    again = harmonize.models_predict(models, prepare.feature_table(rows), cfg)
    if not np.array_equal(again, sub["est_final"].to_numpy(float)):
        raise SystemExit("the production refit does not reproduce the sealed est_final")

    x = df.reset_index(drop=True)
    is_train = (x["role"] == "train").to_numpy()
    aqua_ok, terra_ok = ok(x, "aqua"), ok(x, "terra")
    use_terra = (~aqua_ok & terra_ok) | x["aqua_count"].isna().to_numpy()
    snpp_ok = is_train & ok(x, "snpp")
    n20_ok = is_train & ~snpp_ok & ok(x, "noaa20")
    model_rows = ~snpp_ok & ~n20_ok

    bridge = bridge_ratios(x)
    feats = prepare.feature_table(x)
    if use_terra.any():
        t_feats = prepare.feature_table(terra_inputs(x[use_terra], bridge))
        for c in feats.columns:
            feats[c] = feats[c].astype(float)
            feats.loc[use_terra, c] = t_feats[c].to_numpy(float)
    feats = feats[model_rows].reset_index(drop=True)
    est_model = harmonize.models_predict(models, feats, cfg)

    both_viirs = x[is_train & span(x, CONT_FIT) & ok(x, "snpp") & ok(x, "noaa20")]
    cont = harmonize.m1s_ratios(both_viirs, LAM, a_col="noaa20_count", v_col="snpp_count")
    n20 = np.zeros(len(x))
    if n20_ok.any():
        n20[n20_ok] = harmonize.apply_ratios(cont, x[n20_ok].reset_index(drop=True), "noaa20_count")

    est = np.where(snpp_ok, x["snpp_count"].to_numpy(float), n20)
    est[model_rows] = est_model
    source = np.where(
        snpp_ok,
        "snpp",
        np.where(n20_ok, "noaa20_scaled", np.where(use_terra, "model_terra_bridge", "model_aqua")),
    )
    viirs_src = snpp_ok | n20_ok
    sp_last = settings()["api_2026"]["sp_last_day"]
    nrt = np.where(viirs_src, x["month"] > sp_last["VIIRS"][:7], x["month"] > sp_last["MODIS"][:7])
    input_complete = snpp_ok | n20_ok | np.where(use_terra, terra_ok, aqua_ok)

    # stability intervals: the S11 draws, frozen parameters and rounds
    draws = freeze.year_blocks(train["month"], resamples, settings()["seeds"]["resampling"])
    if [d[0] for d in draws] != fz["resamples"]["years_drawn"][:resamples]:
        raise SystemExit("resample draws differ from the sealed submission")
    rs = resampled(cfg, train, feats, draws)
    if resamples_only:
        return pd.DataFrame(), {}
    lo = est.copy()
    hi = est.copy()
    lo[model_rows] = np.percentile(rs, 5, axis=1)
    hi[model_rows] = np.percentile(rs, 95, axis=1)

    raw_modis = x["aqua_count"].fillna(x["terra_count"]).to_numpy(float)
    m0 = np.where(x["month"] < "2012-02", raw_modis, np.where(snpp_ok, est, np.nan))
    out = pd.DataFrame(
        {
            "lat_idx": x["lat_idx"].astype("int16"),
            "lon_idx": x["lon_idx"].astype("int16"),
            "region": x["region"],
            "role": x["role"],
            "month": x["month"],
            "est": est.astype("float32"),
            "lo_90": lo.astype("float32"),
            "hi_90": hi.astype("float32"),
            "source": pd.Categorical(source, categories=SOURCES),
            "nrt": nrt,
            "input_complete": input_complete,
            "est_m0": m0.astype("float32"),
            "aqua_count": x["aqua_count"].astype("float32"),
            "terra_count": x["terra_count"].astype("float32"),
            "snpp_count": np.where(is_train, x["snpp_count"], np.nan).astype("float32"),
        }
    )
    if out["est"].isna().any() or (out["est"] < 0).any():
        raise SystemExit("cell-months without a valid estimate")
    obs = out["source"] == "snpp"
    if not (out.loc[obs, "est"] == out.loc[obs, "snpp_count"]).all():
        raise SystemExit("observed S-NPP months must equal the observation")

    # region x month totals with intervals
    key = out.loc[model_rows, ["region", "month"]].reset_index(drop=True)
    rs_tot = pd.concat([key, pd.DataFrame(rs)], axis=1).groupby(["region", "month"]).sum()
    tot = out.groupby(["region", "month"], observed=True).agg(
        est=("est", "sum"), est_m0=("est_m0", lambda s: s.sum(min_count=1))
    )
    tot = tot.astype({"est": float, "est_m0": float})
    tot["lo_90"], tot["hi_90"] = tot["est"].copy(), tot["est"].copy()
    q = rs_tot.reindex(tot.index).dropna()
    tot.loc[q.index, "lo_90"] = np.percentile(q.to_numpy(float), 5, axis=1)
    tot.loc[q.index, "hi_90"] = np.percentile(q.to_numpy(float), 95, axis=1)
    calibrate, scale, cov = interval_rule()
    if calibrate:
        e = tot["est"].to_numpy(float)
        tot["lo_90"] = np.maximum(0.0, e - scale * (e - tot["lo_90"].to_numpy(float)))
        tot["hi_90"] = e + scale * (tot["hi_90"].to_numpy(float) - e)
    src = out.groupby(["region", "month"], observed=True)["source"].agg(
        lambda s: sorted(set(s.astype(str)))
    )
    if (src.map(len) > 1).any():
        raise SystemExit("more than one source in a region-month")
    tot["source"] = src.map(lambda s: s[0])
    tot["nrt"] = out.groupby(["region", "month"], observed=True)["nrt"].all()
    tot["input_complete"] = out.groupby(["region", "month"], observed=True)["input_complete"].all()

    front = out.loc[model_rows, prepare.KEY + ["month"]].reset_index(drop=True)
    keep = []
    for b in range(min(FRONTEND_RESAMPLES, resamples)):
        nz = rs[:, b] > 0
        keep.append(front[nz].assign(resample=np.int8(b), value=rs[nz, b]))
    frontend_rs = pd.concat(keep, ignore_index=True)

    meta = {
        "version": VERSION,
        "model": "LightGBM E028 (two-stage), frozen evaluation model",
        "freeze": "results/freeze.json",
        "freeze_commit": fz["code_commit"],
        "training": fz["training"],
        "inputs": fz["inputs"],
        "rounds": fz["rounds"],
        "resamples": resamples,
        "interval": {
            "calibrated": calibrate,
            "interval_scale": scale,
            "test_region_month_coverage_raw": cov,
        },
        "bridge_fit": BRIDGE_FIT,
        "bridge_regions": "all six regions, MODIS only (docs/decisions/0005 item 6 option B)",
        "continuation_fit": CONT_FIT,
        "lambda": LAM,
    }
    return out, {"meta": meta, "totals": tot.reset_index(), "frontend_rs": frontend_rs}


def recount(out: pd.DataFrame) -> dict:
    """Acceptance check (task card S12): the region x month totals of every observed S-NPP
    month, recounted straight from the cleaned S-NPP points (S04, same quality control), equal
    the dataset exactly."""
    import pyarrow.parquet as pq

    cells = grid.region_cells()
    cells = cells[cells["role"] == "train"]
    codes = cells["lat_idx"].to_numpy(np.int64) * grid.NLON + cells["lon_idx"].to_numpy()
    order = np.argsort(codes)
    codes, names = codes[order], cells["region"].to_numpy()[order]
    parts = []
    for f in sorted((data_dir() / "processed" / "clean" / "snpp").glob("*.parquet")):
        t = pq.read_table(f, columns=["latitude", "longitude", "acq_date"]).to_pandas()
        i, j = grid.cell_index(t["latitude"].to_numpy(), t["longitude"].to_numpy())
        c = i.astype(np.int64) * grid.NLON + j
        pos = np.clip(np.searchsorted(codes, c), 0, len(codes) - 1)
        hit = codes[pos] == c
        month = pd.to_datetime(t.loc[hit, "acq_date"]).dt.strftime("%Y-%m").to_numpy()
        parts.append(pd.DataFrame({"region": names[pos[hit]], "month": month}).value_counts())
    rec = pd.concat(parts).groupby(level=[0, 1]).sum()
    obs = out[out["source"] == "snpp"].groupby(["region", "month"], observed=True)["est"].sum()
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


def region_json(out: pd.DataFrame, tot: pd.DataFrame, region: dict, meta: dict) -> dict:
    d = out[out["region"] == region["name"]].sort_values(["lat_idx", "lon_idx", "month"])
    t = tot[tot["region"] == region["name"]].sort_values("month")
    months = t["month"].tolist()
    cells = d[["lat_idx", "lon_idx"]].drop_duplicates()
    est = d["est"].to_numpy().reshape(len(cells), len(months))
    sums = d.groupby("month")[["aqua_count", "terra_count", "snpp_count"]].sum(min_count=1)

    def r(a) -> list:
        return [None if np.isnan(v) else round(float(v), 2) for v in np.asarray(a, dtype=float)]

    return {
        "version": VERSION,
        "region": region["name"],
        "label": region["label"],
        "role": region["role"],
        "bbox": [region["west"], region["south"], region["east"], region["north"]],
        "cell_deg": settings()["grid"]["cell_deg"],
        "months": months,
        "month_source": t["source"].tolist(),
        "month_nrt": [bool(v) for v in t["nrt"]],
        "month_input_complete": [bool(v) for v in t["input_complete"]],
        "cells": {
            "lat_idx": cells["lat_idx"].astype(int).tolist(),
            "lon_idx": cells["lon_idx"].astype(int).tolist(),
        },
        "est": [r(row) for row in est],
        "totals": {
            "est": r(t["est"]),
            "lo_90": r(t["lo_90"]),
            "hi_90": r(t["hi_90"]),
            "est_m0": r(t["est_m0"]),
            **{k: r(sums[k].reindex(months)) for k in sums.columns},
        },
        "model": meta,
    }


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write(out: pd.DataFrame, extra: dict) -> list[str]:
    root = data_dir() / "processed" / VERSION
    (root / "frontend").mkdir(parents=True, exist_ok=True)
    meta, tot = extra["meta"], extra["totals"]
    out.to_parquet(root / f"dataset_{VERSION}.parquet", index=False, compression="zstd")
    extra["frontend_rs"].to_parquet(
        root / f"resamples{FRONTEND_RESAMPLES}_{VERSION}.parquet", index=False, compression="zstd"
    )
    tot.to_csv(root / f"region_totals_{VERSION}.csv", index=False, lineterminator="\n")
    for region in regions():
        data = json.dumps(region_json(out, tot, region, meta), separators=(",", ":"))
        with gzip.GzipFile(root / "frontend" / f"{region['name']}.json.gz", "wb", mtime=0) as f:
            f.write(data.encode("utf-8"))
    (root / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", "utf-8", newline="\n")
    return package(out, root)


DOCS = ("data-interface.md", "data-card.md", "anomaly-cases.json")  # shipped with the release


def package(out: pd.DataFrame, root=None) -> list[str]:
    """S14 delivery: the dataset as gzip CSV (fixed gzip timestamp, LF, empty field = no data,
    numbers to 6 significant digits), the documents of DOCS, then SHA256SUMS of every file.
    Same input -> same bytes on every machine."""
    root = root or data_dir() / "processed" / VERSION
    with (
        gzip.GzipFile(root / f"dataset_{VERSION}.csv.gz", "wb", mtime=0) as gz,
        io.TextIOWrapper(gz, encoding="utf-8", newline="\n") as f,
    ):
        out.to_csv(f, index=False, lineterminator="\n", float_format="%.6g")
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
    sub.add_parser("terra-check")
    sub.add_parser("package", help="S14 files from the existing dataset parquet")
    b = sub.add_parser("build")
    b.add_argument("-n", type=int, default=freeze.RESAMPLES)
    b.add_argument("--resamples-only", action="store_true", help="only fill the resample cache")
    args = p.parse_args()
    if args.cmd == "terra-check":
        res = terra_check()
        path = data_dir() / "s12" / "terra_check.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(res["combined_male"], indent=2))
        return 0
    if args.cmd == "package":
        root = data_dir() / "processed" / VERSION
        print("\n".join(package(pd.read_parquet(root / f"dataset_{VERSION}.parquet"), root)))
        return 0
    out, extra = build(prepare.load_grid(), args.n, args.resamples_only)
    if args.resamples_only:
        return 0
    if any((data_dir() / "processed" / "clean" / "snpp").glob("*.parquet")):
        rec = recount(out)
        print(f"acceptance recount: {rec}", flush=True)
        if rec["mismatches"]:
            raise SystemExit("observed S-NPP months differ from the cleaned observations")
    else:  # rebuilt from the data-v0 release, which has no cleaned VIIRS points (ADR 0003)
        rec = {"skipped": "no cleaned S-NPP points in this data folder (data-v0 release)"}
        print(f"acceptance recount skipped: {rec['skipped']}", flush=True)
    extra["meta"]["acceptance_recount"] = rec
    lines = write(out, extra)
    print(f"{len(out)} cell-months; sources: {out['source'].value_counts().to_dict()}")
    print("\n".join(lines))
    (data_dir() / "S12.done").write_text("ok\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
