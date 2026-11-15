"""Sum the 14 GFED training regions from the release CSV for the world monthly series.

Holdout boxes are excluded. Intervals are omitted because quantiles do not add.
Usage: python -I build_world.py <region_totals_global-v1.csv> <out.json>
"""

import csv
import json
import sys
from collections import defaultdict

HOLDOUT = {"north_australia", "central_siberia", "indo_gangetic"}
rows = defaultdict(list)
with open(sys.argv[1], newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["region"] not in HOLDOUT:
            rows[r["month"]].append(r)
months = sorted(rows)
out = {
    "months": months,
    "est": [],
    "est_m0": [],
    "source": [],
    "nrt": [],
    "input_complete": [],
    "regions": 0,
}
for m in months:
    rs = rows[m]
    out["regions"] = len(rs)
    out["est"].append(round(sum(float(r["est"]) for r in rs), 2))
    m0 = [r["est_m0"] for r in rs]
    out["est_m0"].append(None if any(v == "" for v in m0) else round(sum(float(v) for v in m0), 2))
    src = {r["source"] for r in rs}
    out["source"].append(src.pop() if len(src) == 1 else "mixed")
    out["nrt"].append(any(r["nrt"] == "True" for r in rs))
    out["input_complete"].append(all(r["input_complete"] == "True" for r in rs))
json.dump(out, open(sys.argv[2], "w"), separators=(",", ":"))


def y(yr, k):
    return sum(
        v for mm, v in zip(months, out[k], strict=False) if mm.startswith(yr) and v is not None
    )


print(
    len(months),
    "months;",
    out["regions"],
    "regions; 2011 raw",
    round(y("2011", "est_m0")),
    "2014 raw",
    round(y("2014", "est_m0")),
    "2011 harm",
    round(y("2011", "est")),
)
