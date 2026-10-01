---
description: Seeded - every line has placeholder resistance and no charging.
tags: [case-auditor]
runs: 3
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

Can I trust the power flow on Hawaii40_base.pwb? PowerWorld isn't on this machine, but I already ran the case audit on it: the output is findings.md and findings.json in the fixtures folder you can read.
