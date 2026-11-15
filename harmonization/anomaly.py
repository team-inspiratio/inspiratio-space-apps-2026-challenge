"""Anomaly indicator of the web page: reference implementation and the standard test cases.

  uv run python -X utf8 -m harmonization.anomaly cases    # writes docs/anomaly-cases.json

Rules: proposal "Anomaly indicators" and docs/data-interface.md section 6. The front end
implements the same function and checks itself against docs/anomaly-cases.json (every case:
input -> expected output).
Decisions the proposal leaves open are fixed here and in docs/decisions/0011:

  series     list of months {"month": "YYYY-MM", "value": float | None, "input_complete": bool,
             "source": str, "nrt": bool} for one area (a preset region, or the cell sum of a
             user-drawn area); months not listed count as no data
  finished   a month is over when the as-of date (UTC, "YYYY-MM-DD") is on or after the first day
             of the next month; an unfinished month gets no anomaly, only its value so far
  reference  same calendar month, years from REF_START (2001) to the year before the target,
             value present and input_complete true; baseline "snpp" keeps only source "snpp"
  ties       values are given to 2 decimals, so x counts as equal to h when |x - h| <= TIE_EPS
             (0.005) and as smaller when x < h - TIE_EPS
  percentile 100 * (smaller + 0.5 * equal) / n
  median     usual median (mean of the two middle values when n is even)
  ratio      h / median, only when median >= MIN_MEDIAN (5); otherwise None and note
             "small_median" ("this month usually has very few detections")
  level      "high" if percentile >= 90, "low" if <= 10, else "normal"; only when n >= MIN_REF
             (10), otherwise None and status "insufficient_history"
status, checked in this order:
  no_data               the target month has no value
  month_in_progress     the target month is not over (value = detections so far)
  incomplete_coverage   the target month has missing days: value shown, nothing else
  no_history            no reference month at all
  insufficient_history  1..9 reference months: percentile, median, ratio, but no level
  ok                    level given
`preliminary` is true when the target value comes from near-real-time data (`nrt`).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys

import numpy as np
import pandas as pd

from harmonization.config import ROOT, data_dir

REF_START = 2001
MIN_REF = 10
MIN_MEDIAN = 5.0
TIE_EPS = 0.005
HIGH, LOW = 90.0, 10.0
CASES = ROOT / "docs" / "anomaly-cases.json"
LABELS = {  # proposal "Wording": never fire counts, burned area or severity
    "high": {
        "zh": "火点活动偏高（VIIRS 等效估计）",
        "en": "Fire activity above normal (VIIRS-equivalent estimate)",
    },
    "normal": {
        "zh": "火点活动正常（VIIRS 等效估计）",
        "en": "Fire activity normal (VIIRS-equivalent estimate)",
    },
    "low": {
        "zh": "火点活动偏低（VIIRS 等效估计）",
        "en": "Fire activity below normal (VIIRS-equivalent estimate)",
    },
}
NOTES = {
    "small_median": {
        "zh": "该月历史上通常很少记录到火点",
        "en": "This month usually has very few detections",
    },
    "insufficient_history": {
        "zh": "历史不足（参考年数少于 10）",
        "en": "Not enough history (fewer than 10 reference years)",
    },
    "preliminary": {"zh": "初步结果（近实时数据）", "en": "Preliminary (near-real-time data)"},
    "incomplete_coverage": {"zh": "覆盖不完整", "en": "Incomplete coverage"},
}


def month_over(month: str, as_of: str) -> bool:
    y, m = int(month[:4]), int(month[5:7])
    nxt = f"{y + (m == 12):04d}-{m % 12 + 1:02d}-01"
    return as_of >= nxt


def anomaly(series: list[dict], target: str, as_of: str, baseline: str = "all") -> dict:
    if baseline not in ("all", "snpp"):
        raise ValueError(f"unknown baseline {baseline!r}")
    by_month = {s["month"]: s for s in series}
    t = by_month.get(target)
    out = {
        "status": None,
        "value": None,
        "n_ref": 0,
        "ref_years": [],
        "median": None,
        "ratio": None,
        "percentile": None,
        "level": None,
        "preliminary": False,
        "notes": [],
    }
    if t is None or t.get("value") is None:
        out["status"] = "no_data"
        return out
    h = float(t["value"])
    out["value"] = h
    out["preliminary"] = bool(t.get("nrt", False))
    if out["preliminary"]:
        out["notes"].append("preliminary")
    if not month_over(target, as_of):
        out["status"] = "month_in_progress"
        return out
    if not t.get("input_complete", True):
        out["status"] = "incomplete_coverage"
        out["notes"].append("incomplete_coverage")
        return out
    year, cal = int(target[:4]), target[5:7]
    refs = []
    for s in series:
        y = int(s["month"][:4])
        if s["month"][5:7] != cal or not (REF_START <= y < year):
            continue
        if s.get("value") is None or not s.get("input_complete", True):
            continue
        if baseline == "snpp" and s.get("source") != "snpp":
            continue
        refs.append((y, float(s["value"])))
    refs.sort()
    out["n_ref"] = len(refs)
    out["ref_years"] = [y for y, _ in refs]
    if not refs:
        out["status"] = "no_history"
        return out
    x = np.array([v for _, v in refs])
    smaller = int((x < h - TIE_EPS).sum())
    equal = int((np.abs(x - h) <= TIE_EPS).sum())
    out["percentile"] = 100.0 * (smaller + 0.5 * equal) / len(x)
    out["median"] = float(statistics.median(x.tolist()))
    if out["median"] >= MIN_MEDIAN:
        out["ratio"] = h / out["median"]
    else:
        out["notes"].append("small_median")
    if len(x) < MIN_REF:
        out["status"] = "insufficient_history"
        out["notes"].append("insufficient_history")
        return out
    p = out["percentile"]
    out["level"] = "high" if p >= HIGH else "low" if p <= LOW else "normal"
    out["status"] = "ok"
    return out


# --- standard test cases -------------------------------------------------------------------
def m(month: str, value, complete: bool = True, source: str = "model_aqua", nrt: bool = False):
    return {
        "month": month,
        "value": value,
        "input_complete": complete,
        "source": source,
        "nrt": nrt,
    }


def july(years, values, **kw) -> list[dict]:
    return [m(f"{y}-07", v, **kw) for y, v in zip(years, values, strict=True)]


def hand_cases() -> list[dict]:
    """Edge cases with expected values worked out by hand (not by running anomaly())."""
    D = "2026-11-03"  # as-of date for finished months
    cases = []

    def case(cid, desc, series, target, expected, as_of=D, baseline="all"):
        cases.append(
            {
                "id": cid,
                "description": desc,
                "input": {"series": series, "target": target, "as_of": as_of, "baseline": baseline},
                "expected": expected,
            }
        )

    base = {"value": None, "n_ref": 0, "ref_years": [], "median": None, "ratio": None}
    base |= {"percentile": None}
    base |= {"level": None, "preliminary": False, "notes": []}
    yrs = list(range(2005, 2020))
    case(
        "basic_high",
        "15 reference Julys 1..15, target 20: percentile 100, median 8, ratio 2.5. The June of the"
        " target year and a later July are not references.",
        july(yrs, range(1, 16)) + [m("2020-06", 999.0), m("2020-07", 20.0), m("2021-07", 0.0)],
        "2020-07",
        {**base, "status": "ok", "value": 20.0, "n_ref": 15, "ref_years": yrs, "median": 8.0}
        | {"ratio": 2.5, "percentile": 100.0, "level": "high"},
    )
    yrs = list(range(2001, 2016))
    vals = [5, 5, 5, 1, 1, 1, 1, 1, 9, 9, 9, 9, 9, 9, 9]
    case(
        "ties_count_half",
        "Equal values count half: 5 smaller, 3 equal of 15 -> 100 * 6.5 / 15.",
        [m(f"{y}-03", float(v)) for y, v in zip(yrs, vals, strict=True)] + [m("2016-03", 5.0)],
        "2016-03",
        {**base, "status": "ok", "value": 5.0, "n_ref": 15, "ref_years": yrs, "median": 5.0}
        | {"ratio": 1.0, "percentile": 100 * 6.5 / 15, "level": "normal"},
    )
    yrs = list(range(2010, 2020))
    case(
        "boundary_90_is_high",
        "Percentile exactly 90 is high (10 references 1..10, target 9.5).",
        july(yrs, [float(v) for v in range(1, 11)]) + [m("2020-07", 9.5)],
        "2020-07",
        {**base, "status": "ok", "value": 9.5, "n_ref": 10, "ref_years": yrs, "median": 5.5}
        | {"ratio": 9.5 / 5.5, "percentile": 90.0, "level": "high"},
    )
    case(
        "boundary_10_is_low",
        "Percentile exactly 10 is low (10 references 1..10, target 1.5).",
        july(yrs, [float(v) for v in range(1, 11)]) + [m("2020-07", 1.5)],
        "2020-07",
        {**base, "status": "ok", "value": 1.5, "n_ref": 10, "ref_years": yrs, "median": 5.5}
        | {"ratio": 1.5 / 5.5, "percentile": 10.0, "level": "low"},
    )
    yrs = list(range(2011, 2020))
    case(
        "insufficient_history",
        "9 reference years: numbers shown, no level.",
        july(yrs, [float(v) for v in range(1, 10)]) + [m("2020-07", 100.0)],
        "2020-07",
        {**base, "status": "insufficient_history", "value": 100.0, "n_ref": 9, "ref_years": yrs}
        | {"median": 5.0, "ratio": 20.0, "percentile": 100.0, "notes": ["insufficient_history"]},
    )
    yrs = list(range(2008, 2020))
    vals = [0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 10, 20]
    case(
        "small_median_no_ratio",
        "Median 0.5 (< 5): no ratio, note small_median; 10 of 12 smaller.",
        july(yrs, [float(v) for v in vals]) + [m("2020-07", 6.0)],
        "2020-07",
        {**base, "status": "ok", "value": 6.0, "n_ref": 12, "ref_years": yrs, "median": 0.5}
        | {"percentile": 100 * 10 / 12, "level": "normal", "notes": ["small_median"]},
    )
    yrs = list(range(2010, 2020))
    case(
        "median_zero_any_fire_is_high",
        "All references 0, target 3: percentile 100 and high, no ratio (division by 0 avoided).",
        july(yrs, [0.0] * 10) + [m("2020-07", 3.0)],
        "2020-07",
        {**base, "status": "ok", "value": 3.0, "n_ref": 10, "ref_years": yrs, "median": 0.0}
        | {"percentile": 100.0, "level": "high", "notes": ["small_median"]},
    )
    case(
        "median_zero_zero_is_normal",
        "All references 0, target 0: all equal -> percentile 50, normal.",
        july(yrs, [0.0] * 10) + [m("2020-07", 0.0)],
        "2020-07",
        {**base, "status": "ok", "value": 0.0, "n_ref": 10, "ref_years": yrs, "median": 0.0}
        | {"percentile": 50.0, "level": "normal", "notes": ["small_median"]},
    )
    case(
        "incomplete_target",
        "Target month has missing days: value shown, no percentile or level.",
        july(yrs, [10.0] * 10) + [m("2020-07", 50.0, complete=False)],
        "2020-07",
        {**base, "status": "incomplete_coverage", "value": 50.0, "notes": ["incomplete_coverage"]},
    )
    yrs12 = list(range(2001, 2013))
    ser = [m(f"{y}-08", float(i + 1), complete=y not in (2003, 2004)) for i, y in enumerate(yrs12)]
    keep = [y for y in yrs12 if y not in (2003, 2004)]
    case(
        "incomplete_references_dropped",
        "Reference years with missing days (2003, 2004) are left out: n = 10.",
        ser + [m("2013-08", 4.0)],
        "2013-08",
        {**base, "status": "ok", "value": 4.0, "n_ref": 10, "ref_years": keep, "median": 7.5}
        | {"ratio": 4.0 / 7.5, "percentile": 20.0, "level": "normal"},
    )
    yrs = list(range(2001, 2015))
    case(
        "year_2000_not_a_reference",
        "Default baseline starts in 2001: 2000-11 (value 0) is not a reference.",
        [m("2000-11", 0.0, source="model_terra_bridge")]
        + [m(f"{y}-11", 10.0) for y in yrs]
        + [m("2015-11", 10.0)],
        "2015-11",
        {**base, "status": "ok", "value": 10.0, "n_ref": 14, "ref_years": yrs, "median": 10.0}
        | {"ratio": 1.0, "percentile": 50.0, "level": "normal"},
    )
    yrs = list(range(2016, 2026))
    octs = [m(f"{y}-10", float(v), source="snpp") for y, v in zip(yrs, range(10, 20), strict=True)]
    case(
        "month_in_progress",
        "As-of date inside the target month: only the value so far, no anomaly.",
        octs + [m("2026-10", 15.0, source="snpp", nrt=True)],
        "2026-10",
        {**base, "status": "month_in_progress", "value": 15.0, "preliminary": True}
        | {"notes": ["preliminary"]},
        as_of="2026-10-20",
    )
    case(
        "finished_on_first_day_preliminary",
        "As-of 2026-11-01: October is over. Near-real-time value -> preliminary.",
        octs + [m("2026-10", 15.0, source="snpp", nrt=True)],
        "2026-10",
        {**base, "status": "ok", "value": 15.0, "n_ref": 10, "ref_years": yrs, "median": 14.5}
        | {"ratio": 15.0 / 14.5, "percentile": 55.0, "level": "normal", "preliminary": True}
        | {"notes": ["preliminary"]},
        as_of="2026-11-01",
    )
    yrs = list(range(2005, 2020))
    ser = [m(f"{y}-07", 1.0) for y in range(2005, 2014)] + [
        m(f"{y}-07", float(v), source="snpp")
        for y, v in zip(range(2014, 2020), range(10, 16), strict=True)
    ]
    ser.append(m("2020-07", 12.0, source="snpp"))
    case(
        "baseline_snpp",
        "Baseline snpp keeps only S-NPP months: 6 references (10..15) -> no level.",
        ser,
        "2020-07",
        {**base, "status": "insufficient_history", "value": 12.0, "n_ref": 6}
        | {"ref_years": list(range(2014, 2020)), "median": 12.5, "ratio": 12.0 / 12.5}
        | {"percentile": 100 * 2.5 / 6, "notes": ["insufficient_history"]},
        baseline="snpp",
    )
    case(
        "baseline_all_same_series",
        "Same series, default baseline: 15 references, median 1 -> no ratio; 11 smaller, 1 equal.",
        ser,
        "2020-07",
        {**base, "status": "ok", "value": 12.0, "n_ref": 15, "ref_years": yrs, "median": 1.0}
        | {"percentile": 100 * 11.5 / 15, "level": "normal", "notes": ["small_median"]},
    )
    yrs = list(range(2010, 2020))
    case(
        "tie_tolerance_equal",
        "3.004 against references of 3.0: equal within 0.005 -> percentile 50.",
        july(yrs, [3.0] * 10) + [m("2020-07", 3.004)],
        "2020-07",
        {**base, "status": "ok", "value": 3.004, "n_ref": 10, "ref_years": yrs, "median": 3.0}
        | {"percentile": 50.0, "level": "normal", "notes": ["small_median"]},
    )
    case(
        "tie_tolerance_larger",
        "3.006 against references of 3.0: larger -> percentile 100.",
        july(yrs, [3.0] * 10) + [m("2020-07", 3.006)],
        "2020-07",
        {**base, "status": "ok", "value": 3.006, "n_ref": 10, "ref_years": yrs, "median": 3.0}
        | {"percentile": 100.0, "level": "high", "notes": ["small_median"]},
    )
    case(
        "no_data",
        "Target month not in the series (or value null).",
        july(yrs, [3.0] * 10) + [m("2020-08", None)],
        "2020-08",
        {**base, "status": "no_data"},
    )
    case(
        "no_history",
        "First year of the record: no reference month.",
        [m("2000-11", 5.0, source="model_terra_bridge"), m("2001-03", 7.0)],
        "2001-03",
        {**base, "status": "no_history", "value": 7.0},
    )
    return cases


REAL = (  # (region, target, as_of, baseline): real region totals of dataset v1
    ("california", "2020-09", "2026-11-03", "all"),
    ("california", "2020-09", "2026-11-03", "snpp"),
    ("southern_africa", "2026-08", "2026-11-03", "all"),
    ("cordoba", "2026-10", "2026-11-03", "all"),
    ("cordoba", "2026-10", "2026-10-15", "all"),
    ("indo_gangetic", "2016-11", "2026-11-03", "all"),
)


def real_cases() -> list[dict]:
    """Region totals of dataset v1 (only the target's calendar month is needed); the expected
    output is this implementation's, so these cases pin the behaviour on real numbers."""
    tot = pd.read_csv(
        data_dir() / "processed" / "v1" / "region_totals_v1.csv", dtype={"month": str}
    )
    out = []
    for region, target, as_of, baseline in REAL:
        g = tot[(tot["region"] == region) & (tot["month"].str[5:7] == target[5:7])]
        series = [
            m(
                r.month,
                round(float(r.est), 2),
                bool(r.input_complete),
                str(r.source),
                bool(r.nrt),
            )
            for r in g.itertuples()
        ]
        exp = anomaly(series, target, as_of, baseline)
        out.append(
            {
                "id": f"real_{region}_{target}_{baseline}_{as_of}",
                "description": f"Dataset v1 region total, {region}, target {target}, as-of {as_of},"
                f" baseline {baseline} (expected = reference implementation).",
                "input": {"series": series, "target": target, "as_of": as_of, "baseline": baseline},
                "expected": exp,
            }
        )
    return out


def write_cases() -> dict:
    doc = {
        "about": "Standard test cases for the anomaly indicator (docs/data-interface.md section 6,"
        " harmonization/anomaly.py). For each case, call anomaly(series, target, as_of, baseline)"
        " and compare every field of `expected`; numbers to 1e-9 relative, lists exactly.",
        "rules": {
            "ref_start_year": REF_START,
            "min_reference_years": MIN_REF,
            "min_median_for_ratio": MIN_MEDIAN,
            "tie_epsilon": TIE_EPS,
            "high_percentile_at_least": HIGH,
            "low_percentile_at_most": LOW,
        },
        "labels": LABELS,
        "notes": NOTES,
        "cases": hand_cases() + real_cases(),
    }
    CASES.write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return doc


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("what", choices=["cases"])
    p.parse_args()
    doc = write_cases()
    print(f"{len(doc['cases'])} cases written to {CASES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
