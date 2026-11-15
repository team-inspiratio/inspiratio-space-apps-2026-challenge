"""One command to rebuild every result of this repository and check it (plan sections 7-8 and 10,
task card 5-report S15).

  uv run python -X utf8 pipeline.py all --from-release   # processed Release data-v0, no FIRMS key
  uv run python -X utf8 pipeline.py all                  # from the raw FIRMS/GFED files (~50 GB)
  uv run python -X utf8 pipeline.py check                # only compare the outputs
  uv run python -X utf8 pipeline.py list                 # stages and which are done

Needs `uv sync` and INSPIRATIO_DATA_DIR (in .env or the environment; an empty folder is fine).
`--from-release` also needs the GitHub CLI logged in (`gh auth login --web`); `all` without it
needs a FIRMS MAP_KEY in .env. Every stage is a module of harmonization/ run as it is; a stage
leaves <data>/pipeline_<stage>.done and is skipped next time (`--force` reruns everything).

Stages, in order:
  raw only      download (FIRMS yearly archive and API, missing-data list), ingest, clean, grid
  release only  fetch: the gridded tables of Release data-v0, checked against its SHA256SUMS
  both          gfed (GFED4.1s, public), explore (S06), judge-check (S07), baselines (S08),
                series-v0 (S09), freeze (S11 resamples of the frozen E028 procedure, three
                windows), series-v1 (S12 dataset and S14 delivery files), validation (S13),
                anomaly (S14 test cases), then check
Not rerun: the S10 experiment loop (a search; its winner E028 is frozen in harmonize.py, and the
freeze stage reruns it on both validation windows), the S10 review, the sealing of the final-test
submission (frozen) and the final test itself (it ran once on GitHub; its scores are in
results/final-test/).

check compares, without changing anything:
  - the tracked score files the stages rewrite (reports/*.json, *.md, docs/anomaly-cases.json)
    with the committed versions (line endings ignored);
  - the frozen procedure on both validation windows with results/freeze.json and with E028 in
    reports/scores-s10.json (scores, parameters, rounds), and the calibration factor;
  - the rebuilt test-set estimates with the sealed results/submission.parquet (bit for bit);
  - the dataset files v0 and v1 with results/expected/dataset-v*.sha256. When the cleaned S-NPP
    points are not in the data folder (Release start) the S12 acceptance recount is skipped:
    meta.json is then compared without it, and the region files (which embed meta.json) bit for
    bit after the published recount is put back.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = [sys.executable, "-X", "utf8", "-m"]
REPO = "team-inspiratio/inspiratio-space-apps-2026"
RELEASE_FILES = {  # data-v0 asset -> place in the data folder
    "grid_regions.parquet": "processed/grid/regions.parquet",
    "grid_month_status.parquet": "processed/grid/month_status.parquet",
    "grid_counts.parquet": "processed/grid/counts.parquet",
}
RAW = [
    ("download", [["harmonization.download", w] for w in ("missing", "annual", "api")]),
    ("ingest", [["harmonization.ingest"]]),
    ("clean", [["harmonization.clean"]]),
    ("grid", [["harmonization.grid"]]),
]
COMMON = [
    ("gfed", [["harmonization.download", "gfed"]]),
    ("explore", [["harmonization.explore"]]),
    ("judge-check", [["harmonization.judge_check"]]),
    ("baselines", [["harmonization.baselines"]]),
    ("series-v0", [["harmonization.series"]]),
    ("freeze", [["harmonization.freeze", "resample", w] for w in ("main", "aux", "test")]),
    ("series-v1", [["harmonization.series_v1", "build"]]),
    ("validation", [["harmonization.validation", "all"]]),
    ("anomaly", [["harmonization.anomaly", "cases"]]),
]
TRACKED = [  # files the stages rewrite; they must come out as committed
    "reports/a5-stats.json",
    "reports/judge-check.md",
    "reports/scores-v1.json",
    "reports/scores-v1.md",
    "reports/validation.json",
    "docs/anomaly-cases.json",
]
DOC_COPIES = {"data-interface.md", "data-card.md", "anomaly-cases.json"}  # compared via git


def data_dir() -> Path:
    from harmonization.config import data_dir as dd

    return dd()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(args: list[str]) -> None:
    print(f"\n$ python -m {' '.join(args)}", flush=True)
    subprocess.run([*PY, *args], cwd=ROOT, check=True)


def fetch_release() -> None:
    """Gridded tables of Release data-v0 (S05 output), checked against its SHA256SUMS."""
    tmp = data_dir() / "release" / "data-v0"
    tmp.mkdir(parents=True, exist_ok=True)
    pats = [x for f in [*RELEASE_FILES, "SHA256SUMS.txt"] for x in ("-p", f)]
    cmd = ["gh", "release", "download", "data-v0", "--repo", REPO, "-D", str(tmp), "--clobber"]
    subprocess.run(cmd + pats, check=True)
    want = {}
    for line in (tmp / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split()
        want[name.lstrip("*")] = digest
    for name, dest in RELEASE_FILES.items():
        got = sha256(tmp / name)
        if got != want[name]:
            raise SystemExit(f"{name}: SHA256 {got} does not match the release ({want[name]})")
        target = data_dir() / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp / name, target)
        print(f"{name}: SHA256 ok -> {dest}", flush=True)


def stages(from_release: bool) -> list[tuple[str, object]]:
    first = [("fetch", fetch_release)] if from_release else RAW
    return [*first, *COMMON]


def marker(name: str) -> Path:
    return data_dir() / f"pipeline_{name}.done"


def run_all(from_release: bool, force: bool) -> None:
    for name, what in stages(from_release):
        m = marker(name)
        if m.exists() and not force:
            print(f"[skip] {name} (done; --force to rerun)", flush=True)
            continue
        t0 = time.time()
        print(f"\n=== {name} ===", flush=True)
        if callable(what):
            what()
        else:
            for args in what:
                run(args)
        m.write_text(f"ok {time.time() - t0:.0f} s\n", encoding="utf-8")
        print(f"=== {name}: done in {time.time() - t0:.0f} s ===", flush=True)


# --- check ---------------------------------------------------------------------------------
def committed(path: str) -> str | None:
    r = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=False)
    return r.stdout.decode("utf-8").replace("\r\n", "\n") if r.returncode == 0 else None


def check() -> bool:
    import numpy as np
    import pandas as pd

    from harmonization import freeze, harmonize, prepare

    results: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))

    for path in TRACKED:
        want = committed(path)
        p = ROOT / path
        got = p.read_text(encoding="utf-8").replace("\r\n", "\n") if p.exists() else None
        record(f"tracked file {path}", want is not None and got == want, "" if got else "missing")

    fz = json.loads((ROOT / "results" / "freeze.json").read_text(encoding="utf-8"))
    s10 = json.loads((ROOT / "reports" / "scores-s10.json").read_text(encoding="utf-8"))
    e028 = next(t for t in s10["top3"] if t["exp_id"] == "E028")
    wd = data_dir() / "s11"
    for w in ("main", "aux"):
        meta = json.loads((wd / f"{w}.json").read_text(encoding="utf-8"))
        ref = fz["validation_windows"][w]
        record(
            f"{w}: frozen procedure = freeze.json (score, config)",
            meta["score"] == ref["score"] and meta["config"] == ref["config"],
        )
        record(
            f"{w}: MALE = E028 in scores-s10.json",
            meta["score"]["male"] == e028["windows"][w]["male"],
            f"{meta['score']['male']:.6f}",
        )
    test = json.loads((wd / "test.json").read_text(encoding="utf-8"))
    record(
        "test refit: config and rounds = freeze.json",
        test["config"] == fz["config"] and test["draws"] == fz["resamples"]["years_drawn"],
    )
    cal = freeze.calibration()
    record(
        "calibration factor = freeze.json",
        cal == fz["calibration"],
        f"interval_scale {cal['pooled']['interval_scale']}",
    )

    sub = pd.read_parquet(freeze.SUBMISSION)
    rows = pd.read_parquet(wd / "test_rows.parquet")
    rs = [c for c in sub.columns if c.startswith("rs_")]
    same_rows = rows[prepare.KEY + ["month"]].equals(
        sub[prepare.KEY + ["month"]].astype(rows[prepare.KEY + ["month"]].dtypes.to_dict())
    )
    record("test rows = submission rows", same_rows)
    record(
        "est_final = sealed submission (bit for bit)",
        np.array_equal(rows["est_final"].to_numpy(), sub["est_final"].to_numpy()),
    )
    record(
        "100 resamples = sealed submission (bit for bit)",
        np.array_equal(rows[rs].to_numpy(), sub[rs].to_numpy()),
    )
    df = prepare.load_grid()
    train = freeze.training_table(df, "test")
    feats = prepare.feature_table(freeze.eval_rows(df, "test"))
    for col, fit in (
        ("est_m1s", lambda t: harmonize.fit_m1s(t, 20.0)),
        ("est_qm", harmonize.fit_qm),
        ("est_m0", harmonize.fit_m0),
    ):
        record(
            f"{col} = sealed submission",
            np.array_equal(np.asarray(fit(train)(feats), float), sub[col].to_numpy(float)),
        )

    for v in ("v0", "v1"):
        root = data_dir() / "processed" / v
        want = {}
        for line in (
            (ROOT / "results" / "expected" / f"dataset-{v}.sha256")
            .read_text(encoding="utf-8")
            .splitlines()
        ):
            digest, name = line.split()
            want[name] = digest
        files = {p.name: p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"}
        for name, digest in sorted(want.items()):
            if name in DOC_COPIES:
                continue
            p = files.get(name)
            if p is None:
                record(f"dataset {v}: {name}", False, "missing")
                continue
            ok = sha256(p) == digest
            detail = ""
            if not ok and name == "meta.json":
                meta = json.loads(p.read_text(encoding="utf-8"))
                if "skipped" in meta.get("acceptance_recount", {}):
                    meta.pop("acceptance_recount")
                    ref = json.loads(committed_release_meta(v) or "{}")
                    ref.pop("acceptance_recount", None)
                    ok = meta == ref
                    detail = "equal except the skipped acceptance recount"
            if not ok and name.endswith(".json.gz"):
                ok = region_json_with_recount(p, v) == digest
                detail = "bit for bit with the published acceptance recount put back" if ok else ""
            record(f"dataset {v}: {name}", ok, detail)

    width = max(len(n) for n, _, _ in results)
    print("\nREPRODUCTION CHECK")
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    n_fail = sum(not ok for _, ok, _ in results)
    print(f"{len(results) - n_fail} passed, {n_fail} failed")
    out = data_dir() / "pipeline_check.json"
    out.write_text(
        json.dumps([{"check": n, "ok": o, "detail": d} for n, o, d in results], indent=1) + "\n",
        encoding="utf-8",
    )
    return n_fail == 0


def committed_release_meta(v: str) -> str | None:
    """meta.json as published: kept next to the expected hashes for this comparison."""
    p = ROOT / "results" / "expected" / f"dataset-{v}-meta.json"
    return p.read_text(encoding="utf-8") if p.exists() else None


def region_json_with_recount(path: Path, v: str) -> str | None:
    """SHA256 of a web-page region file after its skipped acceptance recount is replaced by the
    published one (series_v1 embeds meta.json under "model"), encoded as series_v1 writes it.
    None when the file did not skip the recount."""
    import gzip

    data = json.loads(gzip.decompress(path.read_bytes()))
    model = data.get("model", {})
    if "skipped" not in model.get("acceptance_recount", {}):
        return None
    ref = json.loads(committed_release_meta(v) or "{}")
    if "acceptance_recount" not in ref:
        return None
    model["acceptance_recount"] = ref["acceptance_recount"]
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, filename=path.name) as f:
        f.write(raw)
    return hashlib.sha256(buf.getvalue()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("what", choices=["all", "check", "list"])
    p.add_argument("--from-release", action="store_true", help="start from Release data-v0")
    p.add_argument("--force", action="store_true", help="rerun stages that are already done")
    a = p.parse_args()
    if not os.environ.get("INSPIRATIO_DATA_DIR"):
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    if a.what == "list":
        for name, _ in stages(a.from_release):
            print(f"{'done' if marker(name).exists() else '    '}  {name}")
        return 0
    if a.what == "all":
        t0 = time.time()
        run_all(a.from_release, a.force)
        print(f"\nall stages done in {(time.time() - t0) / 60:.0f} min", flush=True)
    return 0 if check() else 1


if __name__ == "__main__":
    sys.exit(main())
