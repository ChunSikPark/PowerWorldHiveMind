---
description: Install the Python packages this kit needs and check whether PowerWorld can be driven from this machine
---

# PowerWorld setup

Get this machine ready to run the PowerWorld knowledge base. Two things happen: the Python
packages get installed, and the preflight says whether PowerWorld is drivable at all.

Work through the steps in order and stop at the first one that fails. **Report which step
failed and what it printed.** Do not carry on to the next step hoping it resolves itself,
and do not start writing analysis code afterwards — this command only sets up.

## 1. Find Python

```bash
python --version
```

No Python, or a version below 3.9: stop and tell the user to install it from
[python.org/downloads](https://www.python.org/downloads/), **ticking "Add Python to PATH"
on the first installer screen**. That checkbox is unticked by default and is the single
most common thing to get wrong here. Nothing below works without it.

On Windows, `py --version` is worth trying if `python` is not found — a working Python can
still be missing from `PATH`.

## 2. Install the packages

```bash
python -m pip install --upgrade esapp TeamOverbyeWeather pywin32
```

- `esapp` drives PowerWorld through SimAuto.
- `TeamOverbyeWeather` downloads the `.pww` weather files.
- `pywin32` is the COM bridge esapp calls through. On non-Windows it will not install, and
  that is expected — see step 3.

If pip is missing, `python -m ensurepip --upgrade` first.

## 3. Run the preflight

Call `preflight_machine()` from the script in
`${CLAUDE_PLUGIN_ROOT}/methods/preflight-powerworld.md`. It runs checks 1 to 4 — the
platform, `pywin32`, `esapp`, and the SimAuto COM server — and needs no case file. **Read
that page and use its script**; do not write your own version from memory. Leave check 5
(`preflight_case`) alone: the user has not given you a case yet.

**Report the Simulator build date the preflight prints.** PowerWorld's behaviour shifts
between versions and it shifts silently, so the build date belongs in every session's
opening report. See `${CLAUDE_PLUGIN_ROOT}/concepts/version-requirements.md`.

## 4. Say what the result means

A preflight failure is a fact about the machine, not a bug in the code. Give the user the
plain reading of it:

| What failed | What to tell them |
|---|---|
| Platform is not Windows | SimAuto is a Windows COM server and there is no port. The weather half of the kit still works — `${CLAUDE_PLUGIN_ROOT}/methods/teamoverbyeweather-client.md` |
| `pywin32` or `esapp` missing after step 2 | pip installed into a different interpreter than the one running the preflight. Print `sys.executable` from both and reconcile |
| SimAuto will not start | Usually Simulator is not installed, or is installed but has never been run once as administrator to register its COM server |
| A licence / "not authorized" / add-on error | **The SimAuto add-on is licensed separately from Simulator.** No code change fixes this. They need whoever administers their PowerWorld licence. Simulator's own GUI gives no hint of it — it works fine |

The full failure table, with the exact error strings, is in the preflight page.

## 5. Then stop

Say what passed, what the build date is, and — if it failed — which check and what it
means. Do not begin an analysis. Ask the user what they want to do next; if they have a
case file, `${CLAUDE_PLUGIN_ROOT}/methods/esapp-overview.md` is the next page.
