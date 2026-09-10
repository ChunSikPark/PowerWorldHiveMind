# Benchmark — PowerWorldHiveMind v0.2.0

If you are about to drive PowerWorld from Python with an AI assistant, this page tells you
what PowerWorldHiveMind changes, what it does not, and what it costs.

Measured against release **v0.2.0**. Later releases are benchmarked the same way, so the
numbers below can be compared across versions.

**It solved 19 of 23 questions against 6 for a capable assistant with a web
browser.** On the failures PowerWorld does not report as failures it scored **15 of 16**
against **4 of 16**, and that class of question is almost the whole gap. On looking up a command name it is weaker — 4 of 7 — and
slower and more expensive than a web search for the same job.

## What was compared

| Setup | What that means |
|---|---|
| **HiveMind** | the assistant has this repository on disk, and nothing else |
| **A fresh assistant + web** | a capable coding assistant told nothing about PowerWorld, with no documentation and no files, free to search the open web |

Both answered the same 23 questions. Every answer was then marked right or wrong
by a grader that saw a reference answer and the candidates **without knowing which setup
wrote which**. Two answers were planted in the pile to test the grader: one correct but
worded to avoid every obvious keyword, one fluent and confidently backwards. It caught
both. Had it missed either, every score here would have been thrown away.

**Right or wrong only — there is no partial credit.** An earlier version of this benchmark
used a three-level scale, and the middle level is where two of five scoring errors hid: a
wrong answer marked *partly right* reads as a judgement call rather than a mistake, so
nobody re-checks it.

![Where PowerWorldHiveMind helps and where it does not](assets/headline.svg)

---

## 1. Questions where PowerWorld lies to you

Simulator accepts the call, reports success, and returns something wrong. Nothing raises an
error. These are the ones that cost you a day.

| Q | What was asked about | HiveMind | Fresh assistant + web |
|---|---|:--:|:--:|
| A01 | Saved a case and no file appeared | ✅ | ❌ |
| A02 | Set MW on only the coal units | ✅ | ❌ |
| A03 | A DC solve hid a short schedule | ✅ | ✅ |
| A04 | Created lines, nothing was created | ✅ | ❌ |
| A05 | Setting the N-1 voltage limits | ✅ | ❌ |
| A06 | Which outage caused which overload | ✅ | ❌ |
| A07 | An area filter hid tie-line problems | ✅ | ❌ |
| A08 | Violations from a case never solved | ✅ | ❌ |
| A09 | Sorting violations worst-first | ❌ | ❌ |
| A10 | One outage per new generator | ✅ | ❌ |
| A11 | Total system inertia | ✅ | ✅ |
| A12 | Reclassifying lines as transformers | ✅ | ❌ |
| A13 | What hourly wind and solar needs first | ✅ | ❌ |
| A14 | Capacity factor from the output file | ✅ | ❌ |
| A15 | It solves in DC — trust it for AC? | ✅ | ✅ |
| A16 | Speeding up a two-hour outage run | ✅ | ✅ |
| | **solved** | **15 of 16** | 4 of 16 |

**This is what the repository is for.** A fresh assistant with the whole open web could
confirm 4 of these 16. Public documentation describes what a command
does; it does not tell you that the call returns success and writes nothing, or that a
filter silently drops every tie-line, or that a field you are summing is already on a
different base than you think.

**A09 defeated both setups** — sorting violations worst-first. Neither the repository nor
the open web produced a correct answer.

---

## 2. Looking up a command: open PowerWorld's manual

| Q | What was asked about | HiveMind | Fresh assistant + web |
|---|---|:--:|:--:|
| R1 | Run a security-constrained OPF | ❌ | ❌ |
| R2 | Export the Ybus for MATLAB | ✅ | ✅ |
| R3 | Renumber the buses | ❌ | ❌ |
| R4 | Built-in LODF screening | ✅ | ❌ |
| R5 | Combine and crop weather files | ❌ | ❌ |
| R6 | Set participation factors | ✅ | ✅ |
| R7 | Reduce a case to an equivalent | ✅ | ❌ |
| | **solved** | **4 of 7** | 2 of 7 |

Neither setup is good at this. HiveMind gets 4 of 7 and spends
**66 searches** doing it, against 23 for the web. This
repository deliberately does not publish argument syntax — the *Auxiliary File Format*
manual is PowerWorld's copyright — so on several of these it names the right command and
still cannot give you a signature to call it with.

---

## 3. What it costs

**Cost here is counted in searches, not tokens.** A search means the same thing in both
setups: the assistant did not know, and went to look. A token does not — the setups read
different amounts of conversation per step, and separately HiveMind searched 8.1 times per
question when asked an ordinary question and 14.3 times when told to give the best answer
it could — 1.8x, from one sentence of instruction.
**Ranking setups by tokens partly ranks the instructions they happened to be given.**

![How many times each setup had to look](assets/hops.svg)

| | Solved | Searches | **Searches per question solved** |
|---|:--:|--:|--:|
| **HiveMind** | **19 of 23** | 146 | **7.7** |
| Fresh assistant + web | 6 of 23 | 71 | 11.8 |

HiveMind searches more in total (146 against 71) and still costs less per question it
actually solves.

Median wall-clock per question: **42 s** with HiveMind, **69 s** for the fresh
assistant searching the web.

The table cells describe what each question was about rather than quoting it; the questions
and grading prompts are not published. Back to [README](README.md).
