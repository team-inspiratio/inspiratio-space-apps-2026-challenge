# 0002 冻结的护栏在中文 Windows 上读 git 历史会崩溃

## 背景

S01 冻结了 `tools/guardrails.py`。冻结后第一次本地提交时发现：`check_manifest_append_only()` 用 `subprocess.run(..., text=True)` 读 `git log`，没有指定编码。中文 Windows 默认按 GBK 解码，而 S01 的提交信息里有中文（“S01 预注册”），于是本地运行 `python tools/guardrails.py check` 直接崩溃。Linux（CI、grader）默认 UTF-8，不受影响，CI 的裁决照常有效。

文件已冻结，AI 不能改（红线 2），所以先用不改冻结文件的办法绕开。

## 选项

1. **保持现状**：本地一律用 `python -X utf8 tools/guardrails.py check`（已改好 `.pre-commit-config.yaml` 和 `tools/preflight.py`，这两个文件不在冻结清单里）。手动运行时也要加 `-X utf8`，或设环境变量 `PYTHONUTF8=1`。跑测试同理：`uv run python -X utf8 -m pytest`（否则 `test_repository_passes_guardrails` 在中文 Windows 上会失败）。
2. **由人解冻并修复**：在 `guardrails.py` 的两处 `subprocess.run` 加 `encoding="utf-8"`，重新冻结，提交信息写 `[unfreeze]` 和理由。只改编码，不改任何规则。

## 建议

选项 1 已经够用，不影响任何规则和结果；如果队友经常在中文 Windows 上手动跑护栏，再做选项 2。

## 状态

**已确认：选项 1（qiuxue-yee，2026-11-03）。** 用户原话：“看你自己 你觉得哪个好就按照哪个来”，按建议选选项 1：不解冻，本地一律加 `-X utf8`。以后如果有人想做选项 2，必须由人自己提交 `[unfreeze]`。
