# Flow Atelier plugin marketplace

Three independently installable Claude Code plugins for Flow Atelier.

| Plugin | Included skills | Purpose |
|---|---|---|
| `flow-atelier` | `flow-atelier`, `claude-via-atelier` | Understand Atelier; author, run and debug conduits; configure schedules, harnesses and packages; consult Claude through Atelier |
| `autonomous-projects` | `autonomous-projects` | Operate the autonomous-projects conduit, project board, proposal counts and approved-task workflow |
| `automatic-goal` | `automatic-goal` | Run goal exploration in any supported Git project: Codex proposes, Claude Code implements, Codex reviews; preserve shared local decisions |

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
remaining-usage thresholds and shared decision history. Installing its plugin does
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
    skills/automatic-goal/SKILL.md
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
