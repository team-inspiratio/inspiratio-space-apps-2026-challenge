"""pipeline.py (S15): every stage points at a module that exists, the stage order follows the
plan, and nothing in it seals the frozen submission or touches the locked test years."""

import importlib.util
import sys

from harmonization.config import ROOT

sys.path.insert(0, str(ROOT))
import pipeline  # noqa: E402


def test_stage_modules_exist():
    for _, what in pipeline.RAW + pipeline.COMMON:
        for args in what:
            assert importlib.util.find_spec(args[0]) is not None, args[0]


def test_stage_order():
    names = [n for n, _ in pipeline.stages(from_release=True)]
    assert names[0] == "fetch"
    order = ["explore", "judge-check", "baselines", "freeze", "series-v1", "validation", "anomaly"]
    assert [n for n in names if n in order] == order
    assert [n for n, _ in pipeline.stages(from_release=False)][:4] == [
        "download",
        "ingest",
        "clean",
        "grid",
    ]


def test_never_seals_or_runs_the_final_test():
    flat = [" ".join(a) for _, w in pipeline.RAW + pipeline.COMMON for a in w]
    assert not any("seal" in a for a in flat)
    assert not any("final_test" in a for a in flat)


def test_expected_hashes_present():
    for v in ("v0", "v1"):
        lines = (ROOT / "results" / "expected" / f"dataset-{v}.sha256").read_text().splitlines()
        names = {line.split()[1] for line in lines}
        assert f"dataset_{v}.parquet" in names
    assert (ROOT / "results" / "expected" / "dataset-v1-meta.json").exists()


def test_region_file_with_skipped_recount_matches_published(tmp_path):
    import gzip
    import hashlib
    import json

    ref = json.loads((ROOT / "results" / "expected" / "dataset-v1-meta.json").read_text("utf-8"))
    body = {"region": "x", "model": {**ref}, "months": [1.5, None, 3]}
    published = json.dumps(body, separators=(",", ":")).encode("utf-8")
    want = tmp_path / "want" / "x.json.gz"
    want.parent.mkdir()
    with gzip.GzipFile(want, "wb", mtime=0) as f:
        f.write(published)
    body["model"]["acceptance_recount"] = {"skipped": "no cleaned S-NPP points"}
    got = tmp_path / "x.json.gz"
    with gzip.GzipFile(got, "wb", mtime=0) as f:
        f.write(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    digest = hashlib.sha256(want.read_bytes()).hexdigest()
    assert pipeline.region_json_with_recount(got, "v1") == digest
    assert pipeline.region_json_with_recount(want, "v1") is None
