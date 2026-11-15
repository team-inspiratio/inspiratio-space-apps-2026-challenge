"""S07 check of the judge on the real grid: two dummy methods, each run twice.

uv run python -m harmonization.judge_check     # writes reports/judge-check.md

"always 0" must score far worse than "MODIS count as is", and two runs of the same method must
give bit-identical results (SHA256 of the full result JSON).
"""

from __future__ import annotations

import hashlib
import json
import sys

import numpy as np

from harmonization import evaluate, harmonize, prepare
from harmonization.config import ROOT


def fit_zero(train):
    return lambda x: np.zeros(len(x))


DUMMIES = {"always 0": fit_zero, "MODIS count as is (= M0)": harmonize.fit_m0}
SHOWN = ["male", "male_all", "n_primary", "excluded_share", "zero_ge1", "low_mae"]


def fmt(x) -> str:
    return "" if x is None else (f"{x:.4f}" if isinstance(x, float) else str(x))


def main() -> int:
    df = prepare.load_grid()
    lines = [
        "# 判卷机器检查（S07）",
        "",
        "由 `uv run python -m harmonization.judge_check` 生成。两个假方法在两个验证窗口上各跑两次；"
        "“永远预测 0”应明显差于“直接用 MODIS 数”，同一方法两次结果的 SHA256 必须相同。",
        "",
        "| 方法 | 窗口 | " + " | ".join(SHOWN) + " |",
        "|---|---|" + "---:|" * len(SHOWN),
    ]
    hashes, ok = [], True
    for name, fit in DUMMIES.items():
        runs = [evaluate.evaluate(fit, df) for _ in range(2)]
        digest = [hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest() for r in runs]
        ok &= digest[0] == digest[1]
        hashes.append(f"- {name}：`{digest[0][:16]}…` / `{digest[1][:16]}…`")
        for w in prepare.WINDOWS:
            row = [fmt(runs[0][w][k]) for k in SHOWN]
            lines.append(f"| {name} | {w} | " + " | ".join(row) + " |")
        lines.append(f"| {name} | 两窗口合并 MALE | {fmt(runs[0]['combined_male'])} |")
    lines += ["", "两次运行的 SHA256：", "", *hashes, ""]
    lines.append(f"结论：可重复性 {'通过' if ok else '失败'}。")
    (ROOT / "reports" / "judge-check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
