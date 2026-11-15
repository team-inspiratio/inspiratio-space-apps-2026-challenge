"""S07 judge, part 3: the one-time final test, run only by .github/workflows/grader.yml.

python -m harmonization.final_test --submission results/submission.parquet \
    --locked-dir <dir with the yearly S-NPP zips> --out results/final-test

Never run on the development machine: the locked S-NPP years exist only on GitHub's runner.
The answer key is built with the frozen import, cleaning and gridding code (ingest.normalise,
clean.clean, grid.aggregate), so it is made exactly like the training labels, for the cells of
config/regions.json only (training and holdout regions), 2012-02..2021-06.

Scores (docs/preregistration.md sections 2, 3, 5, 7), for every est_* column of the submission:
  test1  training regions, 2012-02..2013-12, demo rectangles of the training regions
  test2  holdout regions, 2012-02..2021-06, demo rectangles of the holdout regions
with the same metrics as harmonization.evaluate, block-bootstrap differences of est_final against
est_m1s and est_qm, anomaly-class agreement (Cohen's kappa) and interval coverage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from harmonization import clean, evaluate, grid, ingest, prepare
from harmonization.config import settings

TESTS = {"test1": "train", "test2": "holdout"}  # split -> role of the scored cells
KEY_RANGE = ("2012-02", "2021-06")  # every month the answer key covers


def label_status() -> pd.DataFrame:
    """Real status of every label month: the dev-side `locked` flag is replaced by what the
    FIRMS missing-data list says (days_missing also counts days the satellite did not fly)."""
    st = grid.month_status()
    days = pd.PeriodIndex(st["month"], freq="M").days_in_month
    locked = (st["status"] == "locked").to_numpy()
    real = np.where(
        st["days_missing"] == 0,
        "complete",
        np.where(st["days_missing"] >= days, "missing", "partial"),
    )
    st.loc[locked, "status"] = real[locked]
    return st.pivot(index="month", columns="sensor", values="status")


def answer_counts(locked_dir: Path, cells: pd.DataFrame) -> pd.DataFrame:
    """S-NPP counts per (cell, month) for `cells`, from the yearly zips in `locked_dir`."""
    want = np.unique(cells["lat_idx"].to_numpy() * grid.NLON + cells["lon_idx"].to_numpy())
    kept: list[pd.DataFrame] = []
    for path in sorted(locked_dir.glob("*.zip")):
        rows = 0
        for chunk, country in ingest.zip_chunks(path):
            df = ingest.normalise(chunk, "SP", country)
            df = df[df["sensor"] == "snpp"]
            i, j = grid.cell_index(df["latitude"].to_numpy(), df["longitude"].to_numpy())
            df = df[np.isin(i.astype(np.int64) * grid.NLON + j, want)]
            rows += len(df)
            if len(df):
                kept.append(df)
        print(f"{path.name}: {rows} rows in the scored cells", flush=True)
    if not kept:
        raise SystemExit(f"no S-NPP rows for the scored cells in {locked_dir}")
    pts = pd.concat(kept, ignore_index=True)
    years = pd.to_datetime(pts["acq_date"]).dt.year
    parts = []
    for _, g in pts.groupby(years, sort=True):  # cleaned per year, as in S04
        cleaned, counts, _ = clean.clean(g.reset_index(drop=True), set())
        print(f"cleaned: {counts}", flush=True)
        if len(cleaned):
            parts.append(grid.aggregate(cleaned, modis=False))
    return pd.concat(parts, ignore_index=True)[["lat_idx", "lon_idx", "month", "count"]]


def answer_key(locked_dir: Path) -> pd.DataFrame:
    """Dense cell x month table of every region cell, 2012-02..2021-06, with the S-NPP label
    (0 = no detection; NaN where the month is not complete or partial) and sensor status."""
    cells = grid.region_cells()
    months = [m for m in grid.month_range() if KEY_RANGE[0] <= m <= KEY_RANGE[1]]
    base = cells.merge(pd.DataFrame({"month": months}), how="cross")
    counts = answer_counts(locked_dir, cells)
    base = base.merge(counts, on=prepare.KEY + ["month"], how="left")
    st = label_status()
    for sensor in ("snpp", "aqua", "terra"):
        base[f"{sensor}_status"] = base["month"].map(st[sensor])
    has = base["snpp_status"].isin(["complete", "partial"])
    base[prepare.LABEL] = np.where(has, base["count"].fillna(0), np.nan)
    return base.drop(columns="count")


def anomaly_class(target: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """0 low, 1 normal, 2 high from the mid-rank percentile (proposal "anomaly indicator"); `ref` has one
    row of reference values per target, NaN where a year is not in the reference set."""
    n = np.isfinite(ref).sum(axis=1)
    h = target[:, None]
    pct = 100 * ((ref < h).sum(axis=1) + 0.5 * (ref == h).sum(axis=1)) / np.maximum(n, 1)
    return np.where(pct >= 90, 2, np.where(pct <= 10, 0, 1))


def kappa(a: np.ndarray, b: np.ndarray) -> tuple[float | None, list[list[int]]]:
    cm = np.zeros((3, 3), dtype=int)
    np.add.at(cm, (a, b), 1)
    n = cm.sum()
    if n == 0:
        return None, cm.tolist()
    po = np.trace(cm) / n
    pe = (cm.sum(0) * cm.sum(1)).sum() / n**2
    return (float((po - pe) / (1 - pe)) if pe < 1 else None), cm.tolist()


def anomaly_agreement(
    key: pd.DataFrame, table: pd.DataFrame, est: dict[str, np.ndarray], rc: pd.DataFrame
) -> dict:
    """Preregistration section 5: classes from observed V vs from each estimate, per rectangle-
    month of the test; reference = same rectangle and calendar month, other usable years of
    2012-02..2021-06, observed V; needs >= 8 reference years and a reference median >= 10."""
    obs_all = key[prepare.LABEL].fillna(0).to_numpy()
    ref_rm = evaluate.rect_month_sums(key, obs_all, prepare.LABEL, rc)
    ref = ref_rm.assign(cal=ref_rm["month"].str[5:7], year=ref_rm["month"].str[:4]).pivot(
        index=["rect_id", "cal"], columns="year", values="V"
    )
    years = ref.columns.to_numpy()
    out = {}
    for name, h in est.items():
        rm = evaluate.rect_month_sums(table, h, prepare.LABEL, rc)
        idx = pd.MultiIndex.from_arrays([rm["rect_id"], rm["month"].str[5:7]])
        x = ref.reindex(idx).to_numpy(float, copy=True)
        x[years[None, :] == rm["month"].str[:4].to_numpy()[:, None]] = np.nan  # not its own year
        n = np.isfinite(x).sum(axis=1)
        med = np.full(len(x), np.nan)
        enough = n >= 8
        med[enough] = np.nanmedian(x[enough], axis=1)
        keep = enough & (med >= 10)
        obs_cls = anomaly_class(rm["V"].to_numpy()[keep], x[keep])
        est_cls = anomaly_class(rm["H"].to_numpy()[keep], x[keep])
        k, cm = kappa(obs_cls, est_cls)
        out[name] = {"kappa": k, "confusion_obs_rows_est_cols": cm, "n": int(keep.sum())}
    return out


def coverage(table: pd.DataFrame, sub: pd.DataFrame, scale: float | None) -> dict:
    """Section 7: share of region-month observed totals inside the 5-95 % stability interval of
    the resampled estimates (columns rs_*), nominal 90 %; optionally with the calibration factor
    fixed on the validation windows (stored as `interval_scale` in the submission metadata)."""
    rs = [c for c in sub.columns if c.startswith("rs_")]
    t = table[table["usable"].to_numpy()]
    out: dict = {"resamples": len(rs)}
    if rs:
        tot = t.groupby(["region", "month"])[[prepare.LABEL, "est_final"] + rs].sum()
        lo = np.percentile(tot[rs].to_numpy(), 5, axis=1)
        hi = np.percentile(tot[rs].to_numpy(), 95, axis=1)
        v, e = tot[prepare.LABEL].to_numpy(), tot["est_final"].to_numpy()
        out["region_month_coverage"] = float(((v >= lo) & (v <= hi)).mean())
        out["n_region_months"] = int(len(tot))
        if scale is not None:
            lo_c, hi_c = e - scale * (e - lo), e + scale * (hi - e)
            out["interval_scale"] = scale
            out["region_month_coverage_calibrated"] = float(((v >= lo_c) & (v <= hi_c)).mean())
    if {"lo_90", "hi_90"} <= set(sub.columns):
        v = t[prepare.LABEL].to_numpy()
        out["cell_month_coverage"] = float(
            ((v >= t["lo_90"].to_numpy()) & (v <= t["hi_90"].to_numpy())).mean()
        )
    return out


def grade(sub: pd.DataFrame, key: pd.DataFrame, scale: float | None = None) -> dict:
    est_cols = sorted(c for c in sub.columns if c.startswith("est_"))
    if "est_final" not in est_cols:
        raise SystemExit("submission has no est_final column")
    extra = [c for c in ("lo_90", "hi_90") if c in sub] + [c for c in sub if c.startswith("rs_")]
    results: dict = {"estimates": est_cols}
    for split, role in TESTS.items():
        start, end = prepare.months(split)
        part = key[(key["role"] == role) & (key["month"] >= start) & (key["month"] <= end)]
        part = part.assign(usable=prepare.usable(part))
        cols = prepare.KEY + ["month"] + est_cols + extra
        table = part.merge(sub[cols], on=prepare.KEY + ["month"], how="left")
        lacking = table["usable"] & table["est_final"].isna()
        if lacking.any():
            raise SystemExit(f"{split}: submission lacks {int(lacking.sum())} usable cell-months")
        cells = part[prepare.KEY].drop_duplicates()
        rc = prepare.rectangle_cells(cells, role=role)
        est = {c: table[c].fillna(0).to_numpy(float) for c in est_cols}
        res = {c: evaluate.score(table, est[c], rc, prepare.LABEL) for c in est_cols}
        cmp = {}
        for other in ("est_m1s", "est_qm"):
            if other in res:
                cmp[f"est_final_vs_{other}"] = evaluate.bootstrap_diff(
                    {split: res["est_final"]}, {split: res[other]}, windows=(split,)
                )
        key_rc = key[key["role"] == role].assign(usable=prepare.usable(key[key["role"] == role]))
        results[split] = {
            "scores": res,
            "differences": cmp,
            "anomaly_agreement": anomaly_agreement(
                key_rc, table, {c: est[c] for c in ("est_final", "est_m1s") if c in est}, rc
            ),
            "coverage": coverage(table, sub, scale),
        }
    return results


def fmt(x: float | None) -> str:
    return "" if x is None else f"{x:.4f}"


def summary_md(results: dict) -> str:
    lines = ["# Final test results", "", "Computed by grader.yml on GitHub's runner.", ""]
    for split in TESTS:
        lines += [f"## {split}", "", "| estimate | MALE | MALE (all) | n | zero >= 1 | low MAE |"]
        lines.append("|---|---:|---:|---:|---:|---:|")
        for c, s in results[split]["scores"].items():
            lines.append(
                f"| {c} | {fmt(s['male'])} | {fmt(s['male_all'])} | {s['n_primary']} | "
                f"{fmt(s['zero_ge1'])} | {fmt(s['low_mae'])} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--submission", type=Path, required=True)
    p.add_argument("--locked-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    meta = pq.read_schema(args.submission).metadata or {}
    scale = float(meta[b"interval_scale"]) if b"interval_scale" in meta else None
    sub = pd.read_parquet(args.submission)
    sub[prepare.KEY] = sub[prepare.KEY].astype("int32")
    key = answer_key(args.locked_dir)
    results = grade(sub, key, scale)
    results["settings_seed_bootstrap"] = settings()["seeds"]["bootstrap"]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "scores.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (args.out / "summary.md").write_text(summary_md(results), encoding="utf-8")
    print(summary_md(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
