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
    ("male", "MALE（主）"),
    ("male_all", "MALE（全体）"),
    ("n_primary", "主样本数"),
    ("zero_ge1", "零火点 Ĥ≥1"),
    ("zero_ge5", "零火点 Ĥ≥5"),
    ("low_mae", "1–9 火点 MAE"),
    ("total_bias_mean_abs", "总量偏差（绝对值均值）"),
    ("season_corr_mean", "季节相关"),
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
    head = "| 方法 | 窗口 | " + " | ".join(label for _, label in SHOWN) + " |"
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
    runs["Terra→Aqua→M1s（链条检查）"] = evaluate.evaluate(chain_fit(df, lam), df)
    diffs = {
        f"{n} 对 {m1s_name}": evaluate.bootstrap_diff(runs[m1s_name], runs[n])
        for n in ("M0", "QM", "Terra→Aqua→M1s（链条检查）")
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
        for part, col in (("全部", "count"), ("白天", "count_day"), ("夜间", "count_night"))
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
        "# 分数表 v1（S08）",
        "",
        "由 `uv run python -m harmonization.baselines` 生成，"
        "打分用冻结的判卷代码 `harmonization/evaluate.py`。"
        "只用训练区（加州、科尔多瓦、非洲南部）的 600 个 demo 矩形；"
        "主验证窗口 main = 训练 2016-01–2021-06、评估 2014–2015；"
        "辅助倒推窗口 aux = 训练 2018-01–2021-06、评估 2016–2017。"
        "全部数字在 `reports/scores-v1.json`。",
        "",
        "## 1. 两个验证窗口上的全部指标",
        "",
        *table(rows),
        "",
        "## 2. 两窗口合并 MALE 与 M1s 的 λ 选择",
        "",
        "| 方法 | 两窗口合并 MALE |",
        "|---|---:|",
        *[f"| {n} | {fmt(r['combined_male'])} |" for n, r in runs.items()],
        "",
        "M1s 的 λ 按两窗口合并 MALE 从 {0, 5, 20, 50, 100} 里选（并列取小的），"
        f"**选定 λ = {lam:g}**。",
        "",
        "## 3. 与 M1s 的差（块状重采样）",
        "",
        "差 = 该方法 MALE − M1s MALE（正数表示比 M1s 差）；"
        "按“区域 × 年”单元有放回重抽 2000 次，两窗口等权；不报告 p 值。",
        "",
        "| 比较 | 差 | 标准误 | 95% 区间 |",
        "|---|---:|---:|---:|",
    ]
    for k, d in out["differences"].items():
        ci = d["ci95"]
        L.append(f"| {k} | {fmt(d['diff'])} | {fmt(d['se'])} | [{fmt(ci[0])}, {fmt(ci[1])}] |")
    b = out["bridge_terra_to_aqua"]
    L += [
        "",
        "## 4. Terra → Aqua 桥接",
        "",
        f"用 M1s 的比例形式（λ = {lam:g}），"
        f"在训练区 {BRIDGE_FIT[0]}–{BRIDGE_FIT[1]} 拟合 Terra→Aqua，"
        f"在 {BRIDGE_CHECK[0]}–{BRIDGE_CHECK[1]} 用真实 Aqua 检验"
        "（只用 Terra/Aqua 比例稳定的年份，见 `reports/findings.md` 第 7 条）。",
        "",
        "| 指标 | 值 |",
        "|---|---:|",
        *[f"| {label} | {fmt(b[k])} |" for k, label in SHOWN],
        "",
        "按区域的月总量偏差（桥接 Aqua ÷ 真实 Aqua − 1）：",
        "",
        "| 区域 | 中位数 | 10% | 90% | 月数 |",
        "|---|---:|---:|---:|---:|",
        *[
            f"| {r} | {fmt(v['median'])} | {fmt(v['p10'])} | {fmt(v['p90'])} | {v['n_months']} |"
            for r, v in b["monthly_total_bias"].items()
        ],
        "",
        "整条链条（Terra → 桥接 Aqua → M1s）在两个验证窗口上的分数"
        "见第 1、2 节“Terra→Aqua→M1s（链条检查）”行，"
        f"桥接比例只用 {BRIDGE_CHAIN_FIT[0]}–{BRIDGE_CHAIN_FIT[1]} 的 MODIS 拟合。"
        "它近似 2000-11 至 2002-06 只有 Terra 时的误差。",
        "",
        "## 5. NOAA-20 → S-NPP 接续检验",
        "",
        f"同样的比例形式，在训练区早段 {CONT_FIT[0]}–{CONT_FIT[1]} 拟合，"
        f"晚段 {CONT_CHECK[0]}–{CONT_CHECK[1]} 检验；"
        "两颗卫星都是完整月才用；白天、夜间分别拟合和检验。",
        "",
        "| 部分 | " + " | ".join(label for _, label in SHOWN) + " |",
        "|---|" + "---:|" * len(SHOWN),
        *[
            f"| {p} | " + " | ".join(fmt(v[k]) for k, _ in SHOWN) + " |"
            for p, v in out["continuation_noaa20_to_snpp"].items()
        ],
        "",
        "按区域的月总量偏差（换算后 NOAA-20 ÷ S-NPP − 1）：",
        "",
        "| 部分 | 区域 | 中位数 | 10% | 90% | 月数 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for p, v in out["continuation_noaa20_to_snpp"].items():
        for r, m in v["monthly_total_bias"].items():
            q = " | ".join(fmt(m[k]) for k in ("median", "p10", "p90", "n_months"))
            L.append(f"| {p} | {r} | {q} |")
    L += [
        "",
        "按区域 × 年的总量偏差（全部）：",
        "",
        "| 区域 | 年 | 偏差 |",
        "|---|---|---:|",
        *[
            f"| {u['region']} | {u['year']} | {fmt(u['bias'])} |"
            for u in out["continuation_noaa20_to_snpp"]["全部"]["total_bias"]
        ],
        "",
    ]
    (ROOT / "reports" / "scores-v1.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
