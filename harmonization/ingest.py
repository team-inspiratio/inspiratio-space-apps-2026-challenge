"""S03 import: stream FIRMS CSVs (yearly zips and API days) into Parquet, one file per source.

uv run python -m harmonization.ingest            # everything not imported yet
uv run python -m harmonization.ingest --keep-zips

VIIRS rows inside holdout regions are dropped in memory, chunk by chunk, before anything is
written (plan section 4.2). After a VIIRS zip is imported it is deleted; its SHA256 stays in
docs/data-manifest.csv. Every source file gets one line in the ledger:
rows_raw = rows_written + rows_holdout_dropped.

Output: <data>/interim/points/<sensor>/<year>/<source>.parquet with a common schema.
"""

from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from harmonization.config import ROOT, data_dir, in_holdout
from harmonization.download import read_manifest

LEDGER = ROOT / "docs" / "ingest-ledger.csv"
LEDGER_FIELDS = ["source", "product", "rows_raw", "rows_holdout_dropped", "rows_written"]
CHUNK = 1_000_000

# FIRMS `satellite` values -> our sensor names (checked against the real files in S02).
SATELLITE = {
    "Terra": "terra",
    "T": "terra",
    "Aqua": "aqua",
    "A": "aqua",
    "N": "snpp",
    "Suomi NPP": "snpp",
    "SNPP": "snpp",
    "1": "noaa20",
    "N20": "noaa20",
    "NOAA-20": "noaa20",
    "J1": "noaa20",
}
VIIRS = {"snpp", "noaa20"}

SCHEMA = pa.schema(
    [
        ("sensor", pa.string()),
        ("product", pa.string()),  # SP (standard) or NRT
        ("latitude", pa.float64()),
        ("longitude", pa.float64()),
        ("acq_date", pa.date32()),
        ("acq_time", pa.int16()),  # HHMM UTC
        ("confidence", pa.string()),  # MODIS 0-100 as text, VIIRS l/n/h
        ("frp", pa.float32()),
        ("scan", pa.float32()),
        ("track", pa.float32()),
        ("daynight", pa.string()),
        ("type", pa.int8()),  # -1 when the product has no type column (NRT)
        ("version", pa.string()),
        ("country", pa.string()),  # yearly packages are split by country; "" for API
    ]
)


def normalise(df: pd.DataFrame, product: str, country: str) -> pd.DataFrame:
    sat = df["satellite"].astype(str).str.strip()
    sensor = sat.map(SATELLITE)
    if sensor.isna().any():
        raise ValueError(f"unknown satellite codes: {sorted(sat[sensor.isna()].unique())[:5]}")
    out = pd.DataFrame(
        {
            "sensor": sensor,
            "product": product,
            "latitude": df["latitude"].astype("float64"),
            "longitude": df["longitude"].astype("float64"),
            "acq_date": pd.to_datetime(df["acq_date"]).dt.date,
            "acq_time": pd.to_numeric(df["acq_time"]).astype("int16"),
            "confidence": df["confidence"].astype(str).str.strip(),
            "frp": df["frp"].astype("float32"),
            "scan": df["scan"].astype("float32"),
            "track": df["track"].astype("float32"),
            "daynight": df["daynight"].astype(str),
            "type": (
                pd.to_numeric(df["type"]).astype("int8")
                if "type" in df
                else np.full(len(df), -1, dtype="int8")
            ),
            "version": df["version"].astype(str) if "version" in df else "",
            "country": country,
        }
    )
    return out


def drop_holdout_viirs(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    viirs = df["sensor"].isin(VIIRS).to_numpy()
    if not viirs.any():
        return df, 0
    hold = viirs & np.asarray(in_holdout(df["latitude"].to_numpy(), df["longitude"].to_numpy()))
    return df[~hold], int(hold.sum())


def zip_chunks(path: Path) -> Iterator[tuple[pd.DataFrame, str]]:
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if not info.filename.lower().endswith(".csv") or info.file_size == 0:
                continue
            country = Path(info.filename).stem.split("_", 2)[-1]
            with z.open(info) as f:
                yield from (
                    (c, country) for c in pd.read_csv(f, chunksize=CHUNK, dtype={"acq_time": str})
                )


class Writers:
    """One ParquetWriter per (sensor, year) for a given source file."""

    def __init__(self, source: str):
        self.source = source
        self.open: dict[tuple[str, int], pq.ParquetWriter] = {}
        self.paths: list[Path] = []

    def write(self, df: pd.DataFrame) -> None:
        years = pd.to_datetime(df["acq_date"]).dt.year
        for (sensor, year), part in df.groupby([df["sensor"], years]):
            key = (sensor, int(year))
            if key not in self.open:
                path = (
                    data_dir()
                    / "interim"
                    / "points"
                    / sensor
                    / str(year)
                    / (f"{self.source}.parquet.tmp")
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                self.open[key] = pq.ParquetWriter(path, SCHEMA, compression="zstd")
                self.paths.append(path)
            table = pa.Table.from_pandas(part, schema=SCHEMA, preserve_index=False)
            self.open[key].write_table(table)

    def close(self) -> None:
        for w in self.open.values():
            w.close()
        for p in self.paths:
            p.replace(p.with_name(p.name.removesuffix(".tmp")))


def read_ledger() -> dict[str, dict]:
    if not LEDGER.exists():
        return {}
    with LEDGER.open(encoding="utf-8", newline="") as f:
        return {r["source"]: r for r in csv.DictReader(f)}


def write_ledger(rows: dict[str, dict]) -> None:
    with LEDGER.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows[k] for k in sorted(rows))


def import_source(source: str, product: str, chunks: Iterator[tuple[pd.DataFrame, str]]) -> dict:
    writers = Writers(source)
    raw = dropped = written = 0
    try:
        for chunk, country in chunks:
            raw += len(chunk)
            df = normalise(chunk, product, country)
            df, d = drop_holdout_viirs(df)
            dropped += d
            written += len(df)
            if len(df):
                writers.write(df)
    finally:
        writers.close()
    return {
        "source": source,
        "product": product,
        "rows_raw": raw,
        "rows_holdout_dropped": dropped,
        "rows_written": written,
    }


def imported_here(source: str) -> bool:
    """Imported into THIS data folder. The ledger is committed (it describes the original run),
    so being listed there alone does not mean the points are here."""
    return any((data_dir() / "interim" / "points").glob(f"*/*/{source}.parquet"))


def same_as_ledger(row: dict, ledger: dict, strict: bool = True) -> None:
    """A source the committed ledger lists must import to exactly the recorded counts. The
    yearly archive is hash-locked, so a difference stops the run; the API (2026) can change as
    FIRMS reprocesses near-real-time data, so there it is only reported."""
    old = ledger.get(row["source"])
    if old is None:
        return
    for k in ("rows_raw", "rows_holdout_dropped", "rows_written"):
        if int(old[k]) != int(row[k]):
            msg = f"{row['source']}: {k} {row[k]} differs from the ledger ({old[k]})"
            if strict:
                raise SystemExit(msg)
            print(f"WARNING {msg}", flush=True)


def api_chunks(files: list[Path]) -> Iterator[tuple[pd.DataFrame, str]]:
    for f in files:
        df = pd.read_csv(f, dtype={"acq_time": str})
        if len(df):
            yield df, ""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--keep-zips", action="store_true", help="do not delete VIIRS zips")
    p.add_argument("--yearly-only", action="store_true", help="skip the API folders")
    args = p.parse_args()
    ledger = read_ledger()
    manifest = read_manifest()

    for path in sorted((data_dir() / "raw" / "firms_yearly").glob("*.zip")):
        source = path.stem
        if imported_here(source):
            continue
        row = import_source(source, "SP", zip_chunks(path))
        same_as_ledger(row, ledger)
        listed = int(manifest.get(f"raw/firms_yearly/{path.name}", {}).get("rows", -1))
        if listed != row["rows_raw"]:
            raise SystemExit(f"{source}: read {row['rows_raw']} rows, manifest says {listed}")
        ledger[source] = row
        write_ledger(ledger)
        print(f"ok {source}: {row}", flush=True)
        if path.name.startswith("viirs") and not args.keep_zips:
            path.unlink()  # plan 4.2: keep only the hash (docs/data-manifest.csv)

    api_root = data_dir() / "raw" / "firms_api"
    api_folders = [] if args.yearly_only else sorted(d for d in api_root.glob("*") if d.is_dir())
    for folder in api_folders:
        source = f"api_{folder.name}"
        if imported_here(source):
            continue
        product = "NRT" if folder.name.endswith("NRT") else "SP"
        row = import_source(source, product, api_chunks(sorted(folder.glob("*.csv"))))
        ledger_api = api_root / "ledger.csv"
        if ledger_api.exists():  # holdout rows were already dropped at fetch time
            fetched = pd.read_csv(ledger_api)
            fetched = fetched[fetched["source"] == folder.name]
            row["rows_raw"] = int(fetched["rows_raw"].sum())
            row["rows_holdout_dropped"] += int(fetched["rows_holdout_dropped"].sum())
        same_as_ledger(row, ledger, strict=False)
        ledger[source] = row
        write_ledger(ledger)
        print(f"ok {source}: {row}", flush=True)

    bad = [
        r["source"]
        for r in ledger.values()
        if int(r["rows_raw"]) != int(r["rows_written"]) + int(r["rows_holdout_dropped"])
    ]
    print("ledger closes" if not bad else f"LEDGER DOES NOT CLOSE: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
