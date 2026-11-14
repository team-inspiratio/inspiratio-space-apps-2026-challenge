@AGENTS.md

## Claude Code 专有说明

- 项目钩子在 `.claude/settings.json`（PreToolUse，脚本 `.claude/hooks/guard.py`，需要 `uv` 在 PATH 上）。它会拦截：下载 2012/2013 年 S-NPP VIIRS 的命令或网址、修改冻结文件、打印或读取 `.env`。被拦截时**不要绕过**（例如改写命令、换工具、拆成几步），而是停下来告诉人。
- 读密钥只用 `python-dotenv`，检查 `.env` 是否填好用 `uv run python tools/preflight.py`。
- 一个会话做一张任务卡；结束前按 AGENTS.md 的“开工流程”第 6 步更新进度并 push。
