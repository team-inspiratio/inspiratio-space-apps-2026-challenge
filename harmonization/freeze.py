"""S11: freeze the selected model and seal the final-test submission (plan section 4.4).

The selected model (docs/decisions/0008) is LightGBM E028: harmonize.fit_lgb with the frozen
configuration harmonize.LGB. Three resampling jobs (any order, they can run in parallel), then
the seal:

  uv run python -X utf8 -m harmonization.freeze resample main   # validation window main
  uv run python -X utf8 -m harmonization.freeze resample aux    # validation window aux
  uv run python -X utf8 -m harmonization.freeze resample test   # refit on test_train, test rows
  uv run python -X utf8 -m harmonization.freeze seal            # results/submission.parquet

resample <window>: run the frozen procedure (fit_lgb: inner-split tuning and early stopping) on
the window's training table, training regions only; then, with those parameters and numbers of
rounds fixed, refit on 100 year-block resamples of the training years (whole calendar years
drawn with replacement, seeds.resampling) and predict the evaluation rows. The validation
windows keep region x month totals of their usable rows (label, estimate, resamples). `test`
keeps per-row estimates for the submission rows, which are built from MODIS inputs only:
training-region cells 2012-02..2013-12 (test 1) and holdout cells 2012-02..2021-06 (test 2).

seal: interval_scale = the smallest factor s for which the stretched region-month intervals
[e - s (e - q05), e + s (q95 - e)] hold 90 % of the observed totals of both validation windows
pooled (the formula of final_test.coverage). The submission adds M1s (lam 20), QM and M0 fitted
on the same training table, cell-level q05/q95 of the resamples (lo_90, hi_90) and the scale in
the Parquet metadata. Before writing, the frozen grader (final_test.grade) is run on a fake
answer key made from MODIS counts, to prove the file has every row and column it needs.
results/freeze.json records the frozen features, parameters, rounds, ranges and code hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from harmonization import evaluate, harmonize, prepare
from harmonization.config import ROOT, data_dir, settings

RESAMPLES = 100
NOMINAL = 0.90
TESTS = {"test1": "train", "test2": "holdout"}  # split -> role of its cells (preregistration)
VALIDATION = tuple(prepare.WINDOWS)  # main, aux
SUBMISSION = ROOT / "results" / "submission.parquet"
FREEZE = ROOT / "results" / "freeze.json"
SCALE_GRID = np.round(np.arange(0, 200001) * 0.01, 2)  # 0.00 .. 2000.00


def work_dir() -> Path:
    d = data_dir() / "s11"
    d.mkdir(parents=True, exist_ok=True)
    return d


def manifest_sha256(path: Path) -> str:
    """The hash config/frozen-manifest.json stores (tools/guardrails.file_sha256: CRLF -> LF)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def training_table(df: pd.DataFrame, window: str) -> pd.DataFrame:
    """Usable training-region rows of a validation window, or of test_train for `test`."""
    if window == "test":
        keep = (df["role"] == "train").to_numpy() & prepare.in_months(df, "test_train")
        return df[keep & prepare.usable(df)].reset_index(drop=True)
    return prepare.window(df, window)[0]


def eval_rows(df: pd.DataFrame, window: str) -> pd.DataFrame:
    """Usable evaluation rows of a validation window; every submission row for `test`."""
    if window == "test":
        parts = [
            df[(df["role"] == role).to_numpy() & prepare.in_months(df, split)]
            for split, role in TESTS.items()
        ]
        return pd.concat(parts, ignore_index=True)
    ev = prepare.window(df, window)[1]
    return ev[ev["usable"].to_numpy()].reset_index(drop=True)


def year_blocks(months: pd.Series, n: int, seed: int) -> list[tuple[list[str], np.ndarray]]:
    """n resamples of whole calendar years with replacement: (years drawn, row indices)."""
    years = months.str[:4].to_numpy()
    uniq = np.unique(years)
    rows = {y: np.flatnonzero(years == y) for y in uniq}
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        out.append(([str(y) for y in pick], np.concatenate([rows[y] for y in pick])))
    return out


def fixed_fit(cfg: dict, train: pd.DataFrame) -> dict:
    """Refit with the frozen parameters and numbers of rounds (no tuning, no early stopping)."""
    x = harmonize.lgb_inputs(train, cfg)
    return harmonize.refit_models(cfg, x, train[harmonize.V].to_numpy(float), cfg["rounds"])


def plain(cfg: dict) -> dict:
    return json.loads(json.dumps(cfg, default=list))


def resample(window: str, n: int = RESAMPLES) -> dict:
    t0 = time.time()
    df = prepare.load_grid()
    train = training_table(df, window)
    rows = eval_rows(df, window)
    feats = prepare.feature_table(rows)
    pred = harmonize.fit_lgb(train.copy())
    cfg = pred.config
    est = np.asarray(pred(feats), dtype=float)
    refit = harmonize.models_predict(fixed_fit(cfg, train), feats, cfg)
    if not np.array_equal(refit, est):
        raise SystemExit("refit with the frozen rounds does not reproduce fit_lgb")
    draws = year_blocks(train["month"], n, settings()["seeds"]["resampling"])
    rs = np.empty((len(rows), n), dtype=np.float32)
    for b, (_, idx) in enumerate(draws):
        models = fixed_fit(cfg, train.iloc[idx].reset_index(drop=True))
        rs[:, b] = harmonize.models_predict(models, feats, cfg)
        print(f"{window}: resample {b + 1}/{n} ({time.time() - t0:.0f} s)", flush=True)
    rs_cols = [f"rs_{b:03d}" for b in range(n)]
    out = pd.concat(
        [
            rows[prepare.KEY + ["region", "month"]].reset_index(drop=True),
            pd.DataFrame({"est_final": est}),
            pd.DataFrame(rs, columns=rs_cols),
        ],
        axis=1,
    )
    meta = {
        "window": window,
        "train_months": [str(train["month"].min()), str(train["month"].max())],
        "train_rows": int(len(train)),
        "eval_rows": int(len(rows)),
        "inputs": list(harmonize.lgb_inputs(train.head(1), cfg).columns),
        "config": plain(cfg),
        "draws": [d[0] for d in draws],
        "runtime_s": round(time.time() - t0),
        "lightgbm": lgb.__version__,
        "threads": harmonize.THREADS,
        "harmonize_sha256": sha256(ROOT / "harmonization" / "harmonize.py"),
    }
    wd = work_dir()
    if window == "test":
        out.to_parquet(wd / "test_rows.parquet", index=False)
    else:
        rc = prepare.rectangle_cells(df.loc[df["role"] == "train", prepare.KEY].drop_duplicates())
        s = evaluate.score(rows, est, rc, prepare.LABEL)
        meta["score"] = {k: s[k] for k in ("male", "zero_ge1", "zero_ge5", "low_mae")}
        meta["male_by_region"] = s["male_by_region"]
        tot = out.assign(V=rows[prepare.LABEL].to_numpy(float))
        tot = tot.groupby(["region", "month"], sort=True)[["V", "est_final"] + rs_cols].sum()
        tot.reset_index().to_parquet(wd / f"val_{window}.parquet", index=False)
    (wd / f"{window}.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"{window}: done in {meta['runtime_s']} s, config {meta['config']}", flush=True)
    return meta


def quantiles(tot: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    rs = tot[[c for c in tot.columns if c.startswith("rs_")]].to_numpy(float)
    return np.percentile(rs, 5, axis=1), np.percentile(rs, 95, axis=1)


def covered(v, e, lo, hi, s) -> np.ndarray:
    """final_test.coverage: v inside [e - s (e - lo), e + s (hi - e)]; s may be an array."""
    s = np.asarray(s, dtype=float)[..., None]
    return (v >= e - s * (e - lo)) & (v <= e + s * (hi - e))


def interval_scale(v, e, lo, hi, target: float = NOMINAL) -> tuple[float, float]:
    """Smallest s on SCALE_GRID with coverage >= target, and the coverage it reaches."""
    cov = covered(v, e, lo, hi, SCALE_GRID).mean(axis=1)
    ok = np.flatnonzero(cov >= target)
    i = int(ok[0]) if len(ok) else int(np.argmax(cov))
    return float(SCALE_GRID[i]), float(cov[i])


def calibration() -> dict:
    """Raw coverage of each validation window and the pooled scale (preregistration 7)."""
    parts, out = [], {}
    for w in VALIDATION:
        tot = pd.read_parquet(work_dir() / f"val_{w}.parquet")
        lo, hi = quantiles(tot)
        v, e = tot["V"].to_numpy(float), tot["est_final"].to_numpy(float)
        out[w] = {
            "region_months": int(len(tot)),
            "coverage_raw": float(covered(v, e, lo, hi, 1.0).mean()),
        }
        parts.append((v, e, lo, hi))
    v, e, lo, hi = (np.concatenate(x) for x in zip(*parts, strict=True))
    scale, cov = interval_scale(v, e, lo, hi)
    out["pooled"] = {
        "region_months": int(len(v)),
        "coverage_raw": float(covered(v, e, lo, hi, 1.0).mean()),
        "interval_scale": scale,
        "coverage_calibrated": cov,
    }
    for w, x in zip(VALIDATION, parts, strict=True):
        out[w]["coverage_calibrated"] = float(covered(*x, scale).mean())
    return out


def fake_key(df: pd.DataFrame) -> pd.DataFrame:
    """An answer key shaped like final_test.answer_key but with a made-up label from MODIS
    (4 x Aqua count): it only checks that the frozen grader can read the submission."""
    key = df[prepare.in_months(df, "test2")].copy()  # 2012-02..2021-06, every region cell
    key["snpp_status"] = "complete"
    key[prepare.LABEL] = np.round(4 * key["aqua_count"].to_numpy(float))
    return key[
        prepare.KEY
        + ["region", "role", "month", "aqua_status", "terra_status", "snpp_status", prepare.LABEL]
    ].reset_index(drop=True)


def seal() -> dict:
    from harmonization import final_test

    wd = work_dir()
    cal = calibration()
    scale = cal["pooled"]["interval_scale"]
    df = prepare.load_grid()
    train = training_table(df, "test")
    rows = eval_rows(df, "test")
    test = pd.read_parquet(wd / "test_rows.parquet")
    if not test[prepare.KEY + ["month"]].equals(
        rows[prepare.KEY + ["month"]].reset_index(drop=True)
    ):
        raise SystemExit("test_rows.parquet does not match the submission rows")
    meta_test = json.loads((wd / "test.json").read_text(encoding="utf-8"))
    feats = prepare.feature_table(rows)
    rs_cols = [c for c in test.columns if c.startswith("rs_")]
    rs = test[rs_cols].to_numpy(np.float32)
    sub = pd.DataFrame(
        {
            "lat_idx": rows["lat_idx"].to_numpy(np.int32),
            "lon_idx": rows["lon_idx"].to_numpy(np.int32),
            "month": rows["month"].astype(str).to_numpy(),
            "est_final": test["est_final"].to_numpy(float),
            "est_m1s": harmonize.fit_m1s(train, 20.0)(feats),
            "est_qm": harmonize.fit_qm(train)(feats),
            "est_m0": harmonize.fit_m0(train)(feats),
            "lo_90": np.percentile(rs, 5, axis=1).astype(np.float32),
            "hi_90": np.percentile(rs, 95, axis=1).astype(np.float32),
        }
    )
    sub = pd.concat([sub, pd.DataFrame(rs, columns=rs_cols)], axis=1)
    est_cols = [c for c in sub.columns if c.startswith("est_")]
    vals = sub[est_cols + ["lo_90", "hi_90"] + rs_cols].to_numpy(float)
    if not np.isfinite(vals).all() or (vals < 0).any():
        raise SystemExit("submission has non-finite or negative estimates")
    if sub.duplicated(prepare.KEY + ["month"]).any():
        raise SystemExit("submission has duplicate cell-months")

    dry = final_test.grade(sub.copy(), fake_key(df), scale)  # raises if anything is missing
    for split in TESTS:
        print(
            f"dry run {split}: est_final MALE on the fake key "
            f"{dry[split]['scores']['est_final']['male']:.4f}, coverage keys "
            f"{sorted(dry[split]['coverage'])}",
            flush=True,
        )

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    table = pa.Table.from_pandas(sub, preserve_index=False)
    info = {"model": "E028", "freeze": "results/freeze.json", "code_commit": commit}
    table = table.replace_schema_metadata(
        {
            **(table.schema.metadata or {}),
            b"interval_scale": repr(scale).encode(),
            b"inspiratio": json.dumps(info).encode(),
        }
    )
    SUBMISSION.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, SUBMISSION, compression="zstd", compression_level=19)
    check = pq.read_schema(SUBMISSION).metadata
    assert float(check[b"interval_scale"]) == scale

    freeze = {
        "stage": "S11",
        "decision": "docs/decisions/0008",
        "selected_model": "LightGBM E028 (two-stage), harmonize.fit_lgb with harmonize.LGB",
        "code_commit": commit,
        "code_sha256_manifest_style": {
            p: manifest_sha256(ROOT / p)
            for p in (
                "harmonization/harmonize.py",
                "harmonization/freeze.py",
                "config/features.json",
                "uv.lock",
            )
        },
        "training": {
            "regions": sorted(train["region"].unique().tolist()),
            "months": meta_test["train_months"],
            "rows": meta_test["train_rows"],
        },
        "inputs": meta_test["inputs"],
        "config": meta_test["config"],
        "rounds": meta_test["config"]["rounds"],
        "lightgbm": meta_test["lightgbm"],
        "threads": meta_test["threads"],
        "seeds": {k: settings()["seeds"][k] for k in ("lightgbm", "resampling")},
        "resamples": {"n": len(rs_cols), "years_drawn": meta_test["draws"]},
        "validation_windows": {
            w: {
                k: v
                for k, v in json.loads((wd / f"{w}.json").read_text(encoding="utf-8")).items()
                if k in ("train_months", "train_rows", "config", "score", "male_by_region")
            }
            for w in VALIDATION
        },
        "calibration": cal,
        "submission": {
            "path": "results/submission.parquet",
            "rows": int(len(sub)),
            "rows_by_split": {
                s: int((prepare.in_months(rows, s) & (rows["role"] == r).to_numpy()).sum())
                for s, r in TESTS.items()
            },
            "columns": list(sub.columns[:9]) + [f"rs_000..rs_{len(rs_cols) - 1:03d}"],
            "interval_scale": scale,
            "sha256": sha256(SUBMISSION),
            "sha256_manifest_style": manifest_sha256(SUBMISSION),
            "bytes": SUBMISSION.stat().st_size,
        },
    }
    FREEZE.write_text(json.dumps(freeze, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(freeze["calibration"], indent=2))
    print(
        f"sealed {SUBMISSION} ({freeze['submission']['bytes'] / 1e6:.1f} MB), "
        f"sha256 {freeze['submission']['sha256']}"
    )
    return freeze


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resample")
    r.add_argument("window", choices=[*VALIDATION, "test"])
    r.add_argument("-n", type=int, default=RESAMPLES)
    sub.add_parser("seal")
    args = p.parse_args()
    if args.cmd == "resample":
        resample(args.window, args.n)
    else:
        seal()
    return 0


if __name__ == "__main__":
    sys.exit(main())
