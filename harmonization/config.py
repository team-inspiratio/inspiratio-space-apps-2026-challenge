"""Shared paths and settings. Secrets come from .env through python-dotenv and are never logged."""

from __future__ import annotations

import json
import os
import sys
from functools import cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import guardrails  # noqa: E402

load_dotenv(ROOT / ".env")


@cache
def settings() -> dict:
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


@cache
def regions() -> list[dict]:
    return json.loads((ROOT / "config" / "regions.json").read_text(encoding="utf-8"))["regions"]


def data_dir() -> Path:
    raw = os.environ.get("INSPIRATIO_DATA_DIR")
    if not raw:
        raise SystemExit("INSPIRATIO_DATA_DIR is not set in .env (see .env.example)")
    path = Path(raw).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def map_key() -> str:
    key = os.environ.get("FIRMS_MAP_KEY", "")
    if len(key) != 32:
        raise SystemExit("FIRMS_MAP_KEY missing or malformed in .env")
    return key


def redact(text: str) -> str:
    """Remove the MAP_KEY from any string before it is printed or logged."""
    key = os.environ.get("FIRMS_MAP_KEY", "")
    return text.replace(key, "<MAP_KEY>") if key else text


def done_marker(stage: str) -> Path:
    return data_dir() / f"{stage}.done"


in_holdout = guardrails.in_holdout
assert_download_allowed = guardrails.assert_download_allowed
