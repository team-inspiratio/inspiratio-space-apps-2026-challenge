"""PROGRESS.md must keep a parseable status block that points at an existing task card."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "current_card",
    "status",
    "claimed_by",
    "claimed_at",
    "last_pushed_stage",
    "next_step",
    "needs_human",
}


def status_block() -> dict:
    text = (ROOT / "PROGRESS.md").read_text(encoding="utf-8")
    match = re.search(
        r"<!-- STATUS:BEGIN -->\s*```yaml\n(.*?)```\s*<!-- STATUS:END -->", text, re.S
    )
    assert match, "PROGRESS.md status block not found"
    return yaml.safe_load(match.group(1))


def test_status_block_is_complete():
    block = status_block()
    assert REQUIRED <= block.keys()
    assert block["status"] in {"ready", "in_progress", "blocked", "done"}
    assert isinstance(block["needs_human"], list)


def test_current_card_exists():
    assert (ROOT / status_block()["current_card"]).is_file()


def test_every_task_card_has_required_sections():
    cards = sorted((ROOT / "docs" / "sessions").glob("*.md"))
    assert {c.stem for c in cards} >= {
        "1-data",
        "2-baselines",
        "3-model",
        "4-freeze-test",
        "5-report",
        "G-global",
    }
    for card in cards:
        text = card.read_text(encoding="utf-8")
        for heading in (
            "前置条件",
            "只读计划",
            "要做的阶段",
            "验收标准",
            "禁止事项",
            "结束时",
            "下一张卡",
        ):
            assert heading in text, f"{card.name} is missing section {heading}"
