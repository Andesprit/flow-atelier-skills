# The `atelier` CLI - every command

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
```

`init` writes `.atelier/conduits/hello/conduit.yaml`, a one-task bash conduit
that works before any AI tool is installed.

`check` validates schema, dependency syntax, loop predicates and template
references, and lists each conduit's required inputs. It runs no tasks.

`plan` validates first (failing identically to `check`), then renders waves with
plain and conditional edges, loop predicates, sinks, and short-circuit gates.
Read-only - no flow is created.

## Running

```bash
atelier run <conduit> [--input key=value]...
atelier run <conduit> --hide-steps          # default is --show-steps
atelier run --resume <flow_id>              # pick up a failed or crashed run
atelier run --again <flow_id>               # fresh run reusing a past flow's inputs
atelier stop <flow_id>                      # gracefully halt a running flow
```

| Flag | Notes |
|---|---|
| `--input` / `-i` | `key=value`, repeatable |
| `--show-steps` / `--hide-steps` | stream intermediate agent thinking and tool activity live (default: show) |
| `--resume` | flow id, prefix matching supported. `conduit_name` is not needed |
| `--again` | flow id, prefix ok; starts a new flow with the saved inputs |

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

On failure it names the failing task and suggests the resume command.

## Inspecting

```bash
atelier status <flow_id> [--json]
atelier logs <flow_id> [-t TASK] [-s CHANNEL] [-n N] [-f] [--json]
atelier outputs <flow_id> [-t TASK] [--json]
atelier timing <flow_id> [--json]
atelier list conduits [--json]
atelier list flows [-c CONDUIT] [--json]
```

| Command | Reads | Use it for |
|---|---|---|
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
atelier harness list [--ready] [--json]
atelier harness check <name> [--timeout SECONDS]
atelier harness check --cmd "/opt/my-agent --acp"
atelier harness sync
```

See `harnesses.md`. `harness sync` is the only command that touches the network;
runs always read the local snapshot.

## Packages

```bash
atelier add <source> [--ref GIT_REF] [--project/--no-project] [--force]
atelier update <package> [--force]
atelier remove <package>
```

See `packages.md`.

## Scheduling

```bash
atelier schedule add <file.{json,yaml}>
atelier schedule list [--json]
atelier schedule remove <id-or-name>
atelier schedule run-now <id-or-name>
atelier scheduler start [--reload-interval 30] [--log-level INFO]
atelier scheduler status [--json]
```

See `scheduling.md`. `scheduler status` reads `.atelier/schedules/` directly and
does **not** contact a running daemon - to confirm the daemon is alive, check the
process.

## Server

```bash
atelier serve [--host 127.0.0.1] [--port 8000] [--reload-interval 30.0] \
              [--cors-origin URL]... [--log-level INFO]
```

`--port 0` picks an ephemeral port. `--cors-origin` is repeatable. See
`serve-and-api.md` for endpoints and the security rules that govern non-loopback
binds.

## Environment variables

All prefixed `ATELIER_`, readable from a `.env` file in the working directory.

| Variable | Default | Controls |
|---|---|---|
| `ATELIER_ATELIER_DIR` | `./.atelier` | base dir for conduits and flows |
| `ATELIER_GLOBAL_ATELIER_DIR` | `~/.atelier` | global conduit store |
| `ATELIER_DEFAULT_TIMEOUT` | `3600` | per-task timeout in seconds |
| `ATELIER_DEFAULT_MAX_CONCURRENCY` | `3` | parallel tasks per conduit |
| `ATELIER_LOOP_HISTORY_LIMIT` | `10` | iterations rendered by `{{loop.history}}`; `<= 0` unlimited |
| `ATELIER_LOOP_HISTORY_ENTRY_CHARS` | `40000` | chars per history entry; `<= 0` unlimited |
| `ATELIER_HARNESSES` | empty | JSON object of `name -> argv`, registers `harness:<name>` |
| `ATELIER_CLAUDE_LAUNCH_CMD` | registry | JSON argv override |
| `ATELIER_CODEX_LAUNCH_CMD` | registry | JSON argv override |
| `ATELIER_OPENCODE_LAUNCH_CMD` | registry | JSON argv override |
| `ATELIER_COPILOT_LAUNCH_CMD` | registry | JSON argv override |
| `ATELIER_CURSOR_LAUNCH_CMD` | registry | JSON argv override |
| `ATELIER_DONE_MARKER` | `[ATELIER_DONE]` | token that ends an `interactive: true` conversation |
| `ATELIER_API_TOKEN` | empty | bearer token for the HTTP/WS API |
| `ATELIER_SERVE_URL` | `http://127.0.0.1:8000` | base of the `run page` link a run prints |
