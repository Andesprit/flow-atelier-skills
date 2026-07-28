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

A run prints a per-task panel as each task finishes, then a summary line and the
new flow id:

```
tick [tool:bash] (10/10)  exit=0 - 0.004s
after [tool:bash]  skipped  (condition not met: tick.output.match(done))
10  1  -  total 0.04s
flow_id: 20260727_0eb21391_loopdemo
```

On failure it names the failing task and suggests the resume command.

## Interactive prompts (`atelier ask`)

```bash
atelier ask --harness <name> [--cwd <dir>] [--name <task>] [--hide-steps] [--json] "prompt"
```

`ask` runs a prompt on one harness and streams the reply - no conduit, no
YAML. It is the CLI equivalent of the frontend's "run a single task", and the
entry point for **multi-agent orchestration**: one AI agent (Cloud Code,
Codex, opencode, …) shells out to flow-atelier to delegate a piece of work to
a *different* harness and converse with it.

The task is **always interactive**: the harness keeps the session open and,
if the invoked agent asks a question (ends a turn without `[ATELIER_DONE]`),
flow-atelier fetches a reply and sends it back, looping until the agent
signals it is done. An agent that answers once and emits the marker completes
as an ordinary one-shot - the loop is invisible when unused. There is no turn
cap on `ask`; the conversation runs until the agent is done, the channel is
closed, or an explicit stop is sent.

```bash
# Human at a keyboard: colored panels; when the agent asks, you type.
atelier ask --harness claude-code "refactor this function for readability"
atelier ask --harness codex "write a test for src/auth.py" --cwd ./my-repo

# Parent agent (agent-to-agent): JSON-lines over stdio. Agents always pass --json.
atelier ask --json --harness opencode "summarize the changes in the last commit"
```

| Flag | Notes |
|---|---|
| `--harness` / `-h` | required. Any `harness:*` from `atelier harness list`. The `harness:` prefix is optional (`claude-code` ≡ `harness:claude-code`). Unknown or not-ready harness exits 1 before any flow starts |
| `--cwd` | working directory the harness runs in. Defaults to the current directory |
| `--name` | cosmetic task name; appears in the flow id (default `ask`) |
| `--show-steps` / `--hide-steps` | stream intermediate agent thinking and tool activity live (default: show) |
| `--json` | machine-readable JSON-lines over stdio (agent-to-agent transport). Agents always pass this. Default is human terminal |

Behaviour notes:

- Without `--json`, output streams live exactly like `atelier run` - same
  per-task panel, heartbeat, and summary footer - then prints the new
  `flow_id`. When the agent asks a question, you type the reply.
- The prompt is both the task prompt and the task description; the ad-hoc
  conduit is named `task__<name>` and is not saved to `.atelier/conduits/`.
- The resulting flow lands under `.atelier/flows/` like any other, so it can
  be inspected with `status`/`logs`/`outputs` and resumed with
  `atelier run --resume <flow_id>` if it failed.

### Agent-to-agent protocol (`--json`)

`--json` switches the transport to **stdio JSON-lines**: atelier emits one
JSON object per line on stdout and reads one JSON reply per turn from stdin.
stdout is pure JSON under `--json` - no panels, colors, or heartbeat.

Outbound events (atelier → parent):

| Event | Meaning |
|---|---|
| `{"type":"flow_started","flow_id":"..."}` | once, before the first turn |
| `{"type":"agent_message","text":"..."}` | streamed text from the invoked agent |
| `{"type":"step","kind":"thinking\|tool_call\|tool_result"[,"tool":"..."][,"status":"..."]}` | intermediate agent activity (a thought, a tool call, a tool result). Only non-empty fields appear: a `thinking` step omits `tool`/`status`, a `tool_call` carries `tool`, a failed `tool_result` carries both |
| `{"type":"request_input","prompt":"..."}` | the agent asked a question - reply now |
| `{"type":"task_event",...}` | per-iteration status |
| `{"type":"done","flow_id":"...","output":"..."}` | agent finished; terminal (may carry `"stopped":true`) |
| `{"type":"error","flow_id":"...","message":"..."}` | failure |

Inbound replies (parent → atelier), only expected after `request_input`:

| Reply | Meaning |
|---|---|
| `{"type":"reply","text":"..."}` | send this text as the next turn |
| `{"type":"stop"}` | end the conversation cleanly |

Closing stdin (EOF) also ends the run cleanly. The `[ATELIER_DONE]` marker is
internal coordination and never appears in the JSON stream.

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
