"""S12 dataset v1: Terra-only rows get Aqua inputs made from Terra, and nothing else changes."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harmonization import harmonize, series_v1  # noqa: E402
from tests.test_series import tiny_grid  # noqa: E402


def test_terra_inputs_scale_counts_and_copy_the_rest():
    df = tiny_grid()
    df["region"] = df["region"].astype(str)
    bridge = series_v1.bridge_ratios(df)
    x = df[df["month"] == "2001-03"].reset_index(drop=True)
    t = series_v1.terra_inputs(x, bridge)
    k = harmonize.apply_ratios(bridge, x.assign(_one=1.0), a_col="_one")
    assert np.allclose(t["aqua_count"], k * x["terra_count"])
    assert np.allclose(t["aqua_nbr_count"], k * x["terra_nbr_count"])
    for f in series_v1.COPY:
        assert (t[f"aqua_{f}"] == x[f"terra_{f}"]).all()
    terra_cols = [c for c in x.columns if c.startswith("terra_")]
    pd.testing.assert_frame_equal(t[terra_cols], x[terra_cols])
