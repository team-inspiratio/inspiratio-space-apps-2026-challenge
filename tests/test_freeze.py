"""S11 freeze: year-block resamples are whole years and reproducible, and the interval scale
uses exactly the coverage formula of the frozen grader (final_test.coverage)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harmonization import final_test, freeze, prepare  # noqa: E402


def test_year_blocks_whole_years_and_reproducible():
    months = pd.Series([f"{y}-{m:02d}" for y in range(2014, 2022) for m in range(1, 13)] * 3)
    a = freeze.year_blocks(months, 5, seed=2026)
    b = freeze.year_blocks(months, 5, seed=2026)
    for (ya, ia), (yb, ib) in zip(a, b, strict=True):
        assert ya == yb and np.array_equal(ia, ib)
        assert len(ya) == 8  # as many years drawn as there are training years
        drawn = months.iloc[ia].str[:4]
        for y in set(ya):  # every drawn year comes whole, once per draw
            assert (drawn == y).sum() == ya.count(y) * (months.str[:4] == y).sum()


def test_interval_scale_matches_the_grader():
    rng = np.random.default_rng(1)
    n, k = 60, 20
    e = rng.uniform(50, 500, n)
    rs = e[:, None] * rng.uniform(0.95, 1.05, (n, k))  # narrow, like a stability interval
    v = e * rng.lognormal(0, 0.3, n)
    lo, hi = np.percentile(rs, 5, axis=1), np.percentile(rs, 95, axis=1)
    s, cov = freeze.interval_scale(v, e, lo, hi)
    assert cov >= 0.90 > freeze.covered(v, e, lo, hi, s - 0.01).mean()

    rs_cols = [f"rs_{i:03d}" for i in range(k)]
    table = pd.DataFrame(
        {
            "region": [f"r{i % 3}" for i in range(n)],
            "month": [
                f"2012-{i // 3 + 1:02d}" if i < 36 else f"2013-{i // 3 - 11:02d}" for i in range(n)
            ],
            prepare.LABEL: v,
            "est_final": e,
            "usable": True,
        }
    )
    table = pd.concat([table, pd.DataFrame(rs, columns=rs_cols)], axis=1)
    out = final_test.coverage(table, table[rs_cols], s)
    assert out["region_month_coverage_calibrated"] == cov
    assert out["region_month_coverage"] == freeze.covered(v, e, lo, hi, 1.0).mean()
