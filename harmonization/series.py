"""S09 milestone A: dataset v0 (M1s, 2000-11..2026-10, with source flags) and front-end files.

uv run python -m harmonization.series

Source of every cell-month (docs/decisions/0005 item 5, docs/data-interface.md):
  snpp              training region, S-NPP complete month: the observed count
  noaa20_scaled     training region, S-NPP not complete but NOAA-20 complete: NOAA-20 x ratio
  m1s_aqua          otherwise, M1s estimate from Aqua
  m1s_terra_bridge  Aqua not complete but Terra complete: Terra -> Aqua bridge, then M1s
`input_complete` is false when the sensor a value comes from has missing days that month.
Holdout regions are M1s estimates for every month (their VIIRS is never on this machine).

Outputs in <data>/processed/v0/: dataset_v0.parquet, region_totals_v0.csv,
frontend/<region>.json.gz, a copy of docs/data-interface.md, SHA256SUMS.txt.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys

import numpy as np
import pandas as pd

from harmonization import harmonize, prepare
from harmonization.config import ROOT, data_dir, regions, settings

VERSION = "v0"
LAM = 20.0  # chosen on the validation windows in S08 (reports/scores-v1.md)
M1S_FIT = ("2014-01", "2021-06")  # splits.test_train: the refit range of the evaluation version
BRIDGE_FIT = ("2003-01", "2019-12")  # stable Terra/Aqua years (reports/findings.md item 7)
CONT_FIT = ("2018-04", "2026-10")  # full NOAA-20 / S-NPP overlap
SOURCES = ["snpp", "noaa20_scaled", "m1s_aqua", "m1s_terra_bridge"]


def ok(df: pd.DataFrame, sensor: str) -> np.ndarray:
    return (df[f"{sensor}_status"] == "complete").to_numpy()


def span(df: pd.DataFrame, s: tuple[str, str]) -> np.ndarray:
    return ((df["month"] >= s[0]) & (df["month"] <= s[1])).to_numpy()


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    train = (df["role"] == "train").to_numpy()
    fit_rows = df[train & span(df, M1S_FIT) & prepare.usable(df)]
    m1s = harmonize.fit_m1s(fit_rows, LAM)
    both_modis = df[train & span(df, BRIDGE_FIT) & ok(df, "terra") & ok(df, "aqua")]
    bridge = harmonize.m1s_ratios(both_modis, LAM, a_col="terra_count", v_col="aqua_count")
    both_viirs = df[train & span(df, CONT_FIT) & ok(df, "snpp") & ok(df, "noaa20")]
    cont = harmonize.m1s_ratios(both_viirs, LAM, a_col="noaa20_count", v_col="snpp_count")

    x = df.reset_index(drop=True)
    bridged = harmonize.apply_ratios(bridge, x, a_col="terra_count")
    aqua_ok, terra_ok = ok(x, "aqua"), ok(x, "terra")
    use_terra = (~aqua_ok & terra_ok) | x["aqua_count"].isna().to_numpy()
    modis_in = np.where(use_terra, bridged, x["aqua_count"].to_numpy(float))
    feats = prepare.feature_table(x).assign(aqua_count=modis_in)
    est_m1s = m1s(feats)

    snpp_ok = train & ok(x, "snpp")
    n20_ok = train & ~snpp_ok & ok(x, "noaa20")
    n20 = np.zeros(len(x))
    if n20_ok.any():
        n20[n20_ok] = harmonize.apply_ratios(cont, x[n20_ok].reset_index(drop=True), "noaa20_count")
    source = np.where(
        snpp_ok,
        "snpp",
        np.where(n20_ok, "noaa20_scaled", np.where(use_terra, "m1s_terra_bridge", "m1s_aqua")),
    )
    est = np.where(snpp_ok, x["snpp_count"].to_numpy(float), np.where(n20_ok, n20, est_m1s))
    input_complete = snpp_ok | n20_ok | np.where(use_terra, terra_ok, aqua_ok)
    # M0 direct splice for comparison charts: MODIS (Aqua, else Terra) before 2012-02, observed
    # S-NPP from 2012-02 where this machine has it.
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
            "source": pd.Categorical(source, categories=SOURCES),
            "input_complete": input_complete,
            "est_m0": m0.astype("float32"),
            "aqua_count": x["aqua_count"].astype("float32"),
            "terra_count": x["terra_count"].astype("float32"),
            "snpp_count": np.where(train, x["snpp_count"], np.nan).astype("float32"),
        }
    )
    if out["est"].isna().any():
        raise SystemExit(f"{int(out['est'].isna().sum())} cell-months without an estimate")
    if not (
        out.loc[out["source"] == "snpp", "est"] == out.loc[out["source"] == "snpp", "snpp_count"]
    ).all():
        raise SystemExit("observed S-NPP months must equal the observation")
    meta = {
        "lambda": LAM,
        "m1s_fit": M1S_FIT,
        "bridge_fit": BRIDGE_FIT,
        "continuation_fit": CONT_FIT,
        "m1s_fallbacks": m1s.ratios["fallbacks"],
    }
    return out, meta


def region_json(out: pd.DataFrame, region: dict, meta: dict) -> dict:
    d = out[out["region"] == region["name"]].sort_values(["lat_idx", "lon_idx", "month"])
    months = sorted(d["month"].unique())
    per_month = d.groupby("month", observed=True).agg(
        source=("source", lambda s: sorted(set(s.astype(str)))),
        input_complete=("input_complete", "all"),
    )
    if (per_month["source"].map(len) > 1).any():
        raise SystemExit(f"{region['name']}: more than one source in a month")
    cells = d[["lat_idx", "lon_idx"]].drop_duplicates()
    est = d["est"].to_numpy().reshape(len(cells), len(months))
    tot = d.groupby("month")[["est", "est_m0", "aqua_count", "terra_count", "snpp_count"]].sum(
        min_count=1
    )

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
        "month_source": [s[0] for s in per_month["source"]],
        "month_input_complete": [bool(v) for v in per_month["input_complete"]],
        "cells": {
            "lat_idx": cells["lat_idx"].astype(int).tolist(),
            "lon_idx": cells["lon_idx"].astype(int).tolist(),
        },
        "est": [r(row) for row in est],
        "totals": {k: r(tot[k]) for k in tot.columns},
        "model": meta,
    }


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    root = data_dir() / "processed" / VERSION
    (root / "frontend").mkdir(parents=True, exist_ok=True)
    out, meta = build(prepare.load_grid())
    out.to_parquet(root / f"dataset_{VERSION}.parquet", index=False, compression="zstd")
    totals = out.groupby(["region", "month", "source"], observed=True)[["est", "est_m0"]].sum(
        min_count=1
    )
    # LF line endings everywhere, so the files and hashes are the same on Windows and Linux
    totals.reset_index().to_csv(
        root / f"region_totals_{VERSION}.csv", index=False, lineterminator="\n"
    )
    for region in regions():
        data = json.dumps(region_json(out, region, meta), separators=(",", ":"))
        path = root / "frontend" / f"{region['name']}.json.gz"
        with gzip.GzipFile(path, "wb", mtime=0) as f:  # mtime 0: same bytes on every run
            f.write(data.encode("utf-8"))
    doc = (ROOT / "docs" / "data-interface.md").read_text(encoding="utf-8")
    (root / "data-interface.md").write_text(doc.replace("\r\n", "\n"), "utf-8", newline="\n")
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    lines = [f"{sha256(p)}  {p.name}" for p in files]  # flat names, as in the release
    (root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", "utf-8", newline="\n")
    print(f"{len(out)} cell-months; sources: {out['source'].value_counts().to_dict()}")
    print("\n".join(lines))
    (data_dir() / "S09.done").write_text("ok\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
