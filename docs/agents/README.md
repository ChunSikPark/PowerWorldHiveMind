# Agent drafts

These are the agent definitions for the roles in
`docs/superpowers/specs/2026-09-28-power-system-agents-design.md` whose engines are **not built
yet**. They live here, not in `agents/`, because Claude Code loads every file in a plugin's
`agents/` folder on install: a draft there would be offered to users and would improvise instead
of running an engine.

| draft | role | depends on | ships in |
|---|---|---|---|
| [case-auditor.md](case-auditor.md) | "is this case sane, and can it run study X?" | `skills/case-audit/` engine | Plan 2 |
| [study-runner.md](study-runner.md) | translate preferences into settings, run studies exactly, summarise | `skills/study-runner/` engine | Plan 3 |
| [network-visualizer.md](network-visualizer.md) | map the network around a site, measure the engineer's design and its own challengers on identical settings, compare side by side | the `violation-map` engine (extended), the study-runner engine | Plan 4 |

The network-visualizer replaced a planned fix-reviewer on 2026-09-28: its full-N-1, same-settings
check now happens inside every design comparison.

Live already: [`agents/schema-librarian.md`](../../agents/schema-librarian.md) (Plan 1).

**Rule for each plan:** its last task moves the draft into `agents/` — only after the engine's
tests pass — and re-checks discovery with `claude --plugin-dir <kit> plugin details powerworld-hivemind`.
Edit a draft freely until then; the plan that builds the engine treats the draft as its brief for
the agent file.

**One constraint every draft respects:** a subagent cannot start another subagent. So agents call
each other's **engines or CLIs**, never each other: the study-runner uses the schema-lookup CLI, and
the network-visualizer runs the `violation-map` and study-runner engines directly.
