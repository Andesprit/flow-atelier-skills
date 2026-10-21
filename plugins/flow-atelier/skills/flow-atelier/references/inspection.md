# Inspect an existing workflow

Optional. Use it before running a workflow you did not write, or when a run says
something you did not expect: one command answers which file `atelier run <name>`
would use, which inputs it needs, which tools its top-level tasks use, and
whether the definition is valid. It runs no workflow and no agent. The first run does not
need it.

## Run it

The script sits beside this skill: `scripts/inspect_workflow.py` in the folder
that holds this skill's `SKILL.md` (in this repository,
`plugins/flow-atelier/skills/flow-atelier/scripts/inspect_workflow.py`). It needs
only `python3` and the `atelier` CLI 0.12.0 or newer.

```bash
python3 <skill-dir>/scripts/inspect_workflow.py <project-path> <conduit>          # for a person
python3 <skill-dir>/scripts/inspect_workflow.py <project-path> <conduit> --json   # for an agent
```

`<project-path>` is the folder you would run `atelier` from. Each `atelier` call
is stopped after `--timeout` seconds (default 60). One inspection can take tens
of seconds while the CLI starts.

## Read the report

```text
valid  [project]  /repo/.atelier/conduits/valid/conduit.yaml
status:      valid definition (inspected, not run)
inputs:      required: name; accepted: name
tasks:       1: greet (tool:bash)
next:        cd /repo && atelier plan valid
not checked: the workflow was not run; input values are not resolved; ...
```

| Exit | `status` | Meaning |
|---|---|---|
| 0 | `valid` | `atelier check` passed and the details were read. It is a definition check only. |
| 1 | `invalid` | `atelier check` rejected the definition. `path` and `error` say which file and line to fix. |
| 2 | `not_inspectable` | Nothing was concluded. `error` says why, `next` says what to check. |
| 64 | (none) | Wrong arguments. |

The `[project]` or `[global]` label is the copy a run uses. A project conduit
replaces a global one with the same name even when the project copy is broken;
the report then says `invalid` for the project file and never falls back to the
global copy.

The JSON object has `conduit`, `status`, `source`, `path`, `required_inputs`,
`accepted_inputs`, `tools` (`task` and `tool` per top-level task), `error`,
`next` and `not_checked`. Unknown fields stay `null`. Prompts and other task
settings are not included; use `atelier show <name>` to read the whole file.

`next` is a suggestion. The script never runs it. A valid workflow gets
`atelier plan <name>`, plus `atelier check <name> --recursive` when it calls other
workflows.

## What it does not check

It does not run the workflow, resolve the input values you would pass, validate
nested `tool:conduit` children, start or log in agents, predict cost, or prove a
run will succeed. Use `atelier check <name> --recursive` for children and
`atelier harness check <name>` for an agent.

## What it runs

Only `atelier check --json <conduit>` and, if that passes, `atelier show --json
<conduit>`, from `<project-path>`, with `ATELIER_NO_UPDATE_CHECK=1` and no
bytecode writes. On timeout it stops the whole process group it started
(POSIX; on other systems only the direct child is stopped). No agent, workflow,
package, scheduler, server or network command is part of it.

The `atelier` CLI creates its directories when they are missing, even for
`check`. So the script first looks for `<atelier dir>/conduits`, `flows` and
`schedules` and `<global dir>/conduits`. If one is missing or unreadable, it
calls nothing and reports `not_inspectable` with the exact paths. Creating them
is your choice; the report prints the `mkdir -p` command that would do it.

The directories follow the CLI settings: `ATELIER_ATELIER_DIR` and
`ATELIER_GLOBAL_ATELIER_DIR` from the environment, relative to the project path,
or `<project>/.atelier` and `~/.atelier`. If the project's `.env` sets one of
those two paths, the script does not guess its value: it reports
`not_inspectable` and asks you to export the setting or use `atelier check`
directly. Other `.env` contents are not read out.

If the definition changes, or resolves to a different file, between the `check`
and `show` calls, the report says `not_inspectable` instead of mixing two files.
