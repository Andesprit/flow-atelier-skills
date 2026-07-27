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
atelier harness list           # every agent, and whether it runs here
atelier harness list --ready   # only the ones usable right now
atelier harness list --json
atelier harness sync           # refresh the snapshot from the network
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
