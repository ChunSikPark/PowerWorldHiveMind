# Evals for the case-auditor

Eight cases for `claude plugin eval`: two on live audits of the public Hawaii40 and Texas2k
cases, six on seeded copies of Hawaii40 that test the agent's judgment. Each case folder holds
`case.yaml`, `prompt.md`, `graders/` and `fixtures/`. PowerWorld is not in the eval sandbox, so
each `prompt.md` carries the audit inline: the engineer's question, one line saying the audit was
already run, then `fixtures/findings.md` verbatim in a fence. `fixtures/findings.md` and
`findings.json` stay the source of truth: `tools/case-audit-dev/write_prompt.py` writes the
prompt from them, and the suite fails if a prompt no longer embeds its fixture word for word.

The prompt's frontmatter also carries `append_system_prompt`, written by the same tool: eval run 2
showed the main session answering every case itself and never dispatching case-auditor, so it is
told to hand the request and the audit to case-auditor verbatim and relay the reply verbatim. The
engineer's question itself stays plain.

To regenerate a case, write its fixtures (`replay.py` for a seeded case; a live audit, then
`scrub_findings.py`, for a live one), then run `write_prompt.py evals/<case>`.

## What is inferred, and what the first run settled

Three behaviours of the eval sandbox were inferred from its documentation. The first run settled
one; until a run settles the other two, treat a failure that traces to one of them as a harness
question, not an agent defect.

1. **Still inferred: the `Agent` call's input shape.** The `ran-the-case-auditor` grader matches
   `"subagent_type": "...case-auditor"` in the tool input. If the sandbox records the call
   differently, that grader fails while the others pass; fix `input_match` to the shape the trace
   shows.
2. **Settled: where the fixtures reach the agent.** On native Windows `context.add_dirs` is not
   exposed to the agent at all, and `scaffold_script` fails (the eval tool hands a backslash path
   to `/bin/bash`, exit 127). The first run scored 0/8, every case unable to find its fixtures. The
   fixtures are therefore inlined in the prompt, and `case.yaml` holds only `schema_version` and
   `name`.
3. **Still inferred: how faithfully the main session relays the subagent's answer.** The content
   graders read the final answer. If the main session shortens the subagent's reply, a content
   grader can fail for that reason. Record it; do not loosen a grader to make it pass.

Do not commit `evals/results/`.
