"""The PowerWorldHiveMind tag for Claude Code's terminal status line.

Prints [PWHM#0.4.0], plus a yellow "↑0.5.0 available" when the kit's daily update check has
seen a newer version. Status lines render in the terminal only, not in the desktop app.

/powerworld-hivemind:powerworld-setup adds it only when the user says yes. If they already
had a status line, setup saves that command to ~/.claude/powerworld-hivemind-statusline.json;
this script runs it on the same input and puts the tag beside it, so nothing is replaced.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home() / ".claude"
VERSION_CACHE = HOME / "powerworld-hivemind-version.json"
SAVED = HOME / "powerworld-hivemind-statusline.json"
SEP = "\x1b[2m | \x1b[0m"
OMC_TAG = re.compile(r"(\x1b\[1m\[OMC#[^\]]*\]\x1b\[0m)")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def tag():
    version = lambda v: tuple(int(p) for p in str(v).split(".") if p.isdigit())
    local = read_json(ROOT / ".claude-plugin" / "plugin.json").get("version", "?")
    latest = read_json(VERSION_CACHE).get("latest", "")
    out = f"\x1b[1m[PWHM#{local}]\x1b[0m"
    if latest and version(latest) > version(local):
        out += f" \x1b[33m↑{latest} available\x1b[0m"
    return out


def previous(data):
    command = read_json(SAVED).get("previous")
    if not command:
        return ""
    try:
        r = subprocess.run(command, shell=True, input=data, capture_output=True, timeout=5)
        return r.stdout.decode("utf-8", "replace").rstrip("\n")
    except (OSError, subprocess.SubprocessError):
        return ""


def main():
    data = sys.stdin.buffer.read()
    t, prev = tag(), previous(data)
    if OMC_TAG.search(prev):
        out = OMC_TAG.sub(lambda m: m.group(1) + SEP + t, prev, count=1)
    else:
        out = t + SEP + prev if prev else t
    sys.stdout.buffer.write(out.encode("utf-8"))


if __name__ == "__main__":
    main()
