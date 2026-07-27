# flow-atelier-skills

Agent skills for [flow-atelier](https://github.com/Andesprit/flow-atelier), the
local-first YAML workflow runner whose steps are shell commands, AI coding
agents, nested conduits, and human approval gates.

| Skill | Covers |
|---|---|
| **flow-atelier** | Authoring `conduit.yaml`, the full `atelier` CLI, harnesses and the ACP registry, scheduling, packages, the HTTP/WS server, and troubleshooting |
| **autonomous-projects** | Setting up, running, tuning and debugging the [autonomous-projects](https://github.com/Andesprit/autonomous-projects) package: the tick bot that proposes ideas and code reviews into a repo's board and implements approved tasks behind a two-agent review gate |

Both are written for the operator: what to run, in what order, what each failure
means, and what to do about it. Deep material lives in each skill's
`references/` and is read on demand rather than loaded up front.

## Install

### As a Claude Code plugin (both skills)

```
/plugin marketplace add Andesprit/flow-atelier-skills
/plugin install flow-atelier-skills@flow-atelier-skills
```

### With the `skills` CLI (pick either or both)

```bash
npx skills add Andesprit/flow-atelier-skills
```

This works for any agent the CLI supports (Claude Code, Codex, Cursor, opencode,
Gemini CLI, Copilot and others), not just Claude Code.

### By hand

Copy the skill folder you want into `~/.claude/skills/` or a project's
`.claude/skills/`:

```bash
git clone https://github.com/Andesprit/flow-atelier-skills.git
cp -R flow-atelier-skills/skills/flow-atelier ~/.claude/skills/
```

## Layout

```
.claude-plugin/
  marketplace.json      the Claude Code marketplace manifest
  plugin.json           the plugin manifest
skills/
  flow-atelier/
    SKILL.md
    references/         conduit-yaml, cli, harnesses, scheduling,
                        packages, serve-and-api, troubleshooting
  autonomous-projects/
    SKILL.md
    references/         architecture, troubleshooting
```

`skills/<name>/SKILL.md` is the path both installers resolve: the `skills` CLI
discovers skills there, and the marketplace plugin sources `./`, so one tree
serves both without duplication.

## License

MIT - see [LICENSE](LICENSE).
