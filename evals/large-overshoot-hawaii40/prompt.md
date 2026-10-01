---
description: Seeded - the slack unit 20 MW over its rating; the flows are artifacts.
tags: [case-auditor]
runs: 3
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

Scan Hawaii40_base.pwb for me - anything wrong with it? PowerWorld isn't on this machine, but I already ran the case audit on it: the output is findings.md and findings.json in the fixtures folder you can read.
