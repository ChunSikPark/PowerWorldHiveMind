# Benchmark

Does this kit actually make an agent better at PowerWorld? Measured, not asserted.

**74 agent sessions across two runs.** Both bars were registered and committed *before* any
agent ran, and both are reported in full — including the gate the kit failed.

---

## The headline

An agent answered 16 PowerWorld automation questions twice: once with this kit, once with
nothing. Same model, same questions, no shared context.

```
                 correct   partial   wrong
  with the kit   ████████████████  16      ·        ·
  no kit          ████             4       ██████ 6   ██████ 6
```

| | with the kit | no kit |
|---|---:|---:|
| **correct** | **16 / 16** | 4 / 16 |
| partial | 0 | 6 |
| wrong | 0 | **6** |

**A swing of +12 out of 16.**

The control arm is the part worth dwelling on. It never once said *"I don't know"* — it
self-reported confidence on **16 of 16** while scoring 4. Its six wrong answers were all the
*silent* kind, the sort PowerWorld accepts without complaint:

- multiplied `Gen.TSH` by `GenMVABase` (it is already on a 100 MVA system base — ~13x too high on a large unit)
- wrote `BranchDeviceType` directly (it is derived and read-only; the write is a no-op)
- ranked every violation on one polarity (`Bus Low Volts` is worse when *lower*)
- wrote a `LimitSet` partial row (`SetData` needs the entire field row or it errors)
- hand-wrote `CONTINGENCY` blocks (inventing labels PowerWorld would not use)

None of those raise an exception. That is the failure mode this kit exists to prevent, and
the 12-question gap is the measurement of it.

---

## Scorecard

Eight gates, all registered in advance.

| Gate | Bar | Result | |
|---|---|---:|:--|
| names the page it followed | >= 14/16 | **16/16** | pass |
| states the documented gotcha | >= 13/16 | **16/16** | pass |
| does not claim ignorance on a covered topic | <= 1/16 | **0/16** | pass |
| **says so when nothing covers it** | **>= 5/6** | **4/6** | **FAIL** |
| cites no page that does not exist | 0 | **0 / 43 citations** | pass |
| obeys the silent-failure code rules | >= 4/5 | **4/5** | pass |
| reads only the kit, nothing else | 0 | **0 / 38 agents** | pass |
| beats the no-kit control | >= +5/16 | **+12** | pass |

**Seven of eight. One miss is a miss, so the run is recorded as a failure.** What that gate
found is below.

---

## The limitation it found

The kit promises, in `AGENTS.md`: *"When no page covers it, say so out loud."* That promise
had never been tested. It holds when coverage is genuinely zero — **all four** topics the kit
does not mention at all were correctly reported as absent.

It broke on the *partial* case. Asked whether `CTGSkip` or `Delete` shrinks a contingency
set, four independent agents split **two right, two wrong** — a coin flip. The two wrong ones
confidently recommended the wrong command, one describing the result as *"a shrunk,
reversible active set"* when nothing is removed from the case.

The cause was structural. `CTGSkip` appeared in three kit pages **as a field being written,
and nowhere with its meaning explained.** The agent recognised a familiar identifier and
stopped searching.

> **A mentioned-but-unexplained identifier is worse than an absent one.** It ends the search
> while supplying nothing. Absence is safe; half-coverage is not.

**Fixed and verified.** `methods/reducing-a-contingency-set.md` was added, and the same
question re-run four times against the published kit:

| | before | after |
|---|---:|---:|
| correct mechanism | 2/4 | **4/4** |
| recommends the right command | 1/4 | **4/4** |
| notes it is destructive | 1/4 | **4/4** |
| gets the ordering constraint | 0/4 | **4/4** |

---

## Second run: the reference layer

The kit tabulates ~198 SCRIPT commands, and **168 of them appear nowhere else in it**. A
second run of 14 questions tested whether that layer is actually reachable.

| Class | What it measures | Result |
|---|---|---:|
| **R** — the answer exists only in `references/` | names the correct command | **6 / 7** |
| **T** — declared out of scope, but the command is listed | gives *both* the command and the boundary | **3 / 3** |
| **N** — genuinely not covered | says so | **4 / 4** |

The reference layer is read, and read well. A second, larger private knowledge base answering
the same questions scored **5/7** and **0/3** on the first two classes — the difference traced
to a single routing line in `AGENTS.md` telling the agent where to look up a command whose
name it does not know.

**The honest limitation this exposed:** the kit's command reference deliberately does not
reproduce argument syntax. Agents find the right command and then correctly report they
cannot write working code with it. One put it precisely:

> *"coverage at the 'which command exists' level, not the 'how to use it' level."*

So on three of seven Class R questions the agent named the right command and still marked the
topic uncovered. That is not bluffing — it is the kit being honest about a real ceiling.

One question defeated **both** knowledge bases: *"reduce this case to an equivalent."* The
command `Equivalence` is listed in both, and neither agent found it. A pure vocabulary miss.

---

## What this does not establish

- **One model, one arm per question.** n = 16 and n = 14. A gate at n = 7 moves on one answer.
- **No code was executed against PowerWorld.** Code was scored against the documented
  silent-failure rules — *"would this have failed quietly"*, not *"did this run"*.
- **The questions were model-drafted from the source the kit was cut from, then reviewed.**
  That review did not catch everything: **5 of 36 ground-truth rows were wrong**, every one of
  them in the answer key rather than in an agent's answer. Where key and agent disagreed, the
  agent was more often right. Any benchmark whose key is written by the same kind of system
  being tested carries this, and it is stated here rather than discovered later.
- **The kit failed its own registered bar.** The fix is verified on the specific defect; the
  gate has not been re-measured, because the question that failed is now covered and can no
  longer test absence.

---

## Reproducing it

Every artefact — the pre-registered bars, the questions, the answer key with its
pre-run hash, all 74 answers, and the scoring scripts — is retained outside this repository.
The method is worth more than the numbers:

1. **Register the bar before running.** Commit it. Do not renegotiate after seeing results.
2. **Seal the answer key by hash** and verify it byte-for-byte afterwards.
3. **Run a no-knowledge control arm.** Without it, a score cannot be attributed to the kit.
4. **Score blind** to which arm produced which answer.
5. **Plant a calibration pair** — one correct answer worded to avoid every keyword, one
   confident inversion. A scorer that misses either is not a scorer.
6. **Positive-control every guard.** A check that has only ever returned "clean" has not been
   tested. The contamination oracle here was run against a planted violation first.
