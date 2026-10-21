# Flow Atelier plugin marketplace

Three independently installable Claude Code plugins for Flow Atelier. They give an
agent instructions. They do not install the Atelier CLI, log in agents, install
executable conduits, or start runs.

## Pick your job

Install only the plugin your job needs. Each skill link has the detailed setup.

| Job | Plugin and skill | Needs | Try this first | You should see |
|---|---|---|---|---|
| Write and run workflows | `flow-atelier`: [flow-atelier](plugins/flow-atelier/skills/flow-atelier/SKILL.md) | plugin, `atelier` CLI. An agent only for agent steps. | In a terminal, follow [first run](plugins/flow-atelier/skills/flow-atelier/references/first-run.md). In Claude: "Write a conduit that runs my tests and stops when they pass." | `hello world` from a shell-only flow; no agent runs. |
| Ask Claude from Codex | `flow-atelier`: [claude-via-atelier](plugins/flow-atelier/skills/claude-via-atelier/SKILL.md) | the skill in Codex (see [other agents](#install-skills-in-other-agents)), `atelier` CLI, a Claude Code login | In a terminal: `atelier harness check claude-code`. Then in Codex: "Ask Claude to review src/ and report problems." | Claude's answer plus Codex's own check. The request is a real Claude run and spends its quota. |
| Let an agent work through an approved task board | `autonomous-projects`: [autonomous-projects](plugins/autonomous-projects/skills/autonomous-projects/SKILL.md) | plugin, CLI, the autonomous-projects package, the separate `agent-skills` plugin, a Claude Code login | In Claude: "Set up autonomous-projects for this repo, but do not run a tick." | Each [setup step](plugins/autonomous-projects/skills/autonomous-projects/SKILL.md#setup-on-a-new-repo) checked and a board to fill in. A tick is a separate, paid request. |
| Pursue an outcome for a fixed time | `automatic-goal`: [automatic-goal](plugins/automatic-goal/skills/automatic-goal/SKILL.md), [goal-report](plugins/automatic-goal/skills/goal-report/SKILL.md), [goal-monitor](plugins/automatic-goal/skills/goal-monitor/SKILL.md) | plugin, CLI 0.12.0+, the automatic-goal package, Claude Code and Codex logins, a dedicated Git worktree | In Claude: "Check whether this repo is ready for a 2-hour automatic goal. Do not start it." | The [prerequisite checks](plugins/automatic-goal/skills/automatic-goal/SKILL.md#prepare-a-project) and what is missing. A run starts only when you ask for one and spends both agents' quota. |

## Install plugins in Claude Code

Inside a Claude Code session, register the marketplace once, then install the
plugin for your job:

```text
/plugin marketplace add Andesprit/flow-atelier-skills
/plugin install flow-atelier@flow-atelier-skills
```

Replace `flow-atelier` with `autonomous-projects` or `automatic-goal` for those jobs.
Each plugin includes its own skills and references; none requires another plugin.
The marketplace identifier remains `flow-atelier-skills`.

Check the install from a terminal:

```bash
claude plugin list                    # the plugin is listed with Status: enabled
claude plugin details flow-atelier    # its skills and projected token cost
```

These commands send no prompt. They read the installed plugin, not an open session.
Start a new Claude Code session after installing, or follow the reload hint that
`/plugin install` prints, before you ask for the job. A skill can also be called by
its full name, for example `/flow-atelier:flow-atelier`.

### Something is missing?

| Symptom | Missing layer | Next check or fix |
|---|---|---|
| Claude does not use the skill | plugin | `claude plugin list` (installed and enabled?), `claude plugin details <plugin>` (skills listed?), then a new session. |
| `command not found: atelier` | CLI | Install it: see [first run](plugins/flow-atelier/skills/flow-atelier/references/first-run.md#1-check-the-cli). |
| `unknown conduit: hello` | project not initialised | `atelier init` in the directory where you run `atelier`. |
| `unknown conduit: goal_loop` or `autonomous-projects` | package not installed in this project | Follow the job's setup link above, then `atelier list conduits`. |
| An agent task cannot start or log in | harness | `atelier harness check <name>`. It sends no prompt. `ready yes` in `atelier list harnesses` does not prove a login. |
| A run failed | conduit or task | `atelier diagnose <flow_id>` first. See [troubleshooting](plugins/flow-atelier/skills/flow-atelier/references/troubleshooting.md#a-run-failed-start-here). |

A successful hello run proves the CLI works. It does not prove an agent login or a
package install.

Optional: to see which file, inputs and tools an existing workflow uses before you
run it, use [inspect an existing workflow](plugins/flow-atelier/skills/flow-atelier/references/inspection.md).
It runs no workflow and no agent.

### Migrating from the old bundled plugin

The former `flow-atelier-skills` plugin is replaced by the three entries above.
Refresh the existing marketplace, install your chosen plugins, then uninstall the
old bundle to avoid duplicate skills:

```text
/plugin marketplace update flow-atelier-skills
/plugin install flow-atelier@flow-atelier-skills
/plugin install autonomous-projects@flow-atelier-skills
/plugin install automatic-goal@flow-atelier-skills
/plugin uninstall flow-atelier-skills@flow-atelier-skills
```

Restart Claude Code after changing plugins if the active session still shows old skills.

## Install skills in other agents

Use the skills CLI against an individual plugin directory, for example:

```bash
npx skills add https://github.com/Andesprit/flow-atelier-skills/tree/main/plugins/automatic-goal
```

Or copy a skill folder from `plugins/<plugin>/skills/<skill>/` into the skill directory
supported by your agent. Keep each skill's references with it.

## Install the executable workflow packages

The board and goal jobs also need an executable package in the project you work on.
These are optional for the other jobs. Use the exact commands in each skill:
[autonomous-projects setup](plugins/autonomous-projects/skills/autonomous-projects/SKILL.md#setup-on-a-new-repo)
and [automatic-goal preparation](plugins/automatic-goal/skills/automatic-goal/SKILL.md#prepare-a-project).
Installing a plugin or a package does not authorize or start an autonomous run.

## Repository layout

```text
.claude-plugin/
  marketplace.json
plugins/
  flow-atelier/
    .claude-plugin/plugin.json
    skills/
      flow-atelier/SKILL.md
      flow-atelier/references/
      claude-via-atelier/SKILL.md
  autonomous-projects/
    .claude-plugin/plugin.json
    skills/autonomous-projects/
      SKILL.md
      references/
  automatic-goal/
    .claude-plugin/plugin.json
    skills/
      automatic-goal/SKILL.md
      goal-report/SKILL.md
      goal-monitor/SKILL.md
```

Plugin sources are relative paths within this repository. Each plugin is self-contained
so installing one copies everything its skills require.

## Validate changes

```bash
claude plugin validate .
claude plugin validate plugins/flow-atelier
claude plugin validate plugins/autonomous-projects
claude plugin validate plugins/automatic-goal
```

Run the maintainer routing suite with Claude Code's `plugin eval` support and an
existing login (Python 3 required):

```bash
python3 evals/run_routing.py --max-cost-usd 8
```

The runner always uses `--no-publish`, `--trust-plugin`, `--ablation none` and
`--runs 1`. It copies all six skills into one temporary `routing` plugin so every
case competes against every skill, approximating installation of all three plugins.
Cases stay outside shipped plugin folders. The 18 cases check skill selection,
three forbidden routes and useful first steps on Atelier 0.12.0; the first-step
judge uses Haiku by default. Results and retained traces go to
`.atelier/routing-evals/<timestamp>/`; use `--output-dir <fresh-directory>` to save
elsewhere, or `--case '<name-glob>'` for a focused rerun. The cost ceiling is checked
before each run, so up to four in-flight runs can exceed it; use `--concurrency 1`
for a tighter bound. The gate requires at least 90% of cases to pass every grader
and every negative case to pass. Partial runs fail. JSON retains each failed grader
and the native eval exit code even when the gate passes. One run per case is a
routing smoke check; repeat runs to investigate variation. These cases propose
commands only and do not prove live agent, scheduler or dashboard execution.

Bump the affected plugin's version when publishing changes. Plugin packaging follows
the [Claude Code marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces).

## License

MIT — see [LICENSE](LICENSE).

## Goal reports and live monitoring

The automatic-goal plugin includes `goal-report` for session retrospectives and `goal-monitor`
for a read-only local dashboard. Reports lead with outcome status, elapsed time, completed
improvements and open work. Each completed change and discarded approach gets a paragraph
covering what, why and how; discarded ideas also explain why they were dropped. Evidence,
validation and technical history remain available below the summary (`report --details`).
The dashboard refreshes saved records every three seconds. Usage is a recorded sample,
not a live provider balance; accepted milestones are not proof of whole-goal completion.

Version 2.0.0 guidance matches the outcome-driven automatic-goal conduits: persistent briefs,
opportunity comparisons, multiple commits per milestone, ACCEPT/REVISE/ABANDON decisions,
a default 10% finishing reserve, bounded recovery and a final demonstration. Install both
updated conduits together after finishing or inspecting existing runs, preserving local edits.
Do not resume legacy KEEP/DISCARD flows with the new workflow; their history remains readable.
Installing this plugin supplies instructions, not the executable reader or web assets.
