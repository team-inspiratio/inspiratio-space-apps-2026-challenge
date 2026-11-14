@AGENTS.md

## Notes specific to Claude Code

- The project hook lives in `.claude/settings.json` (PreToolUse, script `.claude/hooks/guard.py`; it needs `uv` on the PATH). It blocks: commands or URLs that download 2012/2013 S-NPP VIIRS, edits to frozen files, and printing or reading `.env`. When something is blocked, **do not work around it** (for example by rewriting the command, switching tools or splitting it into several steps); stop and tell a person.
- Read secrets only through `python-dotenv`; to check whether `.env` is filled in, use `uv run python tools/preflight.py`.
- One task card per session; before finishing, update progress and push as in step 6 of the "Start-of-session routine" in AGENTS.md.
