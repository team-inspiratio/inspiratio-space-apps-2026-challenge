"""0.25-degree tiles of the released global-v1 dataset, for the zoomed-in map and drawn areas.

Each tile covers 10 x 10 degrees (40 x 40 cells) and holds only cells present in the release:
  header  : b'IT25' magic, uint32 n_cells, uint32 n_months
  idx     : uint16[n]      local cell index = row * 40 + col
                           (row from tile south, col from tile west)
  harm_q  : uint8[n * T]   harmonized value for drawing, log-quantized:
                           round(254 * log1p(v) / log1p(VMAX))
  raw     : uint16[n * T]  direct splice (est_m0) exact count; 65535 = no value
Files are gzip-compressed: tiles/<ty>_<tx>.bin.gz, plus tiles/index.json.
Reads only the published release.
Usage: python -I build_tiles.py <dataset_global-v1.parquet> <out_dir>
"""

import gzip
import json
import struct
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
f = pq.ParquetFile(src)

months: list[str] = []
y, m = 2000, 11
while (y, m) <= (2026, 10):
    months.append(f"{y}-{m:02d}")
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
T = len(months)
midx = {s: i for i, s in enumerate(months)}

# Dense global arrays at 0.25 degrees: 720 x 1440 cells x T months.
H, W = 720, 1440
present = np.zeros((H, W), bool)
harm = np.zeros((H, W, T), np.float32)
raw = np.full((H, W, T), 65535, np.uint16)
raw_max = 0.0
for g in range(f.metadata.num_row_groups):
    t = f.read_row_group(g, columns=["lat_idx", "lon_idx", "month", "est", "est_m0"]).to_pandas()
    mi = t["month"].map(midx)
    ok = mi.notna().to_numpy()
    t = t[ok]
    mi = mi[ok].to_numpy(np.int64)
    la = t["lat_idx"].to_numpy(np.int64)
    lo = t["lon_idx"].to_numpy(np.int64)
    present[la, lo] = True
    harm[la, lo, mi] = np.nan_to_num(t["est"].to_numpy(np.float32))
    m0 = t["est_m0"].to_numpy(np.float64)
    has = ~np.isnan(m0)
    raw_max = max(raw_max, float(np.nanmax(m0)) if has.any() else 0.0)
    raw[la[has], lo[has], mi[has]] = np.clip(np.round(m0[has]), 0, 65534).astype(np.uint16)
    print(f"row group {g + 1}/{f.metadata.num_row_groups}", flush=True)

nz = harm[present]
VMAX = float(np.percentile(nz.max(axis=1), 99.5))
scale = np.log1p(VMAX)
tiles = []
total = 0
for ty in range(18):
    for tx in range(36):
        sub = present[ty * 40 : (ty + 1) * 40, tx * 40 : (tx + 1) * 40]
        r, c = np.nonzero(sub)
        if not r.size:
            continue
        gr, gc = r + ty * 40, c + tx * 40
        hq = np.clip(
            np.round(254 * np.log1p(np.maximum(harm[gr, gc, :], 0)) / scale), 0, 254
        ).astype(np.uint8)
        rw = raw[gr, gc, :].astype("<u2")
        idx = (r * 40 + c).astype("<u2")
        body = struct.pack("<4sII", b"IT25", r.size, T) + idx.tobytes() + hq.tobytes()
        if len(body) % 2:
            body += b"\0"
        body += rw.tobytes()
        name = f"{ty}_{tx}.bin.gz"
        data = gzip.compress(body, compresslevel=9)
        (out / name).write_bytes(data)
        total += len(data)
        tiles.append({"ty": ty, "tx": tx, "n": int(r.size), "bytes": len(data)})

(out / "index.json").write_text(
    json.dumps(
        {"tile_deg": 10, "cells_per_side": 40, "months": months, "vmax": VMAX, "tiles": tiles},
        separators=(",", ":"),
    )
)
print(
    "tiles",
    len(tiles),
    "total MB",
    round(total / 1e6, 1),
    "VMAX",
    round(VMAX, 1),
    "raw max",
    raw_max,
)
