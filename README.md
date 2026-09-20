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
atelier add Andesprit/autonomous-projects --project
atelier add Andesprit/automatic-goal --project
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
a default 20% finishing reserve, bounded recovery and a final demonstration. Install both
updated conduits together after finishing or inspecting existing runs, preserving local edits.
Do not resume legacy KEEP/DISCARD flows with the new workflow; their history remains readable.
Installing this plugin supplies instructions, not the executable reader or web assets.
