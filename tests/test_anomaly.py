"""Anomaly indicator: the reference implementation must reproduce every standard test case in
docs/anomaly-cases.json (hand-worked edge cases plus real dataset-v1 cases), and the hand-worked
cases in the file must be the ones in the code (so nobody edits expected values by hand)."""

import json
import math

import pytest

from harmonization import anomaly

DOC = json.loads(anomaly.CASES.read_text(encoding="utf-8"))


def same(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return a is b
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b


@pytest.mark.parametrize("case", DOC["cases"], ids=[c["id"] for c in DOC["cases"]])
def test_case(case):
    got = anomaly.anomaly(**case["input"])
    assert set(got) == set(case["expected"])
    for k, v in case["expected"].items():
        assert same(got[k], v), f"{case['id']}: {k} = {got[k]!r}, expected {v!r}"


def test_hand_cases_in_file_match_code():
    in_file = {c["id"]: c for c in DOC["cases"] if not c["id"].startswith("real_")}
    in_code = {c["id"]: c for c in anomaly.hand_cases()}
    assert in_file == json.loads(json.dumps(in_code))


def test_rules_block_matches_constants():
    r = DOC["rules"]
    assert r["min_reference_years"] == anomaly.MIN_REF
    assert r["tie_epsilon"] == anomaly.TIE_EPS
    assert r["min_median_for_ratio"] == anomaly.MIN_MEDIAN


def test_month_over():
    assert not anomaly.month_over("2026-10", "2026-10-31")
    assert anomaly.month_over("2026-10", "2026-11-01")
    assert anomaly.month_over("2025-12", "2026-01-01")
    assert not anomaly.month_over("2025-12", "2025-12-31")
