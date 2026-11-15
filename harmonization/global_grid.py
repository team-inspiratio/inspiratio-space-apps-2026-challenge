"""Stage G: the global cells and the global dense cell x month table (docs/decisions/0013).

uv run python -X utf8 -m harmonization.global_grid build   # <data>/processed/global/grid/
uv run python -X utf8 -m harmonization.global_grid info    # cell counts per region and role

The scope is config/regions-global.json: the GFED4.1s basis regions over the whole globe. The
frozen config/regions.json is only read: its holdout boxes stay holdout (role `holdout`, no
VIIRS column, never trained on or scored) and its six boxes stay complete. Every other cell has
role `train` (it carries the S-NPP label and may be used for training and scoring).

Outputs in <data>/processed/global/grid/:
  cells.parquet       lat_idx, lon_idx, region, gfed_region, role, box (v1 box name or "")
  band_<NN>.parquet   the dense table of grid.dense_regions (same columns and values) for the
                      cells of one 10 deg latitude band, minus the unused day/night counts
Built from processed/grid/counts.parquet and month_status.parquet (S05), nothing else.
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from scipy import ndimage

from harmonization import grid, prepare
from harmonization.config import ROOT, data_dir, regions, settings

DROP = tuple(f"{s}_count_{p}" for s in grid.MODIS + grid.VIIRS for p in ("day", "night"))


@cache
def config() -> dict:
    return json.loads((ROOT / "config" / "regions-global.json").read_text(encoding="utf-8"))


def out_dir() -> Path:
    d = data_dir() / "processed" / "global" / "grid"
    d.mkdir(parents=True, exist_ok=True)
    return d


def gfed_codes() -> tuple[np.ndarray, dict[int, str]]:
    """Basis-region code per cell as [lat_idx, lon_idx] (GFED rows run north to south)."""
    sys.path.insert(0, str(ROOT / "tools"))
    from make_rectangles import gfed_basis

    codes, names = gfed_basis()
    return codes[::-1].copy(), names


def box_cells(boxes: list[dict]) -> pd.DataFrame:
    cell = settings()["grid"]["cell_deg"]
    parts = []
    for b in boxes:
        i0, i1 = round((b["south"] + 90) / cell), round((b["north"] + 90) / cell)
        j0, j1 = round((b["west"] + 180) / cell), round((b["east"] + 180) / cell)
        ii, jj = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1), indexing="ij")
        parts.append(
            pd.DataFrame({"lat_idx": ii.ravel(), "lon_idx": jj.ravel(), "name": b["name"]})
        )
    return pd.concat(parts, ignore_index=True)


def global_cells(counts: pd.DataFrame | None = None) -> pd.DataFrame:
    """The global cells with their region and role (config/regions-global.json)."""
    codes, names = gfed_codes()
    keep = codes != 0
    if counts is None:
        counts = pd.read_parquet(
            data_dir() / "processed" / "grid" / "counts.parquet", columns=["lat_idx", "lon_idx"]
        )
    keep[counts["lat_idx"].to_numpy(), counts["lon_idx"].to_numpy()] = True
    rects = prepare.rectangles().rename(columns={"region": "name"})
    for b in (box_cells(rects.to_dict("records")), box_cells(regions())):
        keep[b["lat_idx"].to_numpy(), b["lon_idx"].to_numpy()] = True
    # ocean cells take the code of the nearest land cell
    _, (ni, nj) = ndimage.distance_transform_edt(codes == 0, return_indices=True)
    filled = codes[ni, nj]
    ii, jj = np.nonzero(keep)
    cells = pd.DataFrame({"lat_idx": ii.astype(np.int64), "lon_idx": jj.astype(np.int64)})
    cells["gfed_region"] = [names[c] for c in filled[ii, jj]]
    cells["region"] = cells["gfed_region"]
    cells["role"] = "train"
    cells["box"] = ""
    idx = pd.MultiIndex.from_frame(cells[["lat_idx", "lon_idx"]])
    for r in regions():
        b = box_cells([r])
        hit = idx.isin(pd.MultiIndex.from_frame(b[["lat_idx", "lon_idx"]]))
        cells.loc[hit, "box"] = r["name"]
        if r["role"] == "holdout":
            cells.loc[hit, "region"] = r["name"]
            cells.loc[hit, "role"] = "holdout"
    return cells.sort_values(["lat_idx", "lon_idx"]).reset_index(drop=True)


def bands(cells: pd.DataFrame) -> dict[int, pd.DataFrame]:
    per = round(config()["band_deg"] / settings()["grid"]["cell_deg"])
    b = cells["lat_idx"].to_numpy() // per
    return {int(k): cells[b == k].reset_index(drop=True) for k in np.unique(b)}


def band_path(k: int) -> Path:
    return out_dir() / f"band_{k:02d}.parquet"


def build() -> dict:
    src = data_dir() / "processed" / "grid"
    counts = pd.read_parquet(src / "counts.parquet")
    status = pd.read_parquet(src / "month_status.parquet")
    cells = global_cells(counts)
    cells.to_parquet(out_dir() / "cells.parquet", index=False)
    rows = 0
    for k, c in bands(cells).items():
        # neighbours come from the full counts table, so band edges need nothing special
        dense = grid.dense_regions(counts, status, c[["lat_idx", "lon_idx", "region", "role"]])
        dense = dense.drop(columns=[x for x in DROP if x in dense])
        dense.to_parquet(band_path(k), index=False, compression="zstd")
        rows += len(dense)
        print(f"band {k:02d}: {len(c)} cells, {len(dense)} rows", flush=True)
    info = summary(cells)
    info["rows"] = rows
    (out_dir() / "build.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    (data_dir() / "G_grid.done").write_text("ok\n")
    return info


def summary(cells: pd.DataFrame) -> dict:
    return {
        "cells": int(len(cells)),
        "by_role": cells["role"].value_counts().sort_index().to_dict(),
        "by_region": cells["region"].value_counts().sort_index().to_dict(),
    }


def load_cells() -> pd.DataFrame:
    return pd.read_parquet(out_dir() / "cells.parquet")


def load(
    months: tuple[str, str] | None = None,
    columns: list[str] | None = None,
    role: str | None = None,
    band: int | None = None,
) -> pd.DataFrame:
    """Rows of the global dense table, optionally one month range, role or band only."""
    files = [band_path(band)] if band is not None else sorted(out_dir().glob("band_*.parquet"))
    d = ds.dataset([str(f) for f in files], format="parquet")
    flt = None
    if months is not None:
        flt = (ds.field("month") >= months[0]) & (ds.field("month") <= months[1])
    if role is not None:
        r = ds.field("role") == role
        flt = r if flt is None else flt & r
    return d.to_table(columns=columns, filter=flt).to_pandas()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("cmd", choices=["build", "info"])
    args = p.parse_args()
    info = build() if args.cmd == "build" else summary(global_cells())
    print(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
