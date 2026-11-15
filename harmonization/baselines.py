"""S08 baselines and score table v1: M0, M1s (lambda chosen on validation), QM; Terra -> Aqua
bridge; NOAA-20 -> S-NPP continuation check.

uv run python -m harmonization.baselines      # writes reports/scores-v1.md and .json

Everything is scored with the frozen judge (harmonization.evaluate). The bridge and the
continuation use the M1s ratio form with the lambda chosen for M1s, training regions only:
  bridge        Terra -> Aqua, fitted 2003-01..2010-12, checked on 2011-01..2019-12 against real
                Aqua (only years with a stable Terra/Aqua ratio, reports/findings.md item 7);
                plus the full chain Terra -> Aqua -> VIIRS scored on both validation windows
  continuation  NOAA-20 -> S-NPP, fitted on the early overlap 2018-04..2021-12, checked on
                2022-01..2026-10, total and separately for day and night detections
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from harmonization import evaluate, harmonize, prepare
from harmonization.config import ROOT

BRIDGE_FIT = ("2003-01", "2010-12")
BRIDGE_CHECK = ("2011-01", "2019-12")
BRIDGE_CHAIN_FIT = ("2003-01", "2013-12")  # MODIS only, earlier than every validation window
CONT_FIT = ("2018-04", "2021-12")
CONT_CHECK = ("2022-01", "2026-10")
SHOWN = [
    ("male", "MALE (main)"),
    ("male_all", "MALE (all)"),
    ("n_primary", "Main samples"),
    ("zero_ge1", "Zero hotspots Ĥ≥1"),
    ("zero_ge5", "Zero hotspots Ĥ≥5"),
    ("low_mae", "1–9 hotspots MAE"),
    ("total_bias_mean_abs", "Total bias (mean abs.)"),
    ("season_corr_mean", "Seasonal corr."),
]


def between(df: pd.DataFrame, span: tuple[str, str]) -> pd.Series:
    return (df["month"] >= span[0]) & (df["month"] <= span[1])


def complete(df: pd.DataFrame, *sensors: str) -> np.ndarray:
    return np.logical_and.reduce([(df[f"{s}_status"] == "complete").to_numpy() for s in sensors])


def score_ratio(df, a_col, v_col, fit_span, check_span, lam, sensors, rect_cells) -> dict:
    """Fit an M1s ratio a_col -> v_col on fit_span, score it on check_span (training regions)."""
    t = df[(df["role"] == "train").to_numpy() & complete(df, *sensors)]
    fit = t[between(t, fit_span)]
    chk = t[between(t, check_span)].reset_index(drop=True).assign(usable=True)
    r = harmonize.m1s_ratios(fit, lam, a_col=a_col, v_col=v_col)
    est = harmonize.apply_ratios(r, chk, a_col=a_col)
    res = evaluate.score(chk, est, rect_cells, v_col)
    tot = chk.assign(H=est).groupby(["region", "month"])[["H", v_col]].sum()
    month_bias = (tot["H"] / tot[v_col].where(tot[v_col] > 0) - 1).dropna()
    res["monthly_total_bias"] = {
        region: {
            "median": float(g.median()),
            "p10": float(g.quantile(0.1)),
            "p90": float(g.quantile(0.9)),
            "n_months": int(len(g)),
        }
        for region, g in month_bias.groupby(level="region")
    }
    res["pooled_ratio_by_month"] = {int(k): float(v) for k, v in r["pooled"].items()}
    res["fallbacks"] = r["fallbacks"]
    return res


def chain_fit(df: pd.DataFrame, lam: float):
    """Terra -> Aqua -> VIIRS: bridge ratios fitted on MODIS 2003..2013, M1s on the window."""
    t = df[(df["role"] == "train").to_numpy() & complete(df, "terra", "aqua")]
    bridge = harmonize.m1s_ratios(t[between(t, BRIDGE_CHAIN_FIT)], lam, "terra_count", "aqua_count")

    def fit(train):
        m1s = harmonize.fit_m1s(train, lam)

        def predict(x):
            x = x.reset_index(drop=True)
            pseudo = harmonize.apply_ratios(bridge, x, a_col="terra_count")
            return m1s(x.assign(aqua_count=pseudo))

        return predict

    return fit


def strip(res: dict) -> dict:
    out = {k: v for k, v in res.items() if k not in ("units",)}
    return out


def fmt(x) -> str:
    if x is None:
        return "—"
    return f"{x:.4f}" if isinstance(x, float) else str(x)


def table(rows: list[tuple[str, str, dict]]) -> list[str]:
    head = "| Method | Window | " + " | ".join(label for _, label in SHOWN) + " |"
    lines = [head, "|---|---|" + "---:|" * len(SHOWN)]
    for name, window, res in rows:
        lines.append(f"| {name} | {window} | " + " | ".join(fmt(res[k]) for k, _ in SHOWN) + " |")
    return lines


def main() -> int:
    df = prepare.load_grid()
    rect_cells = prepare.rectangle_cells(
        df.loc[df["role"] == "train", prepare.KEY].drop_duplicates()
    )
    runs: dict[str, dict] = {}
    runs["M0"] = evaluate.evaluate(harmonize.fit_m0, df)
    for lam in harmonize.LAMBDAS:
        runs[f"M1s λ={lam:g}"] = evaluate.evaluate(lambda t, lam=lam: harmonize.fit_m1s(t, lam), df)
    m1s_runs = {lam: runs[f"M1s λ={lam:g}"]["combined_male"] for lam in harmonize.LAMBDAS}
    lam = min(m1s_runs, key=lambda k: (m1s_runs[k], k))  # ties -> smaller lambda
    m1s_name = f"M1s λ={lam:g}"
    runs["QM"] = evaluate.evaluate(harmonize.fit_qm, df)
    runs["Terra→Aqua→M1s (chain check)"] = evaluate.evaluate(chain_fit(df, lam), df)
    diffs = {
        f"{n} vs {m1s_name}": evaluate.bootstrap_diff(runs[m1s_name], runs[n])
        for n in ("M0", "QM", "Terra→Aqua→M1s (chain check)")
    }
    bridge = score_ratio(
        df,
        "terra_count",
        "aqua_count",
        BRIDGE_FIT,
        BRIDGE_CHECK,
        lam,
        ("terra", "aqua"),
        rect_cells,
    )
    cont = {
        part: score_ratio(
            df,
            f"noaa20_{col}",
            f"snpp_{col}",
            CONT_FIT,
            CONT_CHECK,
            lam,
            ("snpp", "noaa20"),
            rect_cells,
        )
        for part, col in (("all", "count"), ("day", "count_day"), ("night", "count_night"))
    }
    out = {
        "lambda_selected": lam,
        "m1s_combined_by_lambda": m1s_runs,
        "runs": {
            k: {w: strip(v[w]) for w in prepare.WINDOWS} | {"combined_male": v["combined_male"]}
            for k, v in runs.items()
        },
        "differences": diffs,
        "bridge_terra_to_aqua": strip(bridge),
        "continuation_noaa20_to_snpp": {k: strip(v) for k, v in cont.items()},
    }
    (ROOT / "reports" / "scores-v1.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_md(out, runs, lam)
    return 0


def write_md(out: dict, runs: dict, lam: float) -> None:
    rows = [(name, w, res[w]) for name, res in runs.items() for w in prepare.WINDOWS]
    L = [
        "# Score table v1 (S08)",
        "",
        "Generated by `uv run python -m harmonization.baselines`; "
        "scored with the frozen grader code `harmonization/evaluate.py`. "
        "Uses only the 600 demo rectangles in the training regions "
        "(California, Córdoba, southern Africa); "
        "main validation window main = train 2016-01–2021-06, evaluate 2014–2015; "
        "auxiliary backward window aux = train 2018-01–2021-06, evaluate 2016–2017. "
        "All numbers are in `reports/scores-v1.json`.",
        "",
        "## 1. All metrics on both validation windows",
        "",
        *table(rows),
        "",
        "## 2. Combined MALE over both windows and the choice of λ for M1s",
        "",
        "| Method | Combined MALE (both windows) |",
        "|---|---:|",
        *[f"| {n} | {fmt(r['combined_male'])} |" for n, r in runs.items()],
        "",
        "The λ for M1s is chosen from {0, 5, 20, 50, 100} by the combined MALE over both windows "
        f"(ties go to the smaller one): **selected λ = {lam:g}**.",
        "",
        "## 3. Differences from M1s (block resampling)",
        "",
        "Difference = the method's MALE − M1s MALE (positive means worse than M1s); "
        '"region × year" units resampled with replacement 2000 times, both windows weighted '
        "equally; no p-values are reported.",
        "",
        "| Comparison | Difference | Standard error | 95% interval |",
        "|---|---:|---:|---:|",
    ]
    for k, d in out["differences"].items():
        ci = d["ci95"]
        L.append(f"| {k} | {fmt(d['diff'])} | {fmt(d['se'])} | [{fmt(ci[0])}, {fmt(ci[1])}] |")
    b = out["bridge_terra_to_aqua"]
    L += [
        "",
        "## 4. Terra → Aqua bridge",
        "",
        f"Using the M1s ratio form (λ = {lam:g}), "
        f"Terra→Aqua is fitted on the training regions over {BRIDGE_FIT[0]}–{BRIDGE_FIT[1]} "
        f"and checked against real Aqua over {BRIDGE_CHECK[0]}–{BRIDGE_CHECK[1]} "
        "(only years with a stable Terra/Aqua ratio, see item 7 of `reports/findings.md`).",
        "",
        "| Metric | Value |",
        "|---|---:|",
        *[f"| {label} | {fmt(b[k])} |" for k, label in SHOWN],
        "",
        "Monthly total bias by region (bridged Aqua ÷ real Aqua − 1):",
        "",
        "| Region | Median | 10% | 90% | Months |",
        "|---|---:|---:|---:|---:|",
        *[
            f"| {r} | {fmt(v['median'])} | {fmt(v['p10'])} | {fmt(v['p90'])} | {v['n_months']} |"
            for r, v in b["monthly_total_bias"].items()
        ],
        "",
        "The scores of the whole chain (Terra → bridged Aqua → M1s) on both validation windows "
        'are in the "Terra→Aqua→M1s (chain check)" rows of sections 1 and 2; '
        f"for them the bridge ratio is fitted only on MODIS from "
        f"{BRIDGE_CHAIN_FIT[0]}–{BRIDGE_CHAIN_FIT[1]}. "
        "This approximates the error for 2000-11 to 2002-06, when only Terra exists.",
        "",
        "## 5. NOAA-20 → S-NPP continuation test",
        "",
        f"Same ratio form, fitted on the early part {CONT_FIT[0]}–{CONT_FIT[1]} "
        f"in the training regions and tested on the late part {CONT_CHECK[0]}–{CONT_CHECK[1]}; "
        "only months complete for both satellites are used; day and night are fitted and "
        "tested separately.",
        "",
        "| Part | " + " | ".join(label for _, label in SHOWN) + " |",
        "|---|" + "---:|" * len(SHOWN),
        *[
            f"| {p} | " + " | ".join(fmt(v[k]) for k, _ in SHOWN) + " |"
            for p, v in out["continuation_noaa20_to_snpp"].items()
        ],
        "",
        "Monthly total bias by region (converted NOAA-20 ÷ S-NPP − 1):",
        "",
        "| Part | Region | Median | 10% | 90% | Months |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for p, v in out["continuation_noaa20_to_snpp"].items():
        for r, m in v["monthly_total_bias"].items():
            q = " | ".join(fmt(m[k]) for k in ("median", "p10", "p90", "n_months"))
            L.append(f"| {p} | {r} | {q} |")
    L += [
        "",
        "Total bias by region × year (all):",
        "",
        "| Region | Year | Bias |",
        "|---|---|---:|",
        *[
            f"| {u['region']} | {u['year']} | {fmt(u['bias'])} |"
            for u in out["continuation_noaa20_to_snpp"]["all"]["total_bias"]
        ],
        "",
    ]
    (ROOT / "reports" / "scores-v1.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
