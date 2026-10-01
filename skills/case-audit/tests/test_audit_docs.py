"""The skill text is executed by another model; pin the parts that break silently."""
import re
from pathlib import Path

import audit
from checks import RULES

KIT = Path(__file__).resolve().parents[3]
SKILL = (KIT / "skills" / "case-audit" / "SKILL.md").read_text(encoding="utf-8")
ENGINE = KIT / "skills" / "case-audit" / "engine"


def test_skill_runs_the_engine_by_the_substituted_plugin_root():
    assert 'python "${CLAUDE_PLUGIN_ROOT}/skills/case-audit/engine/audit.py"' in SKILL


def test_every_flag_the_skill_names_exists():
    parser_flags = set(re.findall(r'"(--[a-z-]+)"', (ENGINE / "audit.py").read_text(encoding="utf-8")))
    assert set(re.findall(r"(--[a-z][a-z-]+)", SKILL)) <= parser_flags


def test_every_profile_the_skill_names_is_valid():
    named = {p for row in re.findall(r"\| `([a-z,]+)`", SKILL) for p in row.split(",")}
    assert named and named <= set(audit.VALID_PROFILES)


def test_skill_says_what_to_do_on_every_exit():
    assert "Exit 0" in SKILL and "Exit 2" in SKILL and "Any other exit" in SKILL


def test_every_page_a_finding_cites_exists():
    cited = {m for p in ENGINE.glob("*.py")
             for m in re.findall(r"((?:concepts|methods|demos|references)/[\w-]+\.md)", p.read_text(encoding="utf-8"))}
    assert cited and [c for c in cited if not (KIT / c).is_file()] == []


def test_rule_ids_are_unique():
    ids = [r[0] for r in RULES]
    assert len(ids) == len(set(ids))
