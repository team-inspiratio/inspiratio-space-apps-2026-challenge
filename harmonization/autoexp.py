"""S10 experiment loop runner (plan section 5, harmonization/program.md).

  uv run python -X utf8 -m harmonization.autoexp run --hyp "one-sentence hypothesis" [--low]
  uv run python -X utf8 -m harmonization.autoexp queue FILE.json [--low]
  uv run python -X utf8 -m harmonization.autoexp restore    # harmonize.py <- best kept version
  uv run python -X utf8 -m harmonization.autoexp status

`run` scores the current harmonization/harmonize.py (method fit_lgb) with the frozen judge
(harmonization.evaluate) on the two validation windows, checks the preregistered guardrails
against M1s (lambda = 20), compares with the best kept experiment by the block bootstrap, appends
one row to harmonization/experiments.csv and records the variant on the experiment branch
(worktree EXP_WORKTREE). `queue` runs a list of {"hyp": ..., "set": {LGB key: value}} one after
another: each sets those entries of the LGB dict in harmonize.py, runs, and puts the previous
source back unless the experiment was kept (hill climbing). This file never changes the judge,
the data or the splits; it only calls them (docs/decisions/0006).

Keep rule (preregistration section 4 and plan section 3 item 7):
  eligible  every guardrail of preregistration section 4 items 3-4 holds against M1s
  kept      eligible and the improvement over the current best (M1s until the first keep)
            exceeds 1 standard error of the block bootstrap difference
Budget: at most 150 experiments or 8 hours from the first one; stop after 30 in a row
without a keep.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from harmonization import evaluate, prepare
from harmonization.config import ROOT, data_dir

SOURCE = ROOT / "harmonization" / "harmonize.py"
CSV = ROOT / "harmonization" / "experiments.csv"
EXP_WORKTREE = Path(os.environ.get("INSPIRATIO_EXP_WORKTREE", ROOT.parent / "inspiratio-exp"))
MAX_EXPERIMENTS, MAX_HOURS, PATIENCE = 150, 8.0, 30
COLUMNS = [
    "exp_id",
    "started_utc",
    "hypothesis",
    "combined_male",
    "male_main",
    "male_aux",
    "diff_vs_m1s",
    "se_vs_m1s",
    "ci95_vs_m1s",
    "zero_ge1_main",
    "zero_ge1_aux",
    "zero_ge5_main",
    "zero_ge5_aux",
    "low_mae_main",
    "low_mae_aux",
    "total_bias_main",
    "total_bias_aux",
    "eligible",
    "guardrail_failures",
    "diff_vs_best",
    "se_vs_best",
    "kept",
    "best_after",
    "runtime_s",
    "source_sha256",
    "config",
]


def exp_dir() -> Path:
    d = data_dir() / "experiments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def strip(res: dict) -> dict:
    """Evaluation results without numpy types (units kept for the bootstrap)."""
    return json.loads(json.dumps(res, default=float))


def m1s_reference(df) -> dict:
    path = exp_dir() / "m1s.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    from harmonization import harmonize

    res = strip(evaluate.evaluate(lambda t: harmonize.fit_m1s(t, 20.0), df))
    path.write_text(json.dumps(res), encoding="utf-8")
    return res


def guardrails(res: dict, ref: dict) -> list[str]:
    """Preregistration section 4 items 3-4, each window separately."""
    fails = []
    for w in prepare.WINDOWS:
        a, b = res[w], ref[w]
        if a["male"] > b["male"]:
            fails.append(f"{w}:male>m1s")
        for region, m in a["male_by_region"].items():
            if m > 1.05 * b["male_by_region"][region]:
                fails.append(f"{w}:{region}>1.05xm1s")
        if a["zero_ge1"] > b["zero_ge1"] + 0.05:
            fails.append(f"{w}:zero_ge1+{a['zero_ge1'] - b['zero_ge1']:.3f}")
        if a["zero_ge5"] > b["zero_ge5"] + 0.02:
            fails.append(f"{w}:zero_ge5+{a['zero_ge5'] - b['zero_ge5']:.3f}")
        if a["low_mae"] > 1.10 * b["low_mae"]:
            fails.append(f"{w}:low_mae x{a['low_mae'] / b['low_mae']:.2f}")
    return fails


def rows() -> list[dict]:
    if not CSV.exists():
        return []
    with CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def best_state() -> dict:
    path = exp_dir() / "best.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"exp_id": "M1s", "results": None}


def budget_left(history: list[dict]) -> str | None:
    """Reason to stop, or None while the budget allows another experiment."""
    if len(history) >= MAX_EXPERIMENTS:
        return f"{MAX_EXPERIMENTS} experiments reached"
    if history:
        first = datetime.fromisoformat(history[0]["started_utc"])
        if (datetime.now(UTC) - first).total_seconds() > MAX_HOURS * 3600:
            return f"{MAX_HOURS:g} hours reached"
    streak = 0
    for r in reversed(history):
        if r["kept"] == "yes":
            break
        streak += 1
    if streak >= PATIENCE:
        return f"{PATIENCE} experiments in a row without a keep"
    return None


def lower_priority() -> None:
    """'上课了' mode: below-normal priority (thread count stays fixed for reproducibility)."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    else:
        os.nice(10)


def git_exp(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(EXP_WORKTREE), *args], check=True, capture_output=True, text=True
    ).stdout


def record_variant(exp_id: str, hyp: str, kept: bool, src: str) -> None:
    """Commit the variant (and, if kept, the new best harmonize.py) to the experiment branch."""
    if not EXP_WORKTREE.exists():
        print(f"note: experiment worktree {EXP_WORKTREE} missing; variant not committed")
        return
    var = EXP_WORKTREE / "harmonization" / "variants" / f"{exp_id}.py"
    var.parent.mkdir(parents=True, exist_ok=True)
    var.write_text(src, encoding="utf-8", newline="\n")
    shutil.copyfile(CSV, EXP_WORKTREE / "harmonization" / "experiments.csv")
    paths = [str(var.relative_to(EXP_WORKTREE)), "harmonization/experiments.csv"]
    if kept:
        (EXP_WORKTREE / "harmonization" / "harmonize.py").write_text(
            src, encoding="utf-8", newline="\n"
        )
        paths.append("harmonization/harmonize.py")
    git_exp("add", *paths)
    trailer = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    msg = f"{exp_id} {'keep' if kept else 'discard'}: {hyp}\n\n{trailer}"
    git_exp("commit", "-q", "-m", msg)


def ruff_format(text: str) -> str:
    """Format a harmonize.py source with the project's ruff settings (pre-commit runs ruff)."""
    out = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--stdin-filename", str(SOURCE), "-"],
        input=text.encode("utf-8"),
        check=True,
        capture_output=True,
        cwd=ROOT,
    )
    return out.stdout.decode("utf-8").replace("\r\n", "\n")


def set_lgb(source: str, values: dict) -> str:
    """Set entries of the LGB dict in the harmonize.py source (Python literals)."""
    block = re.search(r"^LGB: dict = \{\n(.*?)^\}", source, re.S | re.M)
    if block is None:
        raise SystemExit("LGB dict not found in harmonize.py")
    body = block.group(1)
    for key, value in values.items():
        lit = repr(tuple(value) if isinstance(value, list) else value)
        body, n = re.subn(
            rf'^(    "{key}": )(.*?)(,[ \t]*(#.*)?)$',
            lambda m, lit=lit: m.group(1) + lit + m.group(3),
            body,
            flags=re.M,
        )
        if n != 1:
            raise SystemExit(f"LGB key {key!r} not found")
    return source[: block.start(1)] + body + source[block.end(1) :]


def score_source(src: str) -> tuple[dict, list, float]:
    """Score one harmonize.py source (fit_lgb) with the frozen judge; runs in a worker."""
    digest = hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]
    path = exp_dir() / "pending" / f"h_{digest}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location(f"harmonize_{digest}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    df = prepare.load_grid()
    configs: list[dict] = []

    def fit(train):
        pred = mod.fit_lgb(train)
        configs.append(pred.config)
        return pred

    t0 = time.time()
    res = strip(evaluate.evaluate(fit, df))
    return res, configs, time.time() - t0


def queue(path: Path, jobs: int = 1, until: str | None = None) -> int:
    """Run the list in batches of `jobs` parallel experiments; book them in list order."""
    from concurrent.futures import ProcessPoolExecutor

    items = json.loads(path.read_text(encoding="utf-8"))
    deadline = datetime.fromisoformat(until) if until else None
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for i in range(0, len(items), jobs):
            if deadline and datetime.now(UTC) >= deadline:
                print(f"deadline {until} reached; no new experiments", flush=True)
                return 3
            stop = budget_left(rows())
            if stop:
                print(f"budget exhausted: {stop}", flush=True)
                return 2
            base = SOURCE.read_text(encoding="utf-8")
            batch = items[i : i + jobs]
            srcs = [ruff_format(set_lgb(base, it.get("set", {}))) for it in batch]
            started = datetime.now(UTC).replace(microsecond=0)
            futures = [pool.submit(score_source, s) for s in srcs]
            for it, src, fut in zip(batch, srcs, futures, strict=True):
                res, configs, runtime = fut.result()
                if book(it["hyp"], src, res, configs, runtime, started):
                    SOURCE.write_text(src, encoding="utf-8", newline="\n")
    return 0


def run(hyp: str) -> int:
    stop = budget_left(rows())
    if stop:
        print(f"budget exhausted: {stop}")
        return 2
    started = datetime.now(UTC).replace(microsecond=0)
    src = ruff_format(SOURCE.read_text(encoding="utf-8"))
    SOURCE.write_text(src, encoding="utf-8", newline="\n")
    res, configs, runtime = score_source(src)
    book(hyp, src, res, configs, runtime, started)
    return 0


def book(hyp: str, src: str, res: dict, configs: list, runtime: float, started) -> bool:
    """Guardrails, comparison with the best, CSV row, experiment branch. Returns kept."""
    history = rows()
    exp_id = f"E{len(history):03d}"
    ref = m1s_reference(prepare.load_grid())
    fails = guardrails(res, ref)
    vs_m1s = evaluate.bootstrap_diff(ref, res)
    best = best_state()
    if best["results"] is None:
        vs_best = vs_m1s
    else:
        vs_best = evaluate.bootstrap_diff(best["results"], res)
    improvement = -vs_best["diff"]
    kept = not fails and improvement > vs_best["se"]
    (exp_dir() / f"{exp_id}.json").write_text(
        json.dumps({"results": res, "configs": configs}, default=str), encoding="utf-8"
    )
    if kept:
        (exp_dir() / "best.json").write_text(
            json.dumps({"exp_id": exp_id, "results": res}), encoding="utf-8"
        )
        (exp_dir() / "best_harmonize.py").write_text(src, encoding="utf-8", newline="\n")
    row = {
        "exp_id": exp_id,
        "started_utc": started.isoformat(),
        "hypothesis": hyp,
        "combined_male": f"{res['combined_male']:.4f}",
        "male_main": f"{res['main']['male']:.4f}",
        "male_aux": f"{res['aux']['male']:.4f}",
        "diff_vs_m1s": f"{vs_m1s['diff']:.4f}",
        "se_vs_m1s": f"{vs_m1s['se']:.4f}",
        "ci95_vs_m1s": "[{:.4f}, {:.4f}]".format(*vs_m1s["ci95"]),
        **{
            f"{k}_{w}": f"{res[w][m]:.4f}"
            for w in prepare.WINDOWS
            for k, m in (
                ("zero_ge1", "zero_ge1"),
                ("zero_ge5", "zero_ge5"),
                ("low_mae", "low_mae"),
                ("total_bias", "total_bias_mean_abs"),
            )
        },
        "eligible": "no" if fails else "yes",
        "guardrail_failures": ";".join(fails),
        "diff_vs_best": f"{vs_best['diff']:.4f}",
        "se_vs_best": f"{vs_best['se']:.4f}",
        "kept": "yes" if kept else "no",
        "best_after": exp_id if kept else best["exp_id"],
        "runtime_s": f"{runtime:.0f}",
        "source_sha256": hashlib.sha256(src.encode("utf-8")).hexdigest(),
        "config": json.dumps(
            [{k: v for k, v in c.items() if k not in ("monotone",)} for c in configs],
            default=str,
            sort_keys=True,
        ),
    }
    new = not CSV.exists()
    with CSV.open("a", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(row)
    record_variant(exp_id, hyp, kept, src)
    print(
        f"{exp_id} combined {row['combined_male']} (main {row['male_main']}, aux "
        f"{row['male_aux']}); vs M1s {row['diff_vs_m1s']} ± {row['se_vs_m1s']}; vs best "
        f"{row['diff_vs_best']} ± {row['se_vs_best']}; eligible {row['eligible']} "
        f"{row['guardrail_failures']}; kept {row['kept']}; {row['runtime_s']} s",
        flush=True,
    )
    return kept


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--hyp", required=True, help="one-sentence hypothesis of this change")
    r.add_argument("--low", action="store_true", help="below-normal CPU priority (上课了)")
    q = sub.add_parser("queue")
    q.add_argument("file", type=Path, help='JSON list of {"hyp": ..., "set": {...}}')
    q.add_argument("--low", action="store_true", help="below-normal CPU priority (上课了)")
    q.add_argument("--jobs", type=int, default=1, help="experiments run in parallel")
    q.add_argument("--until", help="UTC deadline (ISO 8601): no new experiments after it")
    sub.add_parser("restore")
    sub.add_parser("status")
    args = p.parse_args()
    if args.cmd in ("run", "queue") and args.low:
        lower_priority()
    if args.cmd == "run":
        return run(args.hyp)
    if args.cmd == "queue":
        return queue(args.file, args.jobs, args.until)
    if args.cmd == "restore":
        shutil.copyfile(exp_dir() / "best_harmonize.py", SOURCE)
        print(f"harmonize.py restored to {best_state()['exp_id']}")
        return 0
    history = rows()
    print(
        f"{len(history)} experiments; best {best_state()['exp_id']}; "
        f"stop: {budget_left(history) or 'no'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
