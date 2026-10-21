# Flow Atelier plugin marketplace

Three independently installable Claude Code plugins for Flow Atelier.

| Plugin | Included skills | Purpose |
|---|---|---|
| `flow-atelier` | `flow-atelier`, `claude-via-atelier` | Understand Atelier; author, run and debug conduits; configure schedules, harnesses and packages; consult Claude through Atelier |
| `autonomous-projects` | `autonomous-projects` | Operate the autonomous-projects conduit, project board, proposal counts and approved-task workflow |
| `automatic-goal` | `automatic-goal`, `goal-report`, `goal-monitor` | Pursue user outcomes with Codex supervision and review, Claude implementation and repair, and evidence-backed session reports |

These plugins provide agent instructions. They do not install the Atelier CLI,
authenticate agents, install executable conduits, or start runs.

## Install plugins in Claude Code

Register the marketplace once, then install whichever plugins you need:

```text
/plugin marketplace add Andesprit/flow-atelier-skills
/plugin install flow-atelier@flow-atelier-skills
/plugin install autonomous-projects@flow-atelier-skills
/plugin install automatic-goal@flow-atelier-skills
```

Each plugin includes its own skills and references; none requires another plugin.
The marketplace identifier remains `flow-atelier-skills`.

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

Run these separately in the project where you intend to use the conduits:

```bash
atelier install Andesprit/autonomous-projects --project
atelier install Andesprit/automatic-goal --project
```

The automatic-goal skill explains dedicated worktree setup, required environment,
outcome planning, time and usage reserves, bounded repair and shared decision history. Installing its plugin does
not authorize or start an autonomous run.

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
