# PowerWorldHiveMind

<p align="center">
  <img src="assets/juiced.jpg" alt="A juiced-up pixel-art agent with glowing red eyes" width="220">
</p>

<p align="center"><strong>Your agent on PowerWorldHiveMind.</strong> Version 0.4.0</p>

<p align="center"><a href="https://chunsikpark.github.io/PowerWorldHiveMind/"><strong>Open the site</strong></a>: pick a topic, read only that part, and watch the knowledge graph grow.</p>

### Tired of babysitting your coding agent?

Tired of explaining, again, that `SaveCase` silently does nothing and that a filtered
write changes nothing at all?

**PowerWorldHiveMind juices up your agent.** Drop it in, and your assistant stops guessing
at PowerWorld and starts knowing it, including the failures that never raise an exception
and quietly hand you a wrong answer. You give it a case, it gives you the analysis, and you
stop having to be the documentation.

**19 of 23 right, against 6 for the same assistant without it, marked blind.**
[See the benchmark](BENCHMARK.md).

## Install

Paste this sentence into Claude Code (desktop app or CLI):

```
Install the PowerWorld knowledge base: git clone https://github.com/ChunSikPark/PowerWorldHiveMind ~/.claude/skills/powerworld-hivemind
```

Then run `/reload-plugins`, then `/powerworld-hivemind:powerworld-setup`. The setup installs
the Python packages and checks that this machine can drive PowerWorld, SimAuto licence
included. That's it.

When a newer version is published, Claude tells you at the start of a session and offers to
update. To check, the kit reads one version number from GitHub at most once a day and changes
nothing on your machine. Set `PWHM_NO_UPDATE_CHECK=1` to turn it off.

**Check it worked:** ask what `pw.esa.SaveCase("out.pwb")` does. "Silently writes no file"
means the kit loaded.

- **Codex:** `codex plugin marketplace add ChunSikPark/PowerWorldHiveMind`, then install
  **powerworld-hivemind** from `/plugins`. Not yet tested on a released Codex build.
- **Anything else:** clone the repo, `pip install esapp TeamOverbyeWeather`, start your agent
  in the folder, and tell it `Read AGENTS.md and run the preflight.`
- **Never used Claude Code or Python?** [GETTING-STARTED.md](GETTING-STARTED.md) takes you
  from nothing in six steps, about fifteen minutes.

You need Windows, PowerWorld Simulator, and the SimAuto add-on, which is licensed
separately. The agent can also drive Simulator through `.aux` files dropped in a watched
folder, and read PowerWorld's own message log for each one:
[methods/aux-file-mode.md](methods/aux-file-mode.md).

## What's new in 0.4

- **An agent team** that audits a case, runs studies with your settings, compares designs on
  a map, and watches long runs. Each role is written up in [docs/agents](docs/agents/README.md),
  and the site lets you [watch each one handle a request](https://chunsikpark.github.io/PowerWorldHiveMind/#agents).
- **Answers as pages:** [Design Compare](docs/agents/pages/design-compare.html) for designs,
  [Run Watch](docs/agents/pages/run-watch.html) for long runs, and a swimlane picture of every
  plan before you approve it.
- **Study references:** every study option object and SCRIPT command in Simulator 25, and
  which settings are traps.

Full list in [CHANGELOG.md](CHANGELOG.md).

## Where to go next

| You want | Read |
|---|---|
| The whole kit, by topic | [index.md](index.md) |
| Worked runs on a 37-bus case, failures included | [demos/start-here.md](demos/start-here.md) |
| How it scored, with and without the kit | [BENCHMARK.md](BENCHMARK.md) |
| The agent team and its rules | [docs/agents/README.md](docs/agents/README.md) |
| To file what you worked out as a new page | say *"write that up as a page"*, or [skills/knowledge-base-page/SKILL.md](skills/knowledge-base-page/SKILL.md) |
| To see the pages as a graph offline | open the folder as an [Obsidian](https://obsidian.md) vault and press Ctrl/Cmd+G |
| You are an agent | [AGENTS.md](AGENTS.md) |

<details>
<summary>Which instruction file each agent loads</summary>

On the plugin route, Claude Code loads the four skills under `skills/`, the
`schema-librarian` agent, and the two commands. It does not load `CLAUDE.md` or `AGENTS.md`
from a plugin; `skills/powerworld/SKILL.md` carries the rules and points at the pages.

On the manual route:

| Your agent | Loads | Shipped as |
|---|---|---|
| Codex, Cursor, GitHub Copilot, Windsurf | `AGENTS.md` | the file itself |
| Claude Code | `CLAUDE.md` | a one-line `@AGENTS.md` import |
| Gemini CLI | `GEMINI.md` | a generated copy of `AGENTS.md` |

`GEMINI.md` is generated, so edit `AGENTS.md` instead. Checked against each vendor's docs on
2026-09-09, not smoke-tested on each client.

</details>

## Credits and contributing

Built on [`esapp` (ESA++)](https://github.com/lukelowry/ESApp), the Apache-2.0 PowerWorld
SimAuto wrapper from Texas A&M, and
[`TeamOverbyeWeather`](https://pypi.org/project/TeamOverbyeWeather/). A bug in the package
goes to [esapp](https://github.com/lukelowry/ESApp). A page here that is wrong or missing
goes in an issue here, naming the page. Every page exists because someone lost time to the
thing it documents.

PowerWorld Simulator is commercial software of PowerWorld Corporation. This is an
independent knowledge base and is not affiliated with or endorsed by them.
