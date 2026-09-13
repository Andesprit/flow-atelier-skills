---
name: flow-atelier
description: Author, run, debug, schedule, share and serve flow-atelier conduits - the local-first YAML workflow runner whose steps are shell commands, AI coding agents (Claude Code, Codex, Gemini, opencode, Copilot, Cursor and ~40 more via the ACP registry), nested conduits, and human approval gates. Use when the user mentions flow-atelier, the `atelier` CLI, a conduit or conduit.yaml, a flow or flow_id, `.atelier/`, a harness or `harness:<name>`, `tool:bash` / `tool:hitl` / `tool:conduit`, HITL gates, `depends_on` conditions, repeat/until/while loops, `atelier run/check/plan/serve/schedule/harness/add`, or asks how to write a workflow YAML, wire steps together, loop a step until output matches, gate a step on what a previous step printed, run agents on a timer, or share conduits as a package.
version: 1.0.0
---

# Flow Atelier

A local-first workflow runner. A **conduit** is one YAML file describing a DAG of
steps; steps run shell commands, hand work to AI coding agents, call other
conduits, or pause for a human. Everything is plain files under `.atelier/`.

Source: <https://github.com/Andesprit/flow-atelier>

## Vocabulary

| Term | Meaning |
|---|---|
| **Conduit** | A recipe. One YAML file at `.atelier/conduits/<name>/conduit.yaml` |
| **Task** | One step in that recipe |
| **Flow** | One run of a conduit, saved under `.atelier/flows/<flow_id>/` |
| **Harness** | An AI coding agent a task can hand work to |
| **HITL** | A step that pauses and asks a person a typed question |

Agents run through **your existing login** for that tool. flow-atelier never
sees, stores, or proxies credentials, and installs no agents.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Andesprit/flow-atelier/main/install.sh | bash
```

Prebuilt binaries cover Linux x86_64, macOS arm64, Windows x86_64. Intel Macs are
not supported. Windows uses `irm .../install.ps1 | iex`. With Python 3.13+ and uv:
`uv tool install flow-atelier`.

```bash
atelier init                          # writes .atelier/conduits/hello/
atelier run hello --input name=world
atelier serve                         # visual editor on :8000
```

## Anatomy of a conduit

This one example exercises most of the surface. Every field is optional except
`name`, `description`, `tasks`, and each task's `name` / `description` / `task` /
`tool`.

```yaml
name: deploy_pipeline        # must match the folder name; [A-Za-z0-9_-]
description: Build test deploy
timeout: 3600                # seconds per task (default 3600)
max_concurrency: 3           # parallel tasks within this conduit (default 3)

inputs:
  branch: Branch to deploy               # string shorthand = description
  env: {description: Target, default: staging}   # a default makes it optional

tasks:
  - clone_repo:                          # task names: [A-Za-z0-9_] - NO hyphens
      description: Clone
      task: "git clone -b {{inputs.branch}} $REPO /tmp/build"
      tool: tool:bash
      depends_on: []

  - run_tests:
      description: Run tests
      task: "cd /tmp/build && make test"
      tool: tool:bash
      depends_on: [clone_repo]
      repeat: 3                          # loop up to 3 times...
      until: 'output.match(PASS)'        # ...break as soon as output matches
      on_exhaust: fail                   # fail if 3 runs never matched

  - code_review:
      description: AI review
      task: |
        Review /tmp/build/src for security issues.
        End with exactly one of: VERDICT: APPROVE / VERDICT: REJECT
      tool: harness:claude-code
      depends_on: [clone_repo]
      retries: 2
      retry_backoff: 5

  - approve:
      description: human gate
      task: "I need a final confirmation"
      tool: tool:hitl
      depends_on:
        - run_tests
        - 'code_review.output.match(VERDICT:\s*APPROVE)'
      inputs:
        confirm: "Type 'yes' to approve deploy"

  - deploy:
      description: Run the deploy sub-conduit
      task: deploy_to_env                # the conduit name, not a command
      tool: tool:conduit
      depends_on: [approve]
      inputs: {target_env: "{{inputs.env}}"}

  - rollback:
      description: Rollback if review rejected
      tool: tool:bash
      task: "make rollback"
      depends_on:
        - 'code_review.output.not_match(VERDICT:\s*APPROVE)'
```

`approve` and `rollback` are mutually exclusive branches. **An unmet condition
skips a task, it does not fail it** - and everything downstream skips too.

### Tools

| Tool | Runs |
|---|---|
| `tool:bash` | a shell command |
| `tool:hitl` | prompts a human on the terminal for named answers |
| `tool:conduit` | another conduit, as a nested run (`task:` is its name) |
| `harness:<name>` | an AI agent, e.g. `harness:claude-code`, `harness:codex`, `harness:gemini` |

`tool:*` is a closed set. `harness:*` is open - any ACP agent in the registry,
plus anything you register yourself.

### Templating

| Expression | Resolves to |
|---|---|
| `{{inputs.<name>}}` | a conduit input or HITL answer |
| `{{<task>.output}}` | an earlier task's output (must be in `depends_on`) |
| `{{loop.previous}}` | this task's output from its previous iteration |
| `{{loop.history}}` | all prior iterations, numbered |
| `{{conduit_dir}}` | absolute dir of the running conduit - use for helper scripts |

A missing `{{inputs.x}}` **fails** the task immediately. A reference to a skipped
or incomplete task **skips** the referencing task.

## Command map

Every command, grouped. Flags and exact behavior: `references/cli.md`.

```
authoring    init · create · check · plan
running      run [--input --resume --again --show-steps] · stop
inspecting   status · logs · outputs · timing · list conduits · list flows
cleanup      rm · prune
agents       harness list · harness check · harness sync
packages     add · update · remove
scheduling   schedule add|list|remove|run-now · scheduler start|status
server       serve
```

Fastest loop when authoring: `atelier check` (validates, runs nothing) then
`atelier plan <name>` (renders the DAG as waves, marks gates and sinks, runs
nothing), then `atelier run`.

## Where things live

```
.atelier/
  conduits/<name>/conduit.yaml      project conduits (also ~/.atelier/conduits/)
  schedules/<name>.yaml             one file per schedule
  scheduler_state.json              fired-once markers
  flows/<flow_id>/                  <YYYYMMDD>_<uuid8>_<conduit>
    input.yaml  logs.jsonl  progress.json  outputs.yaml
    flows/<child_flow_id>/          nested tool:conduit runs
```

Conduits resolve **project first, then global** (`~/.atelier/conduits/`); a
project conduit silently overrides a global one of the same name. Flows are
always project-local, written under the directory you ran `atelier` from.

## Traps worth knowing up front

- **Task names take no hyphens.** `[A-Za-z0-9_]` only. Conduit names allow them.
  `my-task` is a validation error; `my_task` is fine.
- **A loop that never matches its predicate still completes.** `repeat: 5` with a
  never-matching `until` runs 5 times and succeeds. Add `on_exhaust: fail` when
  exhausting the budget should be an error.
- **`outputs.yaml` keeps only the last iteration** of a looped task. Skipped
  tasks record `null`.
- **A conduit's "output" is its sink tasks** - the ones nothing else depends on.
  That is what a parent `tool:conduit` loop predicate matches against, and it
  sees *every* nested sub-task output of the iteration, firing on any match.
- **Conduits are code.** Running one runs whatever shell commands it contains.
  Read a package before installing it, and pin `--ref` for anything you do not
  control.
- **Flow logs are unredacted.** Terminal output masks credential-shaped values,
  but `.atelier/flows/<id>/` keeps the raw text. Treat it as sensitive.

## References

- `references/conduit-yaml.md` - complete authoring reference: every schema
  field and its validation, the condition DSL, loop semantics and truth tables,
  templating, HITL, nested conduits.
- `references/cli.md` - every command with its flags and behavior.
- `references/harnesses.md` - the ACP registry, listing and checking agents,
  custom agents, interactive mode, env overrides.
- `references/scheduling.md` - schedule file schema, all three modes, the daemon.
- `references/packages.md` - sharing conduits, `atelier-package.yaml`, install
  and update semantics.
- `references/serve-and-api.md` - the HTTP/WS server, endpoints, and the
  security model.
- `references/troubleshooting.md` - failure modes, debugging a flow, recovery.
