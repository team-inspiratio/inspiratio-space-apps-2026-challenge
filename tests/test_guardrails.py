"""Smoke tests for the repository guardrails and the Claude Code hook (plan section 8)."""

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import guardrails  # noqa: E402

HOOK = ROOT / ".claude" / "hooks" / "guard.py"
FAKE_KEY = "0123456789abcdef" * 2


def run_hook(event: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True, text=True
    )


@pytest.mark.parametrize(
    "command",
    [
        "curl -O https://firms.modaps.eosdis.nasa.gov/data/annual/viirs-snpp_2012_all.zip",
        "wget https://example.org/SUOMI_VIIRS_C2_Global_2013.zip",
        "python -c \"requests.get('https://firms.modaps.eosdis.nasa.gov/api/area/csv/K/"
        "VIIRS_SNPP_SP/world/10/2013-06-01')\"",
    ],
)
def test_locked_downloads_are_detected(command):
    assert guardrails.locked_download_reason(command)


@pytest.mark.parametrize(
    "command",
    [
        "curl -O https://firms.modaps.eosdis.nasa.gov/data/annual/viirs-snpp_2014_all.zip",
        "curl -O https://firms.modaps.eosdis.nasa.gov/data/annual/modis_2012_all.zip",
        'SNPP_START = "2012-01-20"  # constant only',
    ],
)
def test_allowed_requests_pass(command):
    assert guardrails.locked_download_reason(command) is None


def test_assert_download_allowed():
    with pytest.raises(guardrails.LockedDataError):
        guardrails.assert_download_allowed(
            "VIIRS_SNPP_SP", dt.date(2011, 12, 1), dt.date(2012, 2, 1)
        )
    guardrails.assert_download_allowed("VIIRS_SNPP_SP", dt.date(2014, 1, 1), dt.date(2014, 12, 31))
    guardrails.assert_download_allowed("MODIS_SP", dt.date(2012, 1, 1), dt.date(2013, 12, 31))
    guardrails.assert_download_allowed("VIIRS_NOAA20_SP", dt.date(2018, 4, 1), dt.date(2018, 5, 1))


def test_hook_blocks_locked_download():
    cmd = "curl -O https://firms.modaps.eosdis.nasa.gov/data/annual/viirs-snpp_2013_all.zip"
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}})
    assert result.returncode == 2
    assert "2012/2013" in result.stderr


def test_hook_blocks_printing_env():
    assert run_hook({"tool_name": "Bash", "tool_input": {"command": "cat .env"}}).returncode == 2
    read_env = {"tool_name": "Read", "tool_input": {"file_path": str(ROOT / ".env")}}
    assert run_hook(read_env).returncode == 2
    echo_key = {"tool_name": "PowerShell", "tool_input": {"command": "echo $env:FIRMS_MAP_KEY"}}
    assert run_hook(echo_key).returncode == 2
    for command in ("cat .env.example", "grep -rn FIRMS_MAP_KEY tools/"):
        assert run_hook({"tool_name": "Bash", "tool_input": {"command": command}}).returncode == 0


def test_hook_blocks_editing_manifest_and_allows_normal_files():
    manifest = {"tool_name": "Edit", "tool_input": {"file_path": str(guardrails.MANIFEST)}}
    assert run_hook(manifest).returncode == 2
    normal = {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "PROGRESS.md")}}
    assert run_hook(normal).returncode == 0


def test_banned_features_are_detected(tmp_path, monkeypatch):
    features = tmp_path / "features.json"
    features.write_text(json.dumps(["modis_count", "frp_p75", "year", "viirs_count"]))
    monkeypatch.setattr(guardrails, "FEATURES", features)
    assert guardrails.check_features() == [
        "banned feature name: year",
        "banned feature name: viirs_count",
    ]


def test_map_key_pattern():
    assert guardrails.MAP_KEY_RE.search(f"FIRMS_MAP_KEY={FAKE_KEY}")
    assert guardrails.MAP_KEY_RE.search(f"/api/area/csv/{FAKE_KEY}/MODIS_SP/world/1")
    assert not guardrails.MAP_KEY_RE.search("/api/area/csv/{MAP_KEY}/MODIS_SP/world/1")


def test_frozen_hash_ignores_line_endings(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_bytes(b"x = 1\ny = 2\n")
    b.write_bytes(b"x = 1\r\ny = 2\r\n")
    assert guardrails.file_sha256(a) == guardrails.file_sha256(b)


def test_repository_passes_guardrails():
    assert guardrails.run_checks() == []
