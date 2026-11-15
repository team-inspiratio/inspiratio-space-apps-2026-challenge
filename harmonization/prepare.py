"""S07 judge, part 1: data for the two validation windows (frozen after S07).

Reads the frozen settings, regions and rectangles; never reads a test set. Everything here is
fixed before any model is fitted (docs/preregistration.md sections 0-2):
  - the label is the S-NPP monthly count `snpp_count` (target scale);
  - a cell-month is usable only when the label sensor and every MODIS input sensor that is
    operating are `complete` (missing and partial months never enter training or scoring);
  - training and scoring use the cells of the training regions only;
  - `feature_table()` is the only view a model's predict() ever gets: the cell key and the
    features of config/features.json, no VIIRS column, no month or year column.

uv run python -m harmonization.prepare      # prints the size of every window
"""

from __future__ import annotations

import json
import sys
from functools import cache
from pathlib import Path

import numpy as np
import pandas as pd

from harmonization.config import ROOT, data_dir, settings

LABEL = "snpp_count"
LABEL_STATUS = "snpp_status"
MODIS_STATUS = ("aqua_status", "terra_status")
KEY = ["lat_idx", "lon_idx"]
WINDOWS = {  # name -> (training split, evaluation split) in config/settings.yaml
    "main": ("train", "validation"),
    "aux": ("aux_train", "aux_validation"),
}


@cache
def features() -> list[str]:
    return json.loads((ROOT / "config" / "features.json").read_text(encoding="utf-8"))["features"]


def grid_path() -> Path:
    return data_dir() / "processed" / "grid" / "regions.parquet"


def load_grid(path: Path | None = None) -> pd.DataFrame:
    """Dense cell x month table from S05 (MODIS features, VIIRS labels, sensor status)."""
    return pd.read_parquet(path or grid_path())


def months(split: str) -> tuple[str, str]:
    s = settings()["splits"][split]
    return s["start"], s["end"]


def usable(df: pd.DataFrame) -> np.ndarray:
    """Label sensor complete, and every operating MODIS sensor complete."""
    ok = (df[LABEL_STATUS] == "complete").to_numpy().copy()
    for col in MODIS_STATUS:
        ok &= df[col].isin(["complete", "not_operating"]).to_numpy()
    return ok & df[LABEL].notna().to_numpy()


def in_months(df: pd.DataFrame, split: str) -> np.ndarray:
    start, end = months(split)
    return ((df["month"] >= start) & (df["month"] <= end)).to_numpy()


def window(df: pd.DataFrame, name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(training table, evaluation table) of a validation window, training regions only.

    The training table holds usable rows only. The evaluation table holds every cell-month of
    the window with a `usable` flag, so the judge can report the share excluded for missing data.
    """
    train_split, eval_split = WINDOWS[name]
    train_cells = (df["role"] == "train").to_numpy()
    ok = usable(df)
    train = df[train_cells & in_months(df, train_split) & ok].reset_index(drop=True)
    ev = df[train_cells & in_months(df, eval_split)].reset_index(drop=True)
    ev["usable"] = ok[train_cells & in_months(df, eval_split)]
    return train, ev


def feature_table(df: pd.DataFrame) -> pd.DataFrame:
    """What predict() sees: the cell key plus the MODIS features (no VIIRS, no month or year)."""
    cols = KEY + features()
    bad = [c for c in cols if c.startswith(("snpp", "noaa20")) or c in ("month", "year")]
    if bad:
        raise ValueError(f"forbidden predict() columns: {bad}")
    return df[cols].copy()


@cache
def rectangles() -> pd.DataFrame:
    return pd.read_csv(ROOT / "config" / "rectangles.csv")


def rectangle_cells(
    cells: pd.DataFrame, role: str = "train", sets: tuple[str, ...] = ("demo",)
) -> pd.DataFrame:
    """(rect_id, rect region, lat_idx, lon_idx) for every rectangle of `role` in `sets` whose
    cells are all present in `cells`. The regional scope scores the "demo" rectangles; the
    global run (stage G) adds "gfed" (docs/decisions/0004). Rectangle edges lie on the 0.25 deg
    grid, so a rectangle is exactly the set of cells inside it (preregistration section 2)."""
    cell = settings()["grid"]["cell_deg"]
    have = set(
        zip(cells["lat_idx"].to_numpy().tolist(), cells["lon_idx"].to_numpy().tolist(), strict=True)
    )
    parts = []
    rects = rectangles()
    for r in rects[(rects["role"] == role) & rects["set"].isin(sets)].itertuples():
        i0, i1 = round((r.south + 90) / cell), round((r.north + 90) / cell)
        j0, j1 = round((r.west + 180) / cell), round((r.east + 180) / cell)
        ii, jj = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1), indexing="ij")
        pairs = list(zip(ii.ravel().tolist(), jj.ravel().tolist(), strict=True))
        if all(p in have for p in pairs):
            parts.append(
                pd.DataFrame(
                    {
                        "rect_id": r.rect_id,
                        "rect_region": r.region,
                        "lat_idx": ii.ravel(),
                        "lon_idx": jj.ravel(),
                    }
                )
            )
    if not parts:
        return pd.DataFrame(columns=["rect_id", "rect_region", "lat_idx", "lon_idx"])
    return pd.concat(parts, ignore_index=True)


def main() -> int:
    df = load_grid()
    cells = df.loc[df["role"] == "train", KEY + ["region"]].drop_duplicates()
    rc = rectangle_cells(cells)
    print(f"training cells: {len(cells)}; scored rectangles: {rc['rect_id'].nunique()}")
    for name in WINDOWS:
        train, ev = window(df, name)
        print(
            f"{name}: train {len(train)} usable cell-months "
            f"({train['month'].min()}..{train['month'].max()}); "
            f"eval {len(ev)} cell-months, {int(ev['usable'].sum())} usable "
            f"({ev['month'].min()}..{ev['month'].max()})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
