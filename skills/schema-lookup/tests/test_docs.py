"""The skill and agent text is executed by another model; pin the parts that break silently."""
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
SKILL = (KIT / "skills" / "schema-lookup" / "SKILL.md").read_text(encoding="utf-8")
AGENT = (KIT / "agents" / "schema-librarian.md").read_text(encoding="utf-8")


def test_skill_commands_use_the_substituted_plugin_root():
    assert '"${CLAUDE_PLUGIN_ROOT}/skills/schema-lookup/engine/lookup.py"' in SKILL
    assert not [l for l in SKILL.splitlines() if l.lstrip().startswith('python "$KIT/')]


def test_agent_finds_the_skill_by_the_plugin_root():
    assert "${CLAUDE_PLUGIN_ROOT}/skills/schema-lookup/SKILL.md" in AGENT


def test_skill_never_tells_a_read_only_field_to_be_set():
    assert "read-only: say it cannot be written" in SKILL


def test_powershell_search_command_is_one_line():
    for name in ("AGENTS.md", "GEMINI.md"):
        lines = (KIT / name).read_text(encoding="utf-8").splitlines()
        cmd = [l for l in lines if "Select-String" in l]
        assert cmd and all(r"$KIT\references\*.md" in l for l in cmd), name
