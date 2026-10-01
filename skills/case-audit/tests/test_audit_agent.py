"""The agent brief and the engine name the same rules, pages and commands."""
import re
from pathlib import Path

from checks import RULES
from thresholds import DC_SKELETON_PARTIAL_SHARE, DC_SKELETON_SHARE

KIT = Path(__file__).resolve().parents[3]
AGENT = (KIT / "agents" / "case-auditor.md").read_text(encoding="utf-8")
SKILL = (KIT / "skills" / "case-audit" / "SKILL.md").read_text(encoding="utf-8")


def test_the_draft_has_moved():
    assert not (KIT / "docs" / "agents" / "case-auditor.md").exists()
    assert "${CLAUDE_PLUGIN_ROOT}/agents/case-auditor.md" in SKILL


def test_agent_runs_the_skill_by_the_plugin_root():
    assert "${CLAUDE_PLUGIN_ROOT}/skills/case-audit/SKILL.md" in AGENT


def test_agent_and_engine_name_the_same_rules():
    # opf.conditions is a bundle: the engine reports it as opf.1 to opf.3, plus opf.preview.
    engine = ({r[0] for r in RULES} - {"opf.conditions"}) | {"opf.preview"}
    named = set(re.findall(r"`((?:base|mon|ts)\.[a-z_0-9]+|opf\.preview)`", AGENT))
    assert named == engine
    assert {"opf.1", "opf.3"} <= set(re.findall(r"\bopf\.\d\b", AGENT))


def test_every_page_the_agent_cites_exists():
    cited = set(re.findall(r"`((?:concepts|methods|demos|references)/[\w-]+\.md)`", AGENT))
    assert cited and [c for c in cited if not (KIT / c).is_file()] == []
    assert "written in Plan 2" not in AGENT


def test_the_brief_states_the_engines_numbers_and_verdict_lines():
    [row] = [l for l in AGENT.splitlines() if l.startswith("| `base.dc_skeleton`")]
    assert f"{DC_SKELETON_SHARE:.0%}".replace("%", " %") in row and f"{DC_SKELETON_PARTIAL_SHARE:.0%}".replace("%", " %") in row
    assert "zero-length" not in row
    assert "- scopf: READY | NOT READY" in AGENT and "the engine always writes it" in AGENT
    assert "If findings.json says source is snapshot, the case was not opened" in AGENT


def test_the_brief_shows_the_engines_opf_table_header():
    src = (KIT / "skills" / "case-audit" / "engine" / "report.py").read_text(encoding="utf-8")
    header = re.search(r'"(\| area \| OPF may redispatch it[^"]*)"', src).group(1)
    assert "| with cost data |" in header and header in AGENT
