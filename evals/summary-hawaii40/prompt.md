---
description: Summary mode on a clean public case (live audit, path-scrubbed).
tags: [case-auditor]
runs: 3
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

Give me a summary of Hawaii40_base.pwb - what's in it, and is it sane? PowerWorld isn't on this machine, but I already ran the case audit on it: the output is findings.md and findings.json in the fixtures folder you can read.
