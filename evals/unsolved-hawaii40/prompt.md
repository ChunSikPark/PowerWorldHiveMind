---
description: Seeded - the AC power flow does not solve; nothing is READY.
tags: [case-auditor]
runs: 3
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

Is Hawaii40_base.pwb ready for a time step? PowerWorld isn't on this machine, but I already ran the case audit on it: the output is findings.md and findings.json in the fixtures folder you can read.
