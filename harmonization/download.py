"""S02 downloads: FIRMS yearly packages, FIRMS API for 2026, missing-data list, GFED4.1s.

uv run python -m harmonization.download annual     # yearly packages (resumable)
uv run python -m harmonization.download gfed       # GFED4.1s burned area
uv run python -m harmonization.download missing    # official missing-data list
uv run python -m harmonization.download api        # 2026 SP + NRT through the API (rate-limited)

Every request first calls assert_download_allowed() (AGENTS.md red line 1); the locked S-NPP
test years are never requested. API VIIRS rows inside holdout regions are dropped before anything is
written. The MAP_KEY is only ever placed in the request URL and is redacted from all messages.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import re
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

from harmonization.config import (
    ROOT,
    assert_download_allowed,
    data_dir,
    in_holdout,
    map_key,
    redact,
    settings,
)

FIRMS = "https://firms.modaps.eosdis.nasa.gov"
YEARLY = f"{FIRMS}/data/country/zips"
YEARLY_LIST = f"{FIRMS}/data/country/yearly_summary_files.txt"
GFED = "https://www.geo.vu.nl/~gwerf/GFED/GFED4"
MANIFEST = ROOT / "docs" / "data-manifest.csv"
MANIFEST_FIELDS = ["file", "source", "start", "end", "bytes", "sha256", "rows", "retrieved_utc"]

# FIRMS file prefix -> (source name for the guardrail, first year, last year)
YEARLY_SOURCES = {
    "modis": ("MODIS_SP", 2000, 2025),
    "viirs-snpp": ("VIIRS_SNPP_SP", 2014, 2025),  # 2012-2013 are the locked test set
    "viirs-jpss1": ("VIIRS_NOAA20_SP", 2018, 2025),
}
GFED_YEARS = range(2000, 2024)  # GFED4.1s: final to 2016, beta 2017-2023
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "inspiratio-harmonization (NASA Space Apps 2026)"


def log(msg: str) -> None:
    print(redact(msg), flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()


def read_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        return {row["file"]: row for row in csv.DictReader(f)}


def write_manifest(rows: dict[str, dict]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows[k] for k in sorted(rows))


def record(rel: str, source: str, start: dt.date, end: dt.date, path: Path, rows: int) -> None:
    manifest = read_manifest()
    manifest[rel] = {
        "file": rel,
        "source": source,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "rows": rows,
        "retrieved_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_manifest(manifest)


def present(rel: str, manifest: dict[str, dict]) -> bool:
    """Already in THIS data folder with the size the manifest records. The manifest is committed
    (it describes the original run), so being listed alone does not mean the file is here."""
    path = data_dir() / rel
    row = manifest.get(rel)
    return row is not None and path.exists() and path.stat().st_size == int(row["bytes"])


def imported_here(name: str) -> bool:
    """A yearly zip already imported into this data folder (VIIRS zips are deleted after S03)."""
    stem = name.removesuffix(".zip")
    return any((data_dir() / "interim" / "points").glob(f"*/*/{stem}.parquet"))


def keep_or_check(rel: str, source: str, start, end, path: Path, rows: int, manifest) -> None:
    """New file: record it. File the manifest already lists: it must have the recorded SHA256
    (raw data are hash-locked, plan section 10); the committed row is left as it is."""
    row = manifest.get(rel)
    if row is None:
        record(rel, source, start, end, path, rows)
        return
    got = sha256(path)
    if got != row["sha256"]:
        raise SystemExit(f"{rel}: SHA256 {got} differs from docs/data-manifest.csv")


def fetch(url: str, dest: Path, source: str, start: dt.date, end: dt.date, size: int = 0) -> Path:
    """Resumable streaming download into dest (a .part file is renamed on completion)."""
    assert_download_allowed(source, start, end)
    if dest.exists() and (not size or dest.stat().st_size == size):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(8):
        have = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with SESSION.get(url, headers=headers, stream=True, timeout=120) as r:
                if r.status_code == 416:  # already complete
                    break
                r.raise_for_status()
                mode = "ab" if have and r.status_code == 206 else "wb"
                with part.open(mode) as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            if not size or part.stat().st_size >= size:
                break
        except requests.RequestException as e:
            log(f"  retry {attempt + 1} for {dest.name}: {type(e).__name__}")
            time.sleep(min(60, 5 * 2**attempt))
    else:
        raise RuntimeError(f"giving up on {dest.name}")
    if size and part.stat().st_size != size:
        raise RuntimeError(f"{dest.name}: got {part.stat().st_size} bytes, expected {size}")
    part.replace(dest)
    return dest


def count_zip_rows(path: Path) -> int:
    """Data rows across all CSV members (header lines excluded)."""
    rows = 0
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if not info.filename.lower().endswith(".csv"):
                continue
            with z.open(info) as f:
                lines = sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 24), b""))
                rows += max(0, lines - 1)
    return rows


def yearly_sizes() -> dict[str, int]:
    text = SESSION.get(YEARLY_LIST, timeout=60).text
    sizes = {}
    for line in text.splitlines():
        parts = line.strip().split(",")
        if len(parts) >= 2 and parts[0].endswith(".zip") and parts[1].isdigit():
            sizes[parts[0]] = int(parts[1])
    return sizes


def annual(only: str | None = None) -> None:
    sizes = yearly_sizes()
    out = data_dir() / "raw" / "firms_yearly"
    manifest = read_manifest()
    jobs = [
        (prefix, source, year)
        for prefix, (source, first, last) in YEARLY_SOURCES.items()
        if only in (None, prefix)
        for year in range(first, last + 1)
    ]
    for prefix, source, year in jobs:
        name = f"{prefix}_{year}_all_countries.zip"
        rel = f"raw/firms_yearly/{name}"
        if present(rel, manifest) or imported_here(name):
            continue
        if name not in sizes:
            log(f"skip {name}: not in FIRMS listing")
            continue
        start, end = dt.date(year, 1, 1), dt.date(year, 12, 31)
        t0 = time.time()
        path = fetch(f"{YEARLY}/{name}", out / name, source, start, end, sizes[name])
        rows = count_zip_rows(path)
        keep_or_check(rel, source, start, end, path, rows, manifest)
        mb = path.stat().st_size / 1e6
        log(f"ok {name}: {mb:.0f} MB, {rows} rows, {time.time() - t0:.0f} s")


def gfed() -> None:
    out = data_dir() / "raw" / "gfed"
    manifest = read_manifest()
    for year in GFED_YEARS:
        name = f"GFED4.1s_{year}{'_beta' if year >= 2017 else ''}.hdf5"
        rel = f"raw/gfed/{name}"
        if present(rel, manifest):
            continue
        start, end = dt.date(year, 1, 1), dt.date(year, 12, 31)
        path = fetch(f"{GFED}/{name}", out / name, "GFED4.1s", start, end)
        keep_or_check(rel, "GFED4.1s", start, end, path, 0, manifest)
        log(f"ok {name}: {path.stat().st_size / 1e6:.0f} MB")


def missing() -> None:
    """Official list of dates with missing or degraded FIRMS data; small, kept in git too."""
    today = dt.date.today()
    assert_download_allowed("FIRMS_MISSING_DATA", dt.date(2000, 11, 1), today)
    r = SESSION.get(f"{FIRMS}/api/missing_data/?action=fetch_data", timeout=120)
    r.raise_for_status()
    # The endpoint returns {"success": true, "html": "<tr><td>date</td><td>sensor</td>...</tr>"}
    # with two (date, sensor) pairs per table row.
    pairs = re.findall(
        r"<td>\s*(\d{4}-\d{2}-\d{2})\s*</td>\s*<td>\s*([^<]+?)\s*</td>", r.json()["html"]
    )
    df = pd.DataFrame(pairs, columns=["date", "sensor"]).drop_duplicates()
    df = df.sort_values(["sensor", "date"]).reset_index(drop=True)
    dest = ROOT / "docs" / "firms-missing-data.csv"
    df.to_csv(dest, index=False, lineterminator="\n")
    record(
        "docs/firms-missing-data.csv",
        "FIRMS_MISSING_DATA",
        dt.date(2000, 11, 1),
        today,
        dest,
        len(df),
    )
    log(f"ok missing-data list: {len(df)} rows, columns {list(df.columns)}")


# --- API (2026) -------------------------------------------------------------------------------


def api_plan() -> list[tuple[str, dt.date]]:
    """(source, day) pairs for 2026: SP up to its end date, NRT afterwards; S-NPP ends 11-02."""
    a = settings()["api_2026"]
    first = dt.date.fromisoformat(a["first_day"])
    last = dt.date.fromisoformat(a["last_day"])
    sp_end = {k: dt.date.fromisoformat(v) for k, v in a["sp_last_day"].items()}
    snpp_end = dt.date.fromisoformat(a["snpp_last_day"])
    plan = []
    for sensor, instrument in (
        ("MODIS", "MODIS"),
        ("VIIRS_SNPP", "VIIRS"),
        ("VIIRS_NOAA20", "VIIRS"),
    ):
        day = first
        while day <= last:
            if sensor == "VIIRS_SNPP" and day > snpp_end:
                break
            kind = "SP" if day <= sp_end[instrument] else "NRT"
            plan.append((f"{sensor}_{kind}", day))
            day += dt.timedelta(days=1)
    return plan


def key_status() -> tuple[int, int]:
    r = SESSION.get(f"{FIRMS}/mapserver/mapkey_status/", params={"MAP_KEY": map_key()}, timeout=60)
    r.raise_for_status()
    j = r.json()
    return int(j.get("current_transactions", 0)), int(j.get("transaction_limit", 5000))


def api_day(source: str, day: dt.date) -> pd.DataFrame:
    assert_download_allowed(source, day, day)
    url = f"{FIRMS}/api/area/csv/{map_key()}/{source}/world/1/{day.isoformat()}"
    for attempt in range(6):
        try:
            r = SESSION.get(url, timeout=180)
            if r.status_code == 200 and not r.text.startswith("Invalid"):
                return pd.read_csv(io.StringIO(r.text), dtype={"acq_time": str})
            log(f"  {source} {day}: HTTP {r.status_code} {redact(r.text[:120])!r}")
        except requests.RequestException as e:
            log(f"  {source} {day}: {type(e).__name__}")
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"API failed for {source} {day}")


def api(limit_share: float = 0.8) -> None:
    out = data_dir() / "raw" / "firms_api"
    ledger_path = out / "ledger.csv"
    out.mkdir(parents=True, exist_ok=True)
    done = set()
    if ledger_path.exists():
        done = {(r["source"], r["day"]) for r in csv.DictReader(ledger_path.open())}
    todo = [(s, d) for s, d in api_plan() if (s, d.isoformat()) not in done]
    log(f"API: {len(todo)} source-days to fetch")
    new_ledger = not ledger_path.exists()
    with ledger_path.open("a", newline="") as lf:
        ledger = csv.writer(lf, lineterminator="\n")
        if new_ledger:
            ledger.writerow(["source", "day", "rows_raw", "rows_holdout_dropped", "rows_written"])
        for i, (source, day) in enumerate(todo):
            if i % 20 == 0:
                used, cap = key_status()
                while used > limit_share * cap:
                    log(f"  quota {used}/{cap}, waiting")
                    time.sleep(60)
                    used, cap = key_status()
            df = api_day(source, day)
            dropped = 0
            if source.startswith("VIIRS") and len(df):
                mask = in_holdout(df["latitude"].to_numpy(), df["longitude"].to_numpy())
                dropped = int(mask.sum())
                df = df[~mask]
            dest = out / source / f"{day.isoformat()}.csv"
            dest.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(dest, index=False, lineterminator="\n")
            ledger.writerow([source, day.isoformat(), len(df) + dropped, dropped, len(df)])
            lf.flush()
            if i % 50 == 0:
                log(f"  {i}/{len(todo)} {source} {day}: {len(df)} rows")
    log("API done")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("what", choices=["annual", "gfed", "missing", "api"])
    p.add_argument("--only", help="annual: one prefix (modis, viirs-snpp, viirs-jpss1)")
    args = p.parse_args()
    if args.what == "annual":
        annual(args.only)
    elif args.what == "gfed":
        gfed()
    elif args.what == "missing":
        missing()
    else:
        api()
    return 0


if __name__ == "__main__":
    sys.exit(main())
