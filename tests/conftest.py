"""Put the repository root on sys.path for every test module, whatever order pytest collects them
in and however it is started (`uv run pytest` in CI, `python -m pytest` locally)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows with a Chinese locale decodes `git log` output as GBK unless Python runs in UTF-8 mode,
# so test_guardrails failed locally (ADR 0002 runs the guardrail CLI with -X utf8 for the same
# reason). Mirror that here for text-mode subprocess calls only; CI on Linux is unaffected, and the
# frozen tools/guardrails.py stays untouched.
if sys.platform == "win32" and not sys.flags.utf8_mode:
    import functools
    import subprocess

    _run = subprocess.run

    @functools.wraps(_run)
    def _run_utf8(*args, **kwargs):
        if (kwargs.get("text") or kwargs.get("universal_newlines")) and not kwargs.get("encoding"):
            kwargs["encoding"] = "utf-8"
        return _run(*args, **kwargs)

    subprocess.run = _run_utf8
