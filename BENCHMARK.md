# Benchmark

**This kit is worth having for two things: PowerWorld behaviour that fails without raising an
error, and knowing when to stop. For looking up a command name, PowerWorld's own
documentation beats it — a model with web search scored 7 out of 7 there against this kit's
6.**

130 agent runs across four setups. Thresholds written down and committed before any of them
started.

![Where the kit wins and where it doesn't](assets/headline.svg)

---

## The failures that do not raise an error

Sixteen questions about PowerWorld behaviour that returns a wrong answer quietly. The same
model answered each one three ways.

| | correct | partial | wrong |
|---|---:|---:|---:|
| **With the kit** | **16** | 0 | 0 |
| Web search, no kit | 4 | 5 | 7 |
| Model memory, no kit, no web | 4 | 6 | 6 |

**Web search scored the same as answering from memory** — 4 either way — while taking about
three times as long and reading seven times as many tokens. On this kind of question a
browser bought nothing.

It is not that web search failed to find anything. It found plenty, cited it, and was wrong:

| Question | What web search answered, with sources | What is actually true |
|---|---|---|
| tie-line violations vanish under an area filter | your filter is set to require both ends | `AreaNum` reads `0` on a tie-line, so the filter drops it |
| sum generator inertia | H times MVA base | `TSH` is already on a 100 MVA base; multiplying is wrong |
| convert lines to transformers | not possible outside the GUI | scriptable, via `LineXFMR` and `ChangeParametersMultipleElement` |
| sort violations worst-first | sort by Percent descending, per the help page | low-voltage violations sort backwards that way |
| parallelise a slow contingency run | use the distributed-computing add-on | it never spawns workers here and silently runs serial |
| build a contingency aux file | hand-write `DATA (CTG, ...)` blocks | hand-written labels do not match the ones PowerWorld generates |

The sorting one ships a backwards priority list. The transformer one stops the work by
declaring it impossible. The parallel one sends you to buy an add-on that reports success and
does nothing.

The model without any kit never once said it did not know. It claimed confidence on all 16
and got 4.

---

## Looking up a command: use the manual instead

Seven questions whose answer is a PowerWorld SCRIPT command name.

| | named the right command |
|---|---:|
| **Web search** | **7 of 7** |
| With the kit | 6 of 7 |
| A large private wiki | 5 of 7 |
| Model memory only | 4 of 7 |

Web search also returned argument syntax this kit deliberately does not publish:

```
SaveYbusInMatlabFormat("filename", IncludeVoltages)
RenumberBuses(NumCI)
WeatherPWWFileCombine2("source1", "source2", "destination")
WeatherPWWFileGeoReduce("source", "destination", minLat, maxLat, minLon, maxLon)
```

The kit's command reference lists names and purposes and sends you to Simulator's own
*Auxiliary File Format* manual for syntax, because that manual is PowerWorld's copyright. The
consequence is real: on three of these seven the kit named the correct command and still
reported the question uncovered, because it could not supply a signature.

**If your question is "what is this command called", read the manual. This kit adds nothing
there.**

---

## Knowing when to stop

![Does it say so when it cannot answer](assets/boundary.svg)

Ten questions had no answer available in the kit. The correct response is to say so.

| | declined |
|---|---:|
| **With the kit** | **8 of 10** |
| Web search | 1 of 10 |
| Model memory only | 0 of 10 |

Neither the bare model nor web search ever declined. Asked how to size a transformer against
the flow it will carry — a question containing a real trap, since the transformer's own
impedance changes that flow — web search produced a confident methodology assembled from
HVAC-vendor blog posts.

**The catch, which the chart shows rather than hides:** three of those ten topics *are*
documented publicly. Web search returned correct, sourced procedures for all three, including
that integrated topology processing requires a separately licensed add-on. On those, the kit
said "I don't cover this" while a browser would have answered.

So five of the kit's eight declines are the behaviour you want. Three are the kit declining
something you could have looked up.

---

## What it costs

![Cost against accuracy](assets/cost.svg)

Measured over the eight hardest questions: the kit took 4.6 minutes and 5.8 million tokens
for 8 right. Web search took 8.6 minutes and 8.5 million tokens for 1. Memory alone took 2.8
minutes and 1.2 million tokens for 0.

The kit is roughly twice the wall-clock and ten times the cache reads of answering from
memory. Whether that is worth it is your call; the numbers are here so you can make it.

---

## Where the kit failed its own threshold

Eight checks, all registered before the run. Seven passed.

| Check | Threshold | Result | |
|---|---|---:|:--|
| names the page it followed | 14 of 16 | 16 | pass |
| states the documented trap | 13 of 16 | 16 | pass |
| does not claim ignorance on something covered | at most 1 | 0 | pass |
| **says so when nothing covers the question** | **5 of 6** | **4** | **fail** |
| never cites a page that does not exist | 0 | 0 of 43 citations | pass |
| follows the kit's own code rules | 4 of 5 | 4 | pass |
| reads only the kit | 0 breaches | 0 of 38 agents | pass |
| beats the no-kit model | +5 of 16 | +12 | pass |

The failure: asked whether `CTGSkip` or `Delete` shrinks a contingency set, four agents split
two right and two wrong. `CTGSkip` appeared in three pages as a field being written and
nowhere with an explanation of what it does, so an agent found the word, assumed the topic was
covered, and stopped searching.

A term the kit half-mentions is worse than one it never mentions: it ends the search without
answering anything.

Fixed by adding `methods/reducing-a-contingency-set.md`, then re-run four times against the
published kit:

| | before | after |
|---|---:|---:|
| explains the mechanism correctly | 2 of 4 | 4 of 4 |
| recommends the right command | 1 of 4 | 4 of 4 |
| warns that it is destructive | 1 of 4 | 4 of 4 |
| gets the ordering right | 0 of 4 | 4 of 4 |

---

## What this does not tell you

- **One model, one attempt per question.** Between 4 and 16 questions per measurement. A
  number based on 7 questions moves on a single answer.
- **No code was run against PowerWorld.** Code was checked against the documented traps —
  whether it would have failed quietly, not whether it executed.
- **The answer key had errors and they all pointed one way.** Five entries were wrong, a
  results extractor silently replaced 57 of 130 answers with placeholder text, and two scoring
  keys missed commands the answers plainly contained. **Every one of those flattered this
  kit.** Each was caught by reading an answer that contradicted its own score, never by a
  script. An earlier version of this page reported web search at 1 of 8 and did not mention
  that it had beaten the kit at command lookup; this version corrects both.
- **The kit failed its own threshold**, and that check has not been re-run, because the
  question that failed is now covered and can no longer test whether the kit admits ignorance.

---

## Running it yourself

The thresholds, questions, answer key with its pre-run hash, all answers and the scoring
scripts are kept outside this repository. The method matters more than the numbers:

1. Write the thresholds down and commit them before running anything. Do not adjust them
   afterwards.
2. Hash the answer key before the run, check it after.
3. Run a control with no knowledge base. Without one you cannot tell whether the kit did
   anything.
4. Hide which setup produced which answer from whoever scores it.
5. Plant two fake answers in the scoring set: one correct but avoiding every keyword, one
   confidently backwards. If the scorer misses either, throw the scores out.
6. Test every check by feeding it something that should fail. A check that has only ever
   reported "clean" has not been tested.
7. **Read the answers.** Every error found in this benchmark came from a human-legible answer
   disagreeing with a machine-generated score, and never the other way round.
