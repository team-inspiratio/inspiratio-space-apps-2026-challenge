"""Repository guardrails (plan section 4 and 11.3). Standard library only.

Used by three layers that enforce the same rules:
  - CI (.github/workflows/ci.yml) and pre-commit: `python tools/guardrails.py check`
  - the Claude Code PreToolUse hook (.claude/hooks/guard.py)
  - download code (S02 onward) must call `assert_download_allowed()` before every request

Checks:
  1. frozen files (config/frozen-manifest.json) still match their recorded SHA256, and the
     manifest is append-only across git history
  2. the model feature list (config/features.json) has no year, region-name or VIIRS columns
  3. no tracked config or code requests 2012/2013 S-NPP VIIRS (the time-locked test set)
  4. no FIRMS MAP_KEY value in any tracked file

Freeze files (human-approved, done in S01/S07/S11): `python tools/guardrails.py freeze PATH...`
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "frozen-manifest.json"
FEATURES = ROOT / "config" / "features.json"

# --- test-set locks ---------------------------------------------------------------------------

LOCKED_SNPP_START = dt.date(2012, 1, 1)
LOCKED_SNPP_END = dt.date(2013, 12, 31)

# Ways S-NPP VIIRS shows up in FIRMS URLs, API source names and file names.
SNPP_RE = re.compile(r"(viirs[\W_]*snpp|suomi|\bs[\W_]?npp\b|snpp|vnp14|\bnpp\b)", re.IGNORECASE)
LOCKED_YEAR_RE = re.compile(r"(?<!\d)(2012|2013)(?!\d)")
DOWNLOAD_RE = re.compile(
    r"(https?://|/api/|curl|wget|invoke-webrequest|\biwr\b|invoke-restmethod|\birm\b|"
    r"requests\.|urlopen|urlretrieve|httpx|aria2c|download|firms\.modaps)",
    re.IGNORECASE,
)

# Files allowed to mention locked downloads: the external grader, the guardrails themselves,
# their tests, and prose.
LOCK_SCAN_ALLOW = (
    ".github/workflows/grader.yml",
    "tools/guardrails.py",
    ".claude/hooks/",
    "tests/",
)
SCANNED_SUFFIXES = {
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".sh",
    ".ps1",
    ".cfg",
    ".ini",
    ".txt",
    ".ipynb",
}

# --- secrets ----------------------------------------------------------------------------------

MAP_KEY_RE = re.compile(
    r"(?i)(?:map_?key\s*[=:]\s*[\"']?|/api/[a-z_]+/(?:csv|json|kml|shp)/)([0-9a-f]{32})"
)

# --- features ---------------------------------------------------------------------------------

BANNED_FEATURE_RE = re.compile(
    r"(year|\byr\b|_yr|region|country|continent|basin|place|name|"
    r"viirs|snpp|npp|noaa|vnp|vj1|target|label)",
    re.IGNORECASE,
)


class LockedDataError(RuntimeError):
    """Raised when code tries to fetch test-set data that must never reach this machine."""


def assert_download_allowed(source: str, start: dt.date, end: dt.date) -> None:
    """Refuse any S-NPP VIIRS request that overlaps 2012-01-01..2013-12-31 (test 1)."""
    if SNPP_RE.search(source) and start <= LOCKED_SNPP_END and end >= LOCKED_SNPP_START:
        raise LockedDataError(
            f"{source} {start}..{end} overlaps the locked S-NPP years 2012-2013. "
            "Only the GitHub Actions grader may download them (plan section 4)."
        )


def locked_download_reason(text: str) -> str | None:
    """Return why `text` (a command, URL or source line) looks like a locked download."""
    for line in text.splitlines() or [text]:
        if SNPP_RE.search(line) and LOCKED_YEAR_RE.search(line) and DOWNLOAD_RE.search(line):
            return f"requests 2012/2013 S-NPP VIIRS data: {line.strip()[:200]}"
    return None


# --- helpers ----------------------------------------------------------------------------------


def file_sha256(path: Path) -> str:
    """SHA256 with line endings normalised, so Windows and Linux checkouts agree."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [p for p in out.split("\0") if p]


def load_manifest() -> dict[str, str]:
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8")).get("frozen", {})


def frozen_paths() -> set[str]:
    """Paths no AI edit tool may touch: everything in the manifest, plus the manifest itself."""
    return set(load_manifest()) | {"config/frozen-manifest.json"}


# --- checks -----------------------------------------------------------------------------------


def check_frozen() -> list[str]:
    errors = []
    for rel, expected in load_manifest().items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"frozen file missing: {rel}")
        elif file_sha256(path) != expected:
            errors.append(f"frozen file changed: {rel}")
    return errors


def check_manifest_append_only() -> list[str]:
    """Once frozen, a file's hash may never change or disappear in later manifest versions.

    Needs full git history (CI checks out with fetch-depth 0). Unfreezing is a human decision:
    a commit whose message contains "[unfreeze]" resets the baseline (AGENTS.md red line).
    """
    rel = MANIFEST.relative_to(ROOT).as_posix()
    log = subprocess.run(
        ["git", "log", "--reverse", "--format=%H %s", "--", rel],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    versions = []
    for line in log:
        sha, _, subject = line.partition(" ")
        if "[unfreeze]" in subject:
            versions = []
        show = subprocess.run(
            ["git", "show", f"{sha}:{rel}"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        versions.append(json.loads(show.stdout).get("frozen", {}) if show.returncode == 0 else {})
    versions.append(load_manifest())  # working tree
    errors, seen = [], {}
    for frozen in versions:
        for path, digest in seen.items():
            if frozen.get(path) != digest:
                errors.append(f"frozen entry changed or removed in manifest history: {path}")
        seen.update({p: d for p, d in frozen.items() if p not in seen})
    return sorted(set(errors))


def check_features() -> list[str]:
    if not FEATURES.exists():
        return []
    names = json.loads(FEATURES.read_text(encoding="utf-8"))
    if isinstance(names, dict):
        names = names.get("features", [])
    return [f"banned feature name: {n}" for n in names if BANNED_FEATURE_RE.search(str(n))]


def check_locked_downloads(files: list[str]) -> list[str]:
    errors = []
    for rel in files:
        if rel.startswith(LOCK_SCAN_ALLOW) or Path(rel).suffix.lower() not in SCANNED_SUFFIXES:
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        reason = locked_download_reason(path.read_text(encoding="utf-8", errors="ignore"))
        if reason:
            errors.append(f"{rel}: {reason}")
    return errors


def check_secrets(files: list[str]) -> list[str]:
    errors = []
    for rel in files:
        path = ROOT / rel
        if not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        if MAP_KEY_RE.search(path.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"{rel}: contains a FIRMS MAP_KEY value (keep it in .env only)")
    return errors


def run_checks() -> list[str]:
    files = tracked_files()
    return (
        check_frozen()
        + check_manifest_append_only()
        + check_features()
        + check_locked_downloads(files)
        + check_secrets(files)
    )


def freeze(paths: list[str]) -> None:
    manifest = load_manifest()
    for p in paths:
        rel = Path(p).resolve().relative_to(ROOT).as_posix()
        manifest[rel] = file_sha256(ROOT / rel)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps({"frozen": dict(sorted(manifest.items()))}, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    fr = sub.add_parser("freeze")
    fr.add_argument("paths", nargs="+")
    args = parser.parse_args()

    if args.cmd == "freeze":
        freeze(args.paths)
        print(f"frozen: {', '.join(args.paths)}")
        return 0

    errors = run_checks()
    for e in errors:
        print(f"GUARDRAIL: {e}", file=sys.stderr)
    print(f"guardrails: {len(errors)} violation(s), {len(load_manifest())} frozen file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
