"""Build the compact assets the site's WebGL stage needs, from the released global-v1 parquet.

Reads only the published, harmonized release (no raw satellite records, nothing from 2012-13 S-NPP).
Outputs into site/public/stage/:
  cells.json      1-degree cells that ever burn: centre lat/lon, holdout flag; month list; scale
  harm.bin        uint8 [cells x months], log-quantized harmonized counts (est)
  raw.bin         uint8 [cells x months], log-quantized direct-splice counts (est_m0); 255 = no data
  annual.json     global yearly totals for train cells, raw vs harmonized
  scatter.json    sampled (aqua_count, snpp_count) monthly pairs, train cells, 2014-01..2021-06
Usage: python -I build_assets.py <dataset_global-v1.parquet> <out_dir>
"""

import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

f = pq.ParquetFile(src)
cols = [
    "lat_idx",
    "lon_idx",
    "role",
    "month",
    "est",
    "est_m0",
    "aqua_count",
    "snpp_count",
    "input_complete",
]

months: list[str] = []
y, m = 2000, 11
while (y, m) <= (2026, 10):
    months.append(f"{y}-{m:02d}")
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
T = len(months)
midx = {s: i for i, s in enumerate(months)}

H, W = 180, 360
harm = np.zeros((H, W, T), np.float32)
raw = np.zeros((H, W, T), np.float32)
rawnull = np.zeros((H, W, T), np.int32)
rawcount = np.zeros((H, W, T), np.int32)
hold = np.zeros((H, W), np.int32)
train = np.zeros((H, W), np.int32)
yr_raw: dict[int, float] = {}
yr_harm: dict[int, float] = {}
yr_rawnull: dict[int, int] = {}

rng = np.random.default_rng(20261114)
pairs_x: list[np.ndarray] = []
pairs_y: list[np.ndarray] = []
zero_pairs = 0
total_pairs = 0

for g in range(f.metadata.num_row_groups):
    t = f.read_row_group(g, columns=cols).to_pandas()
    mi = t["month"].map(midx).to_numpy()
    ok = ~np.isnan(mi.astype(float))
    t = t[ok]
    mi = mi[ok].astype(np.int64)
    la = (t["lat_idx"].to_numpy() // 4).astype(np.int64)
    lo = (t["lon_idx"].to_numpy() // 4).astype(np.int64)
    est = t["est"].to_numpy(np.float32)
    m0 = t["est_m0"].to_numpy(np.float32)
    is_train = (t["role"] == "train").to_numpy()
    np.add.at(harm, (la, lo, mi), np.nan_to_num(est))
    m0null = np.isnan(m0)
    np.add.at(raw, (la, lo, mi), np.nan_to_num(m0))
    np.add.at(rawnull, (la, lo, mi), m0null.astype(np.int32))
    np.add.at(rawcount, (la, lo, mi), 1)
    np.add.at(hold, (la, lo), (~is_train).astype(np.int32))
    np.add.at(train, (la, lo), is_train.astype(np.int32))
    yrs = np.array([int(months[i][:4]) for i in range(T)])[mi]
    for yy in np.unique(yrs):
        s = (yrs == yy) & is_train
        yr_harm[int(yy)] = yr_harm.get(int(yy), 0.0) + float(np.nansum(est[s].astype(np.float64)))
        yr_raw[int(yy)] = yr_raw.get(int(yy), 0.0) + float(np.nansum(m0[s].astype(np.float64)))
        yr_rawnull[int(yy)] = yr_rawnull.get(int(yy), 0) + int(m0null[s].sum())
    # Paired monthly counts in the observed overlap, training cells only, 2014-01..2021-06.
    ms = t["month"].to_numpy()
    win = is_train & (ms >= "2014-01") & (ms <= "2021-06") & t["input_complete"].to_numpy(bool)
    ax = t["aqua_count"].to_numpy(np.float32)
    sy = t["snpp_count"].to_numpy(np.float32)
    both = win & ~np.isnan(ax) & ~np.isnan(sy)
    total_pairs += int(both.sum())
    nz = both & ((ax > 0) | (sy > 0))
    zero_pairs += int((both & ~nz).sum())
    idx = np.flatnonzero(nz)
    if idx.size:
        take = rng.random(idx.size) < 0.02
        pairs_x.append(ax[idx[take]])
        pairs_y.append(sy[idx[take]])
    print(f"row group {g + 1}/{f.metadata.num_row_groups}", flush=True)

# Keep 1-degree cells that ever burn in the harmonized record.
burn = harm.sum(axis=2) > 0
la_i, lo_i = np.nonzero(burn)
N = la_i.size
vmax = float(np.percentile(harm[burn].max(axis=1), 99.5))
scale = np.log1p(vmax)


def q(a: np.ndarray) -> np.ndarray:
    return np.clip(np.round(254 * np.log1p(np.maximum(a, 0)) / scale), 0, 254).astype(np.uint8)


H8 = q(harm[la_i, lo_i, :])
R8 = q(raw[la_i, lo_i, :])
# A 1-degree cell-month is "no data" in the direct splice when every 0.25-degree child is null.
allnull = rawnull[la_i, lo_i, :] >= np.maximum(rawcount[la_i, lo_i, :], 1)
R8[allnull] = 255
H8.tofile(out / "harm.bin")
R8.tofile(out / "raw.bin")

holdflag = (hold[la_i, lo_i] > train[la_i, lo_i]).astype(int)
(out / "cells.json").write_text(
    json.dumps(
        {
            "n": int(N),
            "months": months,
            "lat": (la_i - 90 + 0.5).tolist(),
            "lon": (lo_i - 180 + 0.5).tolist(),
            "holdout": holdflag.tolist(),
            "vmax": vmax,
            "encoding": (
                "uint8 = round(254*log1p(v)/log1p(vmax)); "
                "raw 255 = no data; row-major [cell][month]"
            ),
        },
        separators=(",", ":"),
    )
)

years = sorted(yr_harm)
(out / "annual.json").write_text(
    json.dumps(
        {
            "scope": "train cells (14 GFED regions); same scope as the site's direct splice",
            "years": years,
            "harm": [round(yr_harm[y]) for y in years],
            "raw": [round(yr_raw[y]) if yr_rawnull[y] == 0 else None for y in years],
        },
        separators=(",", ":"),
    )
)

X = np.concatenate(pairs_x)
Y = np.concatenate(pairs_y)
(out / "scatter.json").write_text(
    json.dumps(
        {
            "window": "2014-01..2021-06, training cells, complete months",
            "pairs_total": total_pairs,
            "pairs_both_zero": zero_pairs,
            "sample_rate": 0.02,
            "x_aqua": X.round(2).tolist(),
            "y_snpp": Y.round(2).tolist(),
        },
        separators=(",", ":"),
    )
)

print("cells", N, "months", T, "vmax", round(vmax, 1), "scatter", X.size)
for y in (2011, 2014):
    print(y, "raw", round(yr_raw[y]), "harm", round(yr_harm[y]), "rawnull", yr_rawnull[y])
