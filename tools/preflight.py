"""Environment preflight for anyone (human or AI) picking up the project. Never prints secrets.

uv run python tools/preflight.py            # all checks
uv run python tools/preflight.py --need-gb 50   # data stages need ~50 GB free
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        # Explicit UTF-8: on Chinese Windows the default codepage (GBK) cannot decode gh's output.
        p = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--need-gb", type=float, default=5.0, help="free space needed for data")
    args = parser.parse_args()
    results: list[tuple[str, bool, str]] = []

    results.append(("python 3.12", sys.version_info[:2] == (3, 12), sys.version.split()[0]))

    env = dotenv_values(ROOT / ".env")
    key = env.get("FIRMS_MAP_KEY") or ""
    results.append((".env FIRMS_MAP_KEY", len(key) == 32, "set" if key else "missing"))

    data_dir = env.get("INSPIRATIO_DATA_DIR") or ""
    if data_dir:
        path = Path(data_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(path).free / 1e9
        results.append(("data dir free space", free >= args.need_gb, f"{path}: {free:.0f} GB free"))
    else:
        results.append(("data dir free space", False, "INSPIRATIO_DATA_DIR missing in .env"))

    code, out = run(["git", "config", "core.longpaths"])
    results.append(("git core.longpaths", out == "true" or sys.platform != "win32", out or "unset"))

    code, out = run(["git", "branch", "--show-current"])
    results.append(("git branch", code == 0 and out != "main", out))

    hook = (ROOT / ".git" / "hooks" / "pre-commit").exists()
    results.append(("pre-commit installed", hook, "run: uv run pre-commit install"))

    if shutil.which("gh"):
        code, out = run(["gh", "auth", "status"])
        results.append(
            ("gh logged in", code == 0, "ok" if code == 0 else "run: gh auth login --web")
        )
    else:
        results.append(("gh installed", False, "install GitHub CLI: https://cli.github.com"))

    code, out = run([sys.executable, "-X", "utf8", "tools/guardrails.py", "check"])
    results.append(("guardrails", code == 0, out.splitlines()[-1] if out else ""))

    width = max(len(name) for name, _, _ in results)
    for name, ok, detail in results:
        print(f"[{'OK ' if ok else 'FIX'}] {name:<{width}}  {detail}")
    failed = [name for name, ok, _ in results if not ok]
    print(f"\npreflight: {len(failed)} item(s) to fix" if failed else "\npreflight: all good")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
