"""Claude Code PreToolUse hook: an early reminder layer in front of the CI guardrails.

Blocks (exit code 2, reason on stderr, which Claude sees):
  - shell commands or fetched URLs that request 2012/2013 S-NPP VIIRS (time-locked test set)
  - edits to frozen files listed in config/frozen-manifest.json, and to the manifest itself
  - printing .env (keeps the FIRMS key out of transcripts and logs)

Standard library only; the rules live in tools/guardrails.py.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import guardrails  # noqa: E402

SHELL_TOOLS = {"Bash", "PowerShell"}
EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHOW_ENV_RE = re.compile(
    r"(\b(cat|type|get-content|gc|less|more|head|tail|select-string|grep|rg|sed|awk)\b"
    r"[^|;&]*\.env\b(?!\.)"
    r"|\becho\b[^|;&]*\$\{?(env:)?FIRMS_MAP_KEY|\bprintenv\b|^\s*(env|set)\s*$)",
    re.IGNORECASE,
)


def relative(path: str) -> str | None:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except (ValueError, OSError):
        return None


def block(reason: str) -> int:
    print(f"Blocked by project guardrail: {reason} (see AGENTS.md, red lines)", file=sys.stderr)
    return 2


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool = event.get("tool_name", "")
    args = event.get("tool_input", {}) or {}

    if tool in SHELL_TOOLS:
        command = args.get("command", "")
        if reason := guardrails.locked_download_reason(command):
            return block(reason)
        if SHOW_ENV_RE.search(command):
            return block("do not print .env or the FIRMS key; load it with python-dotenv")
    elif tool == "WebFetch":
        if reason := guardrails.locked_download_reason("download " + args.get("url", "")):
            return block(reason)
    elif tool in EDIT_TOOLS:
        rel = relative(args.get("file_path") or args.get("notebook_path") or "")
        if rel and rel in guardrails.frozen_paths():
            return block(f"{rel} is frozen; only a human may change it")
    elif tool == "Read":
        rel = relative(args.get("file_path", ""))
        if rel == ".env":
            return block("do not read .env into the conversation; it holds the FIRMS key")
    return 0


if __name__ == "__main__":
    sys.exit(main())
