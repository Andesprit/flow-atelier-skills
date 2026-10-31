# Harnesses - the AI agents

A harness is an AI coding agent a task hands work to, addressed as
`tool: harness:<name>`.

**flow-atelier does not install agents and does not manage their logins.** You
install the agent, you log into it with its own CLI, and flow-atelier runs the
command that agent documents. No API keys are configured, stored, or proxied.

```yaml
- review:
    description: review the diff
    task: "review the working tree and list any bugs"
    tool: harness:gemini
    depends_on: []
```

## Finding a name

Names come from the [ACP registry](https://agentclientprotocol.com/get-started/registry),
a snapshot of which ships with each release. Roughly 40 agents, including
`claude-code`, `codex`, `gemini`, `copilot`, `cursor`, `opencode`, `qwen-code`,
`goose`, `amp-acp`.

```bash
atelier list harnesses           # every agent, and whether it runs here
atelier list harnesses --ready   # only the ones usable right now
atelier list harnesses --json
atelier harness sync            # refresh the snapshot from the network
```

`harness sync` is the only command that touches the network. It stores the
refreshed registry in the global atelier dir, where it supersedes the bundled
snapshot; runs always read the local copy.

The `via` column says how an agent starts:

- **`npx` / `uvx`** - the agent's own package manager fetches it on first run, at
  the version the registry pins. Needs Node.js or uv on PATH. This is the
  agent's normal distribution mechanism, the same as running the command
  yourself.
- **`binary`** - you install the agent's CLI; flow-atelier runs it from PATH.
  `harness list` names the missing binary when it is absent.

Harness names must be `^[a-z0-9][a-z0-9-]*$` - lowercase letters, digits and
hyphens.

## Checking one before you use it

```bash
atelier harness check gemini
atelier harness check harness:gemini          # the prefix is accepted too
atelier harness check --cmd "/opt/my-agent --acp"
atelier harness check gemini --timeout 120    # default 90s
```

The check starts the agent, completes the ACP handshake, opens a session, and
stops. **No prompt is sent, so it costs no tokens.** It reports one of:

| Result | Meaning | Fix |
|---|---|---|
| **ok** | agent name and version, ACP version, session modes offered | none |
| **not found on PATH** | the binary is not installed | install the agent yourself |
| **started but did not speak ACP** | usually the wrong entry point | most CLIs need an `--acp` flag |
| **could not open a session** | usually not logged in | the check lists the auth methods the agent advertises; log in with that agent's own CLI |

Failures exit non-zero and include the tail of the agent's own stderr, which is
where a failing agent explains itself. Run this before debugging a conduit - a
harness task that fails for auth reasons looks like a conduit problem and is not.

## Choosing an agent for one run

Use this when a workflow names an agent you cannot or do not want to use today.
`--agent TASK=HARNESS` picks another agent for one run. The conduit file is not
changed. This example recipe has two agent tasks:

Save `.atelier/conduits/review_pair/conduit.yaml`:

```yaml
name: review_pair
description: draft with one agent, review with another
inputs:
  topic:
    description: what to write about
tasks:
  - prepare:
      description: prepare the topic
      task: 'echo "topic={{inputs.topic}}"'
      tool: tool:bash
  - draft:
      description: first draft
      task: "Write one line about {{inputs.topic}}"
      tool: harness:claude-code
      depends_on: [prepare]
  - review:
      description: check the draft
      task: "Review this line: {{draft.output}}"
      tool: harness:claude-code
      depends_on: [draft]
```

1. **Find the task names.** `atelier show review_pair` prints the definition.
   Only top-level `harness:` tasks can take `--agent`: here `draft` and
   `review`, not `prepare`.
2. **Find an agent name.** `atelier list harnesses --ready` shows agents whose
   command is on PATH. `atelier harness check <name>` starts the agent but
   sends no prompt (see [Checking one](#checking-one-before-you-use-it)).
   Neither proves that your login, model or quota will do real work.
3. **Run it.** This starts real agent work, billed by that agent's provider:

   ```bash
   atelier run review_pair --input topic=tea --agent review=codex
   ```

   Repeat the option for more tasks: `--agent draft=gemini --agent review=codex`.
   The value is `<name>`, `<name>:<model>` or `<name>:<model>:<effort>`, with or
   without `harness:`. Tasks you do not name keep the recipe's agent.
4. **See what the run used.** Copy the printed `flow_id`, then run
   `atelier status <flow_id>`. Its `agent` column shows each chosen agent and
   marks the rest `(recipe)`. When a run saved no choice, the column is absent.

If `atelier run --help` does not mention `--agent` (or the run says
`No such option: --agent`), your build does not have it. Upgrade (see
[Upgrade Atelier](cli.md#upgrade-atelier)) or edit the `tool:` line instead.

### Run again or resume with a choice

The choices are saved with the run.

- **`atelier run --again <flow_id>`** starts a new flow and runs every task
  again. It reuses the saved choices. `--agent` on the same command replaces the
  choice for the tasks it names.
- **`atelier run --resume <flow_id>`** continues a failed or crashed flow (a
  completed flow cannot resume). Completed tasks keep their output and the agent
  that produced it. The rest run with the saved choices, or the recipe's agent
  where none was saved. Without `--agent`, a looping task that stopped part way
  continues on the agent it started with.
- **`--resume <flow_id> --agent TASK=HARNESS`** may name only a task that is
  `pending` or `failed`. A completed, running, skipped or cancelled task is
  refused. A looping task (`repeat`) that already saved a successful iteration
  is refused too, even while it is failed and even if you name the same agent:
  its loop history belongs to the first agent. Use `--again` to redo it.
- **The recipe changed.** Saved choices are checked against the file as it is
  now. If a chosen task was renamed or is no longer an agent task, `--again`
  and `--resume` refuse with *the recipe changed since that run*. Another
  `--agent` does not get past this; start a fresh `atelier run <conduit>`.

A resume reads the current file and is at-least-once: a task can run again and
repeat side effects or cost. See
[what resume does not promise](recovery-exercise.md#what-this-shows-and-what-it-does-not).

Inside a called conduit, `call.task=HARNESS` selects a task of a statically
named child (`task: child_name`). A child chosen by template (`{{...}}`) is
refused.

### When `--agent` is refused

Each refusal happens before any task starts, and leaves the files and saved
runs as they were.

| Message contains | Cause | Fix |
|---|---|---|
| `has no task 'reveiw' — did you mean 'review'?` | no top-level task with that name | use a name from the listed `valid agent selectors` |
| `runs 'tool:bash', which is not an agent` | the task is a shell, human or conduit step | only `harness:` tasks take `--agent` |
| `is not an agent — --agent re-points harness tasks only` | the value was `tool:...` | give an agent name; edit the YAML to change a tool |
| `expected TASK=HARNESS` | no `=` or an empty side | `--agent review=codex` |
| `names task 'draft' twice` | the same task given two agents | one `--agent` per task |
| `is not a harness name` | bad name, or more parts than `<name>:<model>:<effort>` | `<name>[:<model>[:<effort>]]`, lowercase |
| `names unknown agent` | not in the registry or `ATELIER_HARNESSES` | `atelier list harnesses` |
| `cannot run: task 'draft' [...] not found on PATH` | the agent's command is not installed | install it, or choose another agent |
| `only a pending or failed task can be given another agent` | resume named a task that already finished | `atelier run --again <flow_id> --agent ...` |
| `already recorded iteration` | resume named a loop that has saved iterations | `atelier run --again <flow_id> --agent ...` |
| `can only resume failed or crashed flows` | the flow completed | `--again` |

## Registering an agent the registry does not list

Something private, a fork, a local build:

```bash
ATELIER_HARNESSES='{"mine":["/opt/my-agent","--acp"]}'
```

Each entry registers `harness:<name>` as a first-class tool driven by the same
executor as every other harness. A name that collides with a registry agent
overrides it.

To pin one of the five harnesses that predate the registry to a specific argv,
use its own variable instead:

```bash
ATELIER_CLAUDE_LAUNCH_CMD=["npx","-y","@agentclientprotocol/claude-agent-acp@0.62.0"]
ATELIER_CODEX_LAUNCH_CMD=["npx","-y","@agentclientprotocol/codex-acp@1.1.7"]
ATELIER_OPENCODE_LAUNCH_CMD=["opencode","acp"]
ATELIER_COPILOT_LAUNCH_CMD=["npx","-y","@github/copilot@1.0.75","--acp"]
ATELIER_CURSOR_LAUNCH_CMD=["cursor-agent","acp"]
```

These override the registry. Both forms take a JSON array of argv.

## One-turn vs interactive

By default a harness task runs **one turn** and stops: the prompt goes out, the
reply comes back, the task's output is that reply.

```yaml
- long_chat:
    description: work with the agent until it says it is done
    task: "Refactor the parser, then tell me what changed."
    tool: harness:claude-code
    depends_on: []
    interactive: true
```

With `interactive: true` flow-atelier appends this to every message it sends:

> When - and only when - you are completely finished, output the exact token
> `[ATELIER_DONE]` to signal completion.

Then it keeps the conversation open. The agent replies, the reply streams to your
terminal, and if `[ATELIER_DONE]` has not appeared, flow-atelier asks **you** for
the next message to send back. The loop ends when the token shows up. The token
is configurable via `ATELIER_DONE_MARKER`.

If the agent asks permission to run a tool, you get a numbered menu on the
terminal and your choice is sent back as the answer.

Interactive tasks need a human at the keyboard. For unattended runs (scheduled
ticks, CI) leave `interactive: false` and shape the prompt so one turn is enough.

## Prompting patterns that work

**Make the output machine-checkable.** Conditional dependencies and loop
predicates are regexes over the agent's output, so ask for a fixed token:

```yaml
task: |
  Review /tmp/build/src for security issues.
  End your response with exactly one of:
  VERDICT: APPROVE
  VERDICT: REJECT
depends_on: []
```

then gate on it:

```yaml
depends_on: ['code_review.output.match(VERDICT:\s*APPROVE)']
```

**Guard against a step ending its turn early.** An agent can return narration
instead of the block you asked for. If a later step consumes that output, verify
it first with a cheap `tool:bash` step that greps for your markers and emits a
value the next step gates on. Do not make that check fail the task if siblings
are running - a failure cancels them.

**Retries are for crashes, `repeat` is for iteration.** `retries: 2` re-runs a
task that *failed*; `repeat` loops one that *succeeded*. An agent that answers
badly has still succeeded, so shape that with `repeat` + `until`.

## Streaming

`atelier run` prints intermediate agent thinking and tool activity by default.
`--hide-steps` silences it. The argument identifying each tool call is printed so
the run is readable, with credential-shaped values (`Bearer <token>`, `sk-`,
`ghp_`, `xox` prefixes, `--password` / `TOKEN=` flags) masked as `***` on the way
to the screen. That masking is a heuristic, not a guarantee, and the recorded
logs under `.atelier/flows/<id>/` keep the **unredacted** text.
