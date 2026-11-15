# 0002 The frozen guardrails crash on Chinese Windows when reading git history

## Background

S01 froze `tools/guardrails.py`. The first local commit after the freeze revealed the problem: `check_manifest_append_only()` reads `git log` with `subprocess.run(..., text=True)` without specifying an encoding. Chinese Windows decodes as GBK by default, and the S01 commit message contained Chinese text ("S01 pre-registration", written in Chinese), so running `python tools/guardrails.py check` locally crashed outright. Linux (CI, the grader) uses UTF-8 by default and is not affected, so CI's verdict remains valid as usual.

The file is frozen and an AI may not change it (red line 2), so for now the problem is worked around without changing the frozen file.

## Options

1. **Keep things as they are**: locally, always use `python -X utf8 tools/guardrails.py check` (`.pre-commit-config.yaml` and `tools/preflight.py` have already been changed accordingly; neither file is in the frozen manifest). When running it by hand, also add `-X utf8`, or set the environment variable `PYTHONUTF8=1`. The same goes for running the tests: `uv run python -X utf8 -m pytest` (otherwise `test_repository_passes_guardrails` fails on Chinese Windows).
2. **A person unfreezes and fixes it**: add `encoding="utf-8"` to the two `subprocess.run` calls in `guardrails.py`, freeze it again, and write `[unfreeze]` and the reason in the commit message. Only the encoding changes, none of the rules.

## Recommendation

Option 1 is enough: it does not affect any rule or result. If teammates often run the guardrails by hand on Chinese Windows, do option 2 as well.

## Status

**Confirmed: option 1 (qiuxue-yee, 2026-11-03).** The user's words (translated from Chinese): "Up to you; go with whichever you think is better." Option 1 was chosen as recommended: no unfreezing, and locally always add `-X utf8`. If anyone later wants option 2, a person must commit the `[unfreeze]` themselves.
