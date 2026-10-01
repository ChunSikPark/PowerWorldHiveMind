---
description: Seeded - three renewables lack a PFW model; the time step still runs.
tags: [case-auditor]
runs: 3
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

Will a time step work on Hawaii40_base.pwb? I mostly care about the wind and solar. PowerWorld isn't on this machine, but I already ran the case audit on it: the output is findings.md and findings.json in the fixtures folder you can read.
