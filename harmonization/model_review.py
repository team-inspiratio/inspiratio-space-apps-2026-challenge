"""S10 independent model review of the top 3 LightGBM experiments (preregistration section 4
item 5): leakage checks, feature-group ablation, prediction relationship plots, window stability.

  uv run python -X utf8 -m harmonization.model_review
      writes reports/model-review.json and reports/figures/s10-*.png

Only the two validation windows (prepare.window, training regions only) are used; no test data.
Every refit takes the tuned parameters of the window from experiments/E###.json with Optuna off,
so the number of rounds is again chosen by early stopping on the training table's earliest months.
"""

from __future__ import annotations

import csv
import difflib
import json
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from harmonization import autoexp, evaluate, prepare  # noqa: E402
from harmonization.config import ROOT, regions  # noqa: E402
from harmonization.s10_scores import BRANCH, load_variant  # noqa: E402

TOP3 = ("E028", "E018", "E032")
FIRST = "E028"
OUT_JSON = ROOT / "reports" / "model-review.json"
FIG = ROOT / "reports" / "figures"
WINDOWS = tuple(prepare.WINDOWS)
METRICS = ("male", "zero_ge1", "zero_ge5", "low_mae")
FLAGS = ["terra_no_detection", "aqua_no_detection"]
FORBIDDEN = {"lat_idx", "lon_idx", "month", "year", "region", "role"}
COLORS = {"california": "#2a78d6", "cordoba": "#eb6834", "southern_africa": "#1baf7a"}
MODEL_C, OBS_C, HOLD_C = "#2a78d6", "#eb6834", "#8a8a85"
SEED = 7
A = "aqua_count"


def both(k: str) -> list[str]:
    return [f"aqua_{k}", f"terra_{k}"]


GROUPS = {  # feature groups removed in turn from the #1 candidate
    "aqua_count": ["aqua_count"],
    "terra_all": [f for f in prepare.features() if f.startswith("terra_")],
    "frp": both("frp_median") + both("frp_p75") + both("low_frp_share"),
    "pixel_area": both("pixel_area_mean"),
    "night_share": both("night_share"),
    "fire_days": both("fire_days"),
    "nbr_count": both("nbr_count"),
    "no_detection_add_back": FLAGS,  # E028 already drops them: this row adds them back
    "lat": ["lat"],
    "cal_month": ["cal_month"],
}


def window_of(train: pd.DataFrame) -> str:
    return "main" if train["month"].min() < prepare.months("aux_train")[0] else "aux"


def tuned(exp_id: str) -> tuple[dict, dict]:
    """({window: tuned config without rounds}, {window: rounds}) from experiments/E###.json."""
    cfgs = json.loads((autoexp.exp_dir() / f"{exp_id}.json").read_text(encoding="utf-8"))
    cfgs = cfgs["configs"]
    out, rounds = {}, {}
    for w, c in zip(WINDOWS, cfgs, strict=True):
        c = dict(c)
        rounds[w] = c.pop("rounds")
        out[w] = c
    return out, rounds


def run(mod, cfgs: dict, df: pd.DataFrame, **extra) -> tuple[dict, dict]:
    """Frozen-judge evaluation with Optuna off; returns (results, {window: fit details})."""
    fitted: dict = {}

    def fit(train: pd.DataFrame):
        w = window_of(train)
        cfg = {**cfgs[w], **extra, "optuna_trials": 0}
        t = train.reset_index(drop=True)
        _, held = mod.inner_split(t, int(cfg["inner_months"]))
        p = mod.fit_lgb(train, **cfg)
        fitted[w] = {
            "predict": p,
            "train_months": [t["month"].min(), t["month"].max()],
            "inner_held_months": [t.loc[held, "month"].min(), t.loc[held, "month"].max()],
        }
        return p

    return autoexp.strip(evaluate.evaluate(fit, df)), fitted


def summary(res: dict, m1s: dict) -> dict:
    s = {"combined": res["combined_male"]}
    for w in WINDOWS:
        for k in METRICS:
            s[f"{k}_{w}"] = res[w][k]
        s[f"male_by_region_{w}"] = res[w]["male_by_region"]
    s["guardrail_failures"] = autoexp.guardrails(res, m1s)
    return s


def csv_rows() -> dict:
    with autoexp.CSV.open(encoding="utf-8", newline="") as f:
        return {r["exp_id"]: r for r in csv.DictReader(f)}


def source(exp_id: str) -> list[str]:
    src = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{BRANCH}:harmonization/variants/{exp_id}.py"],
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    return src.splitlines()


def leakage(exp_id: str, mod, fitted: dict, rounds: dict, rows: dict) -> dict:
    allowed = set(prepare.features()) | set(mod.DERIVED)
    out: dict = {"windows": {}}
    rng = np.random.default_rng(SEED)
    for w, f in fitted.items():
        p = f["predict"]
        names = {k: m.feature_name() for k, m in p.models.items()}
        used = set().union(*names.values())
        ft = prepare.feature_table(rows[w])
        scrambled = ft.copy()
        for c in prepare.KEY:
            scrambled[c] = rng.permutation(scrambled[c].to_numpy())
        out["windows"][w] = {
            "feature_names": names,
            "not_allowed": sorted(used - allowed),
            "forbidden": sorted(
                c for c in used if c in FORBIDDEN or c.startswith(("snpp", "noaa20"))
            ),
            "rounds_refit": p.config["rounds"],
            "rounds_json": rounds[w],
            "train_months": f["train_months"],
            "inner_held_months": f["inner_held_months"],
            "key_scramble_max_abs_diff": float(np.abs(p(ft) - p(scrambled)).max()),
        }
    diff = difflib.unified_diff(source(FIRST), source(exp_id), lineterm="", n=0)
    out["source_diff_vs_E028"] = [
        d for d in diff if d[:1] in "+-" and not d.startswith(("+++", "---"))
    ]
    return out


def lat_tests(fitted: dict, rows: dict, rect_cells: pd.DataFrame) -> dict:
    """MALE when lat is replaced by each region's median lat (keeps only the region identity)
    and when the regions' median lats are swapped cyclically (wrong region identity)."""
    names = sorted(COLORS)
    out: dict = {}
    for label in ("unchanged", "region_median", "region_swapped"):
        per_w = {}
        for w, f in fitted.items():
            r = rows[w]
            ft = prepare.feature_table(r)
            med = r.groupby("region")["lat"].median()
            if label == "region_median":
                ft["lat"] = r["region"].map(med).to_numpy()
            elif label == "region_swapped":
                nxt = {a: med[b] for a, b in zip(names, names[1:] + names[:1], strict=True)}
                ft["lat"] = r["region"].map(nxt).to_numpy()
            s = evaluate.score(r, f["predict"](ft), rect_cells, prepare.LABEL)
            per_w[w] = {"male": s["male"], "male_by_region": s["male_by_region"]}
        per_w["combined"] = float(np.mean([per_w[w]["male"] for w in WINDOWS]))
        out[label] = per_w
    return out


def pd_curves(predict, rows: pd.DataFrame) -> dict:
    """Partial dependence (mean estimate with one input set to each grid value) on a fixed
    sample of main-window validation rows; ratio = sum estimate / sum Aqua over rows with Aqua>0."""
    rng = np.random.default_rng(SEED)
    ft = prepare.feature_table(rows)
    fire = ft[ft["aqua_count"] > 0]
    s_all = ft.iloc[rng.choice(len(ft), min(6000, len(ft)), replace=False)]
    s_fire = fire.iloc[rng.choice(len(fire), min(6000, len(fire)), replace=False)]
    area = fire["aqua_pixel_area_mean"]
    grids = {
        "aqua_count": np.array([1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300.0]),
        "aqua_pixel_area_mean": np.quantile(area, np.linspace(0.01, 0.99, 25)),
        "lat": np.arange(-40.0, 66.01, 0.5),
        "cal_month": np.arange(1, 13),
    }
    out: dict = {}
    for col, grid in grids.items():
        mean_est, ratio = [], []
        for v in grid:
            if col in ("aqua_count", "aqua_pixel_area_mean"):
                x = s_fire.copy()
                x[col] = v
                est = predict(x)
                mean_est.append(est.mean())
                ratio.append(est.mean() / v if col == "aqua_count" else est.sum() / x[A].sum())
            else:
                x = s_all.copy()
                x[col] = v
                mean_est.append(predict(x).mean())
                y = s_fire.copy()
                y[col] = v
                ratio.append(predict(y).sum() / y[A].sum())
        out[col] = {"grid": grid.tolist(), "mean_est": mean_est, "ratio": ratio}
    return out


def binned(rows: pd.DataFrame, est: np.ndarray, col: str, edges: np.ndarray) -> pd.DataFrame:
    """Observed sum V / sum A and predicted sum H / sum A by bins of `col` (rows with Aqua>0)."""
    t = rows.assign(H=est)
    t = t[t[A] > 0]
    t = t.assign(b=pd.cut(t[col], edges, include_lowest=True, duplicates="drop"), _x=t[col])
    by = t.groupby("b", observed=True)
    g = pd.DataFrame(
        {
            "H": by["H"].sum(),
            "V": by[prepare.LABEL].sum(),
            "A": by[A].sum(),
            "n": by.size(),
            "x": by["_x"].mean(),
        }
    )
    g = g[g["n"] >= 30]
    return pd.DataFrame({"x": g["x"], "pred": g["H"] / g["A"], "obs": g["V"] / g["A"]})


def band_shading(ax) -> None:
    for r in regions():
        if r["role"] == "train":
            ax.axvspan(r["south"], r["north"], color=COLORS[r["name"]], alpha=0.12, lw=0)
        else:
            ax.axvspan(
                r["south"],
                r["north"],
                facecolor="none",
                edgecolor=HOLD_C,
                hatch="//",
                alpha=0.5,
                lw=0,
            )
        train = r["role"] == "train"  # training labels above the plot, holdout labels inside
        ax.text(
            (r["south"] + r["north"]) / 2,
            1.0 if train else 0.02,
            r["name"].replace("_", "\n") + ("" if train else "\n(holdout)"),
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=6,
            color="#444" if train else HOLD_C,
        )


def style(ax, xlabel: str, ylabel: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(color="#e6e6e3", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


LABELS = {
    "aqua_count": "Aqua count",
    "aqua_pixel_area_mean": "Aqua mean pixel area (km2)",
    "lat": "latitude (deg)",
    "cal_month": "calendar month",
}


def plot_pd(pdc: dict, rows: pd.DataFrame, est: np.ndarray) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5))
    for ax, col in zip(axes.ravel(), LABELS, strict=True):
        c = pdc[col]
        ax.plot(
            c["grid"], c["mean_est"], color=MODEL_C, lw=2, marker="o" if col != "lat" else "", ms=4
        )
        if col == "aqua_count":
            ax.set_xscale("log")
        if col == "lat":
            band_shading(ax)
        style(ax, LABELS[col], "mean estimate (PD)")
    fig.suptitle(
        f"{FIRST}: partial dependence of the estimate (main-window validation rows;"
        " count and pixel area on rows with Aqua > 0)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(FIG / "s10-pd-estimate.png", dpi=130)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5))
    edges = {
        "aqua_count": np.array([0.5, 1.5, 2.5, 4.5, 8.5, 16.5, 32.5, 64.5, 1e4]),
        "aqua_pixel_area_mean": np.quantile(
            rows.loc[rows[A] > 0, "aqua_pixel_area_mean"], np.linspace(0, 1, 11)
        ),
        "lat": np.arange(-36.0, 43.0, 1.0),
    }
    for ax, col in zip(axes.ravel(), LABELS, strict=True):
        c = pdc[col]
        ax.plot(c["grid"], c["ratio"], color=MODEL_C, lw=2, label="model PD ratio")
        if col in edges:
            b = binned(rows, est, col, edges[col])
            ax.plot(
                b["x"],
                b["pred"],
                ls="none",
                marker="o",
                ms=5,
                color=MODEL_C,
                mfc="white",
                label="predicted sum H / sum A (binned)",
            )
            ax.plot(
                b["x"],
                b["obs"],
                ls="none",
                marker="s",
                ms=5,
                color=OBS_C,
                label="observed sum V / sum A (binned)",
            )
        else:
            t = rows.assign(H=est)
            t = t[t[A] > 0]
            for reg, g in t.groupby("region"):
                m = g.groupby("cal_month")[["H", prepare.LABEL, A]].sum()
                ax.plot(
                    m.index,
                    m[prepare.LABEL] / m[A],
                    ls="--",
                    lw=1,
                    marker="s",
                    ms=3,
                    color=COLORS[reg],
                    label=f"observed V/A {reg}",
                )
        if col == "aqua_count":
            ax.set_xscale("log")
        if col == "lat":
            band_shading(ax)
        style(ax, LABELS[col], "estimate / Aqua count")
        ax.legend(fontsize=6, frameon=False)
    fig.suptitle(f"{FIRST}: VIIRS-scale estimate per Aqua fire (rows with Aqua > 0)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "s10-pd-ratio.png", dpi=130)
    plt.close(fig)


def plot_importance(models: dict) -> dict:
    imp = {}
    for k, m in models.items():
        g = pd.Series(m.feature_importance("gain"), index=m.feature_name())
        imp[k] = (100 * g / g.sum()).round(2)
    df = pd.DataFrame(imp).fillna(0).sort_values("clf")
    fig, axes = plt.subplots(1, 2, figsize=(10, 6), sharey=True)
    titles = {"clf": "stage 1: fire / no fire classifier", "reg": "stage 2: count model"}
    for ax, k in zip(axes, ("clf", "reg"), strict=True):
        ax.barh(df.index, df[k], color=MODEL_C, height=0.6)
        for y, v in enumerate(df[k]):
            if v >= 3:
                ax.text(v + 0.5, y, f"{v:.0f}%", va="center", fontsize=7, color="#444")
        ax.set_title(titles[k], fontsize=9)
        style(ax, "share of total gain (%)", "")
        ax.grid(axis="y", visible=False)
    fig.suptitle(f"{FIRST} main window: gain importance", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "s10-importance.png", dpi=130)
    plt.close(fig)
    return {k: v.sort_values(ascending=False).to_dict() for k, v in imp.items()}


def pd_lat_summary(c: dict) -> dict:
    """Range of the lat PD inside each region's band, and the PD at each band's centre."""
    g = np.array(c["grid"])
    out = {}
    for r in regions():
        m = (g >= r["south"]) & (g <= r["north"])
        est, rat = np.array(c["mean_est"])[m], np.array(c["ratio"])[m]
        out[r["name"]] = {
            "role": r["role"],
            "mean_est_min_max": [float(est.min()), float(est.max())],
            "ratio_min_max": [float(rat.min()), float(rat.max())],
        }
    out["overall_mean_est_min_max"] = [min(c["mean_est"]), max(c["mean_est"])]
    return out


def stability(exp_id: str) -> dict:
    d = json.loads((autoexp.exp_dir() / f"{exp_id}.json").read_text(encoding="utf-8"))
    res = d["results"]
    keys = (
        "variance_power",
        "num_leaves",
        "min_data_in_leaf",
        "lambda_l2",
        "feature_fraction",
        "p_fire",
    )
    params = {k: [c.get(k) for c in d["configs"]] for k in keys}
    params["rounds"] = [c.get("rounds") for c in d["configs"]]
    return {
        "combined": res["combined_male"],
        "male": {w: res[w]["male"] for w in WINDOWS},
        "male_by_region": {w: res[w]["male_by_region"] for w in WINDOWS},
        "zero_ge1": {w: res[w]["zero_ge1"] for w in WINDOWS},
        "units": {
            w: {f"{u['region']}:{u['year']}": u["male"] for u in res[w]["units"]} for w in WINDOWS
        },
        "params_main_aux": params,
    }


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    df = prepare.load_grid()
    m1s = autoexp.m1s_reference(df)
    cells = df.loc[df["role"] == "train", prepare.KEY].drop_duplicates()
    rect_cells = prepare.rectangle_cells(cells)
    rows = {}
    for w in WINDOWS:
        _, ev = prepare.window(df, w)
        rows[w] = ev[ev["usable"].to_numpy()].reset_index(drop=True)
    csvr = csv_rows()
    out: dict = {"m1s": summary(m1s, m1s), "candidates": {}}

    fitted_first = None
    for exp_id in TOP3:
        mod = load_variant(exp_id)
        cfgs, rounds = tuned(exp_id)
        res, fitted = run(mod, cfgs, df)
        out["candidates"][exp_id] = {
            "summary": summary(res, m1s),
            "csv_combined": float(csvr[exp_id]["combined_male"]),
            "reproduced": abs(res["combined_male"] - float(csvr[exp_id]["combined_male"])) < 5e-5,
            "leakage": leakage(exp_id, mod, fitted, rounds, rows),
            "stability": stability(exp_id),
        }
        print(f"{exp_id}: combined {res['combined_male']:.4f}", flush=True)
        if exp_id == FIRST:
            fitted_first, mod_first, cfgs_first, res_first = fitted, mod, cfgs, res

    # 2. ablation of the #1 candidate (same tuned parameters, Optuna off)
    base_drop = list(cfgs_first["main"]["drop"])
    abl = {"baseline": summary(res_first, m1s)}
    for name, cols in GROUPS.items():
        if name == "no_detection_add_back":
            drop = [c for c in base_drop if c not in cols]
        else:
            drop = sorted(set(base_drop) | set(cols))
        res, _ = run(mod_first, cfgs_first, df, drop=drop)
        abl[name] = summary(res, m1s)
        abl[name]["dropped"] = drop
        print(f"ablation {name}: combined {res['combined_male']:.4f}", flush=True)
    out["ablation"] = abl

    # latitude: region identity or physics?
    out["lat_tests"] = lat_tests(fitted_first, rows, rect_cells)
    for e in ("E016", "E036", "E022", "E034", "E012", "E000"):
        st = stability(e)
        out.setdefault("lat_context", {})[e] = {k: st[k] for k in ("combined", "male_by_region")}

    # 3. prediction relationships (main window)
    p = fitted_first["main"]["predict"]
    pdc = pd_curves(p, rows["main"])
    est = p(prepare.feature_table(rows["main"]))
    plot_pd(pdc, rows["main"], est)
    out["pd"] = pdc
    out["pd_lat_summary"] = pd_lat_summary(pdc["lat"])
    edges = np.quantile(
        rows["main"].loc[rows["main"][A] > 0, "aqua_pixel_area_mean"], np.linspace(0, 1, 11)
    )
    out["pixel_area_binned"] = binned(rows["main"], est, "aqua_pixel_area_mean", edges).to_dict(
        orient="list"
    )
    out["importance_main"] = plot_importance(p.models)
    OUT_JSON.write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=float) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and reports/figures/s10-*.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
