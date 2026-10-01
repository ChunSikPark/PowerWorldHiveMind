# Evals for the case-auditor

Eight cases for `claude plugin eval`: two on live audits of the public Hawaii40 and Texas2k
cases, six on seeded copies of Hawaii40 that test the agent's judgment. Each case folder holds
`case.yaml`, `prompt.md`, `graders/` and `fixtures/` (the audit output the agent reads, because
PowerWorld is not in the eval sandbox).

## What is inferred, not documented

Three behaviours of the eval sandbox are inferred from its documentation and have not been
confirmed by a run. Until the first run settles them, treat a failure that traces to one of them
as a harness question, not an agent defect.

1. **The `Agent` call's input shape.** The `ran-the-case-auditor` grader matches
   `"subagent_type": "...case-auditor"` in the tool input. If the sandbox records the call
   differently, that grader fails while the others pass; fix `input_match` to the shape the trace
   shows.
2. **Where the `add_dirs` folder appears to the agent.** The prompts say the audit output is "in
   the fixtures folder". If the agent cannot find it, name the real path in the prompt body.
3. **How faithfully the main session relays the subagent's answer.** The content graders read the
   final answer. If the main session shortens the subagent's reply, a content grader can fail for
   that reason. Record it; do not loosen a grader to make it pass.

Do not commit `evals/results/`.
