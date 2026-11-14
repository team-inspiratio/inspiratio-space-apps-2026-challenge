"""S01: fixed-seed random scoring rectangles (plan section 3.1). Writes config/rectangles.csv.

uv run python tools/make_rectangles.py

- every region in config/regions.json (train and holdout): 200 squares fully inside the box;
- every GFED4.1s basis region: ~150 squares whose centre cell is in the region, with at least half
  of their 0.25 deg cells in it, not crossing the antimeridian, and not touching any holdout box
  (holdout VIIRS never reaches this machine).
Side lengths are uniform on 1.0, 1.25, ..., 5.0 deg; edges lie on the 0.25 deg grid. Uses only
the GFED basis-region map (no fire data of any kind).
"""

from __future__ import annotations

import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harmonization.config import ROOT, data_dir, regions, settings  # noqa: E402

CELL = 0.25


def gfed_basis() -> tuple[np.ndarray, dict[int, str]]:
    """Basis-region codes on the 0.25 deg grid; row 0 is the northernmost row (89.875N)."""
    path = data_dir() / "raw" / "gfed" / "GFED4.1s_2003.hdf5"
    with h5py.File(path, "r") as f:
        ds = f["ancill/basis_regions"]
        codes = ds[:].astype(int)
        names = {
            int(k.split("_")[1]): str(v).split(" ")[0]
            for k, v in ds.attrs.items()
            if k.startswith("class_")
        }
    return codes, names


def boxes_overlap(a: tuple, b: tuple) -> bool:
    w1, s1, e1, n1 = a
    w2, s2, e2, n2 = b
    return w1 <= e2 and w2 <= e1 and s1 <= n2 and s2 <= n1


def main() -> int:
    cfg = settings()["scoring"]
    rng = np.random.default_rng(settings()["seeds"]["rectangles"])
    side_cells = np.arange(
        round(cfg["rect_side_deg"]["min"] / CELL), round(cfg["rect_side_deg"]["max"] / CELL) + 1
    )
    holdouts = [
        (r["west"], r["south"], r["east"], r["north"]) for r in regions() if r["role"] == "holdout"
    ]
    rows = []

    for r in regions():
        n_w = round((r["east"] - r["west"]) / CELL)
        n_h = round((r["north"] - r["south"]) / CELL)
        for _ in range(cfg["rect_per_demo_region"]):
            k = int(rng.choice(side_cells[side_cells <= min(n_w, n_h)]))
            i = int(rng.integers(0, n_w - k + 1))
            j = int(rng.integers(0, n_h - k + 1))
            west, south = r["west"] + i * CELL, r["south"] + j * CELL
            rows.append(
                ("demo", r["name"], r["role"], west, south, west + k * CELL, south + k * CELL)
            )

    codes, names = gfed_basis()
    for code in sorted(c for c in names if c != 0):
        cells = np.argwhere(codes == code)
        made = tries = 0
        while made < cfg["rect_per_gfed_region"] and tries < 200_000:
            tries += 1
            k = int(rng.choice(side_cells))
            row, col = cells[rng.integers(len(cells))]
            top, left = row - k // 2, col - k // 2
            if top < 0 or left < 0 or top + k > codes.shape[0] or left + k > codes.shape[1]:
                continue
            block = codes[top : top + k, left : left + k]
            if (block == code).mean() < 0.5:
                continue
            west = -180 + left * CELL
            north = 90 - top * CELL
            box = (west, north - k * CELL, west + k * CELL, north)
            if any(boxes_overlap(box, h) for h in holdouts):
                continue
            rows.append(("gfed", names[code], "train", *box))
            made += 1
        if made < cfg["rect_per_gfed_region"]:
            print(f"warning: {names[code]} only {made} rectangles")

    df = pd.DataFrame(rows, columns=["set", "region", "role", "west", "south", "east", "north"])
    df.insert(0, "rect_id", range(len(df)))
    df["side_deg"] = df["east"] - df["west"]
    out = ROOT / "config" / "rectangles.csv"
    df.to_csv(out, index=False, lineterminator="\n", float_format="%.2f")
    print(df.groupby(["set", "region"]).size().to_string())
    print(f"wrote {len(df)} rectangles to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
