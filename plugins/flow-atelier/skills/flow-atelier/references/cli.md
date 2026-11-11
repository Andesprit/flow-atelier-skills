# The `atelier` CLI - every command

Command names and flags below target atelier 0.14.0.

Global: `atelier --version`, `atelier --install-completion`,
`atelier --show-completion`.

Most inspection commands take a **flow id or any unique prefix**, so
`atelier status 20260727_0eb` works.

## Authoring

```bash
atelier init                                   # scaffold .atelier/ + a hello conduit
atelier create <name> [-d/--description TEXT]  # scaffold one empty conduit
atelier check [<conduit>]                      # validate; omit the name to check all
atelier plan <conduit>                         # render the DAG as waves; runs nothing
atelier show <conduit> [--json]                # read the definition that would run
atelier schema                                # print this version's JSON Schema
```

`init` writes `.atelier/conduits/hello/conduit.yaml`, a one-task bash conduit
that works before any AI tool is installed.

`check` validates schema, dependency syntax, loop predicates and template
references, and lists each conduit's required inputs. It runs no tasks.

`plan` validates first (failing identically to `check`), then renders waves with
plain and conditional edges, loop predicates, sinks, short-circuit gates, and
each agent task's permission level. Read-only - no flow is created.

`show` writes the exact YAML to stdout and its source/path to stderr. Project
conduits shadow global ones, including when the project copy is broken.
`--json` instead returns source, path, normalized definition and declared input
names. It does not validate every template; use `check` for readiness.

For editor completion, save the schema:

```bash
atelier schema > .atelier/conduit.schema.json
```

For a conduit at `.atelier/conduits/<name>/conduit.yaml`, add
`# yaml-language-server: $schema=../../conduit.schema.json` as its first line.
Regenerate after upgrading Atelier. Schema validation checks structure;
`atelier check` still checks dependency references, loop predicates and agents.

### Compose an agent workflow

```bash
atelier compose review --step "claude-code=Draft a solution" --step "codex=Review it"
atelier compose panel --parallel --step "claude-code=Review correctness" \
  --step "codex=Review tests" --synthesize "claude-code=Combine the reviews"
```

At least two repeatable `--step` / `-s HARNESS=PROMPT` options are required.
Steps form a chain by default. `--parallel` gives each only the brief;
`--synthesize HARNESS=PROMPT` requires `--parallel` and adds a final task reading
all results. `--description` / `-d TEXT` sets the conduit description.

Harness names come from `atelier list harnesses`, optionally with `:<model>` or
`:<model>:<effort>`. Prompts preserve equals signs after the first `=`, but must
not contain `{{...}}`. Compose writes ordinary YAML and runs no agent. Read and
edit it, run `atelier check review`, then
`atelier run review --input brief="<the work to do>"`.

## Running

```bash
atelier run <conduit> [--input key=value]...
atelier run <conduit> --hide-steps          # default is --show-steps
atelier run --resume <flow_id>              # pick up a failed or crashed run
atelier run --again <flow_id>               # fresh run reusing a past flow's inputs
atelier run <conduit> --agent review=codex  # another agent for one task, this run only
atelier run <conduit> --worktree draft_a     # that task in its own Git checkout
atelier stop <flow_id>                      # gracefully halt a running flow
atelier wait <flow_id> [--timeout SECONDS]   # watch an already-started run
```

| Flag | Notes |
|---|---|
| `--input` / `-i` | `key=value`, repeatable |
| `--show-steps` / `--hide-steps` | stream intermediate agent thinking and tool activity live (default: show) |
| `--resume` | flow id, prefix matching supported. `conduit_name` is not needed |
| `--again` | flow id, prefix ok; starts a new flow with the saved inputs |
| `--worktree` | `TASK`, repeatable; top-level `tool:bash`/`harness:` tasks get separate Git checkouts, unnamed tasks stay in the shared directory, nothing is merged back. See [task-worktrees.md](task-worktrees.md) |
| `--agent` | `TASK=HARNESS`, repeatable; top-level `harness:` tasks only, the file is unchanged, saved for `--again`/`--resume`. See [Choosing an agent for one run](harnesses.md#choosing-an-agent-for-one-run) |

As soon as the flow starts, a run prints its id and the address of its live page
(`--resume` prints the page too):

```
· starting flow 20260727_0eb21391_loopdemo
· run page http://127.0.0.1:8000/runs/20260727_0eb21391_loopdemo
```

The page loads only while `atelier serve` runs from the same directory; see
`serve-and-api.md`. `atelier ask` prints the same line.

Then it prints a per-task panel as each task finishes, a summary line and the
flow id again:

```
tick [tool:bash] (10/10)  exit=0 - 0.004s
after [tool:bash]  skipped  (condition not met: tick.output.match(done))
10  1  -  total 0.04s
flow_id: 20260727_0eb21391_loopdemo
```

On failure it names the failing task and suggests the resume command. First run
`atelier diagnose <flow_id>` to understand the cause before resuming.

`atelier run` and `atelier ask` exit 0 when the flow completed, 1 when it
failed, and 143 when it was stopped by `atelier stop` or another SIGTERM
(before 0.14.0 a stopped run exited 0). A script must not read 143 as success.

`atelier stop` sends the stop signal and waits up to 15 seconds. It exits 0
once the flow is no longer running. It exits 1 when it cannot stop the flow
(already finished, runner gone, another host, or inside a server or scheduler
process) and, since 0.14.0, when the flow is still running after the wait:
the work may still be going, so check `atelier status <flow_id>` again.

`wait` starts nothing and changes nothing. Its default timeout is 60 seconds.
It exits 0 only for a saved `completed` run, printing just the resolved flow id
to stdout; it exits 1 for failure, stop or a dead runner, 124 on timeout, and
130 on Ctrl+C. Timeout or interruption leaves the run going. For scripts:

```bash
flow_id=$(atelier wait latest --timeout 60) && atelier outputs "$flow_id"
```

For an interactive agent conversation, use
`atelier ask "<prompt>" --path /abs/path` in a live terminal. `--path` / `-p` is
required; `--harness NAME[:MODEL[:EFFORT]]` selects the agent (default
`claude-code`). `--permissions full|edits|read-only` sets what the agent may do
without asking; without it the agent gets `ATELIER_AGENT_PERMISSIONS`, else
`full`. A level the agent cannot be held to fails the run before the prompt is
sent (see [permission levels](conduit-yaml.md#agent-permission-levels)).
Answer its questions until it finishes: Enter submits an answer, and Escape then
Enter adds a new line. The hint `Alt+Enter to submit` that 0.14.0 prints is
wrong; 0.14.1 prints the correct one. When stdin is not a terminal, each answer is one line of stdin.

## Inspecting

```bash
atelier diagnose <flow_id> [--json]
atelier status <flow_id> [--json]
atelier logs <flow_id> [-t TASK] [-s CHANNEL] [-n N] [-f] [--json]
atelier outputs <flow_id> [-t TASK] [--json]
atelier timing <flow_id> [--json]
atelier list conduits [--json]
atelier list flows [-c CONDUIT] [--json]
atelier compare <first_flow_id> <second_flow_id> [--json]
atelier compare <conduit> [--json]           # compare its two newest runs
```

| Command | Reads | Use it for |
|---|---|---|
| `diagnose` | saved run records | first step after failure: cause, retained work and next commands |
| `status` | `progress.json` | per-task state of a run, live or finished |
| `logs` | `logs.jsonl` | what a task actually printed |
| `outputs` | `outputs.yaml` | the value each task produced |
| `timing` | `logs.jsonl` | per-task duration, slowest first |

`logs -s/--show` picks the channel: `output` (default), `stdout`, `stderr`,
`steps`, or `all`. `-n/--last N` limits to the last N entries. `-f/--follow`
tails until the flow finishes.

`outputs -t <task>` prints that task's raw output alone, which is pipe-friendly.
Note `outputs.yaml` keeps only the **last** iteration of a looped task, and
records `null` for skipped tasks.

`timing` sums repeated iterations, so a looped step shows its true total cost.

`diagnose` is read-only and starts no agent. A successful reading exits 0 even
when the run failed; this is not a run-success check. It accepts a unique id
prefix or `latest`. For failed nested work, follow the printed child
`atelier diagnose <child_flow_id>` for the original exit status; the parent
does not aggregate full child history. See `troubleshooting.md`.

`compare` reads saved runs to compare agent choices, loop outcomes and duration.
Pass two flow ids, or a conduit name to select its two newest runs.

## Cleanup

```bash
atelier rm <flow_id> [--force] [-y/--yes] [--json]
atelier prune [-c CONDUIT] [--older-than DAYS] [--keep N] [--force] [-y] [--json]
```

`rm` deletes one flow run directory; `--force` deletes even a running flow.
`prune` bulk-deletes terminal runs by age and/or keep-count, and excludes running
flows unless `--force`. Both prompt unless `-y`.

## Agents

```bash
atelier list harnesses [--ready] [--json]
atelier harness check <name> [--timeout SECONDS]
atelier harness check --cmd "/opt/my-agent --acp"
atelier harness sync
```

See `harnesses.md`. `harness sync` refreshes the registry from the network;
harness discovery and runs read the local snapshot. `harness check` also shows
the mode runs will use at the `ATELIER_AGENT_PERMISSIONS` level.

## Packages

```bash
atelier install <source> [--ref GIT_REF] [--project/--no-project] [--force]
atelier update <package> [--force]
atelier uninstall <package>
```

See `packages.md`.

## Scheduling

```bash
atelier schedule add <file.{json,yaml}>
atelier list schedules [--json]
atelier schedule rm <id-or-name>
atelier schedule run-now <id-or-name>
atelier schedule history <id-or-name> [--json]
atelier schedule daemon [--reload-interval 30] [--log-level INFO]
```

See `scheduling.md`. `list schedules` reads `.atelier/schedules/` directly and
does **not** contact a running daemon - to confirm the daemon is alive, check the
process.

`schedule history` shows recorded runs newest first. `schedule daemon` runs in
the foreground until Ctrl+C or SIGTERM; `serve` also embeds a scheduler.

## Server

```bash
atelier serve [--host 127.0.0.1] [--port 8000] [--reload-interval 30.0] \
              [--cors-origin URL]... [--log-level INFO] [--idle-exit MINUTES]
```

`--port 0` picks an ephemeral port. By default only pages this server serves
may call its API; since 0.14.0 a page on another local port gets `403`.
`--cors-origin` (repeatable) names another page's origin that may call it, for
example `--cors-origin http://localhost:5173` for the Vite dev server. The CLI,
scripts and `curl`, which send no `Origin`, still work. See `serve-and-api.md`
for endpoints and the security rules that govern non-loopback binds.

## Upgrade Atelier

```bash
atelier self-update
```

For binary installs, downloads, verifies and installs the latest release.
For pip/uv-managed installs this command exits with guidance to use
`uv tool upgrade flow-atelier` instead. Package updates remain
`atelier update <package>`.

## Environment variables

All are prefixed `ATELIER_`. Most can also come from a `.env` file in the
working directory. The ones marked **shell only** must be exported in your
shell environment: since 0.14.0 Atelier ignores them in that `.env`, because
the folder may be a repository you just cloned. A `.env` may lower
`ATELIER_AGENT_PERMISSIONS` but not set it to `full`. For each ignored line,
Atelier prints on stderr:

```
[flow-atelier] ignored ATELIER_HARNESSES from ./.env: set it in your shell environment instead; the .env of the folder you run in cannot set it
```

| Variable | Default | Controls |
|---|---|---|
| `ATELIER_ATELIER_DIR` | `./.atelier` | base dir for conduits and flows |
| `ATELIER_GLOBAL_ATELIER_DIR` | `~/.atelier` | global conduit store; **shell only** |
| `ATELIER_DEFAULT_TIMEOUT` | `3600` | per-task timeout in seconds |
| `ATELIER_DEFAULT_MAX_CONCURRENCY` | `3` | parallel tasks per conduit |
| `ATELIER_LOOP_HISTORY_LIMIT` | `10` | iterations rendered by `{{loop.history}}`; `<= 0` unlimited |
| `ATELIER_LOOP_HISTORY_ENTRY_CHARS` | `40000` | chars per history entry; `<= 0` unlimited |
| `ATELIER_HARNESSES` | empty | JSON object of `name -> argv`, registers `harness:<name>`; **shell only** |
| `ATELIER_CLAUDE_LAUNCH_CMD` | registry | JSON argv override; **shell only** |
| `ATELIER_CODEX_LAUNCH_CMD` | registry | JSON argv override; **shell only** |
| `ATELIER_OPENCODE_LAUNCH_CMD` | registry | JSON argv override; **shell only** |
| `ATELIER_COPILOT_LAUNCH_CMD` | registry | JSON argv override; **shell only** |
| `ATELIER_CURSOR_LAUNCH_CMD` | registry | JSON argv override; **shell only** |
| `ATELIER_DONE_MARKER` | `[ATELIER_DONE]` | token that ends an `interactive: true` conversation |
| `ATELIER_AGENT_PERMISSIONS` | `full` | `full`, `edits` or `read-only` for every agent task, also `atelier ask`; a task's `permissions:` or `ask --permissions` wins. A `.env` may set `edits` or `read-only`, not `full`. See [permission levels](conduit-yaml.md#agent-permission-levels) |
| `ATELIER_ALLOW_UNENFORCED_PERMISSIONS` | unset | `1` runs `edits` or `read-only` on an agent that cannot be held to it, with a warning, instead of failing; **shell only** |
| `ATELIER_API_TOKEN` | empty | bearer token for the HTTP/WS API; **shell only**. Agent and shell steps do not receive it |
| `ATELIER_SERVE_URL` | `http://127.0.0.1:8000` | base of the `run page` link a run prints; **shell only** |
