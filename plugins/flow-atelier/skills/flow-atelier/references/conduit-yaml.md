# Conduit YAML - complete reference

Everything a `conduit.yaml` can declare, with the validation rules the engine
actually enforces.

## Conduit-level fields

| Field | Type | Default | Rules |
|---|---|---|---|
| `name` | str | required | `^[A-Za-z0-9_-]+$`. Must match the folder name. Rejects `/`, `.`, `..` (it becomes a path component) |
| `description` | str | required | free text |
| `timeout` | int | `3600` | seconds, per task; `>= 1` |
| `max_concurrency` | int | `3` | tasks running in parallel within this conduit; `>= 1` |
| `inputs` | map | `{}` | see below |
| `tasks` | list | required | task names must be unique |

### `inputs`

Two accepted spellings. The string shorthand becomes the description:

```yaml
inputs:
  branch: Branch to deploy                          # required input
  env: {description: Target env, default: staging}  # optional - default supplied
  count: {default: "3"}                             # description may be omitted
```

An input **with** a `default` is optional; callers that omit it get the default,
callers that pass `--input` override it. An input **without** a default is
required, and `atelier check` reports it as `requires --input: <name>`.

Values arrive as strings from `--input key=value`.

## Task-level fields

| Field | Type | Default | Rules |
|---|---|---|---|
| `name` | str | required | `^[A-Za-z0-9_]+$` - **letters, digits and underscores only, no hyphens** |
| `description` | str | required | free text |
| `task` | str | required | shell command, agent prompt, HITL prompt, or a conduit name for `tool:conduit` |
| `tool` | str | required | a built-in `tool:*` or `harness:<name>` |
| `depends_on` | list[str] | `[]` | plain names or conditional expressions |
| `repeat` | int | `1` | `>= 1` |
| `until` | str | none | `output.match(...)` / `output.not_match(...)`; requires `repeat > 1` |
| `while` | str | none | same grammar; mutually exclusive with `until` |
| `on_exhaust` | `complete`\|`fail` | `complete` | requires `until` or `while` |
| `stagnation_limit` | int | none | `>= 2`, requires `repeat > 1` |
| `retries` | int | `0` | `>= 0`; re-runs a task that **failed** |
| `retry_backoff` | float | `0.0` | `>= 0`, seconds between retries |
| `timeout` | int | inherits conduit | `>= 1`, seconds, overrides for this task |
| `interactive` | bool | `false` | harness tasks only; see `harnesses.md` |
| `permissions` | `full`\|`edits`\|`read-only` | `ATELIER_AGENT_PERMISSIONS`, else `full` | harness tasks only; see [Agent permission levels](#agent-permission-levels) |
| `inputs` | map | `{}` | HITL question set, or inputs passed to a nested conduit |

The YAML task form is a list of single-key maps; the key becomes `name`:

```yaml
tasks:
  - my_task:
      description: ...
```

`tool` validation: the `tool:*` side is a closed set (`tool:bash`, `tool:hitl`,
`tool:conduit`) because those executors are code. `harness:<name>` only has its
*shape* checked (`^[a-z0-9][a-z0-9-]*$`); whether an executor is registered for
it is answered later, at run time.

## Agent sessions

Set `session` on `harness:<name>` tasks to continue a named agent conversation
across tasks in the same run. Nested conduits inherit the top-level run's
session scope. Only the same harness can reuse a saved conversation; a different
harness starts its own conversation even if the name matches.

Save this as `.atelier/conduits/shared_session/conduit.yaml`:

```yaml
name: shared_session
description: Two sequential turns in a named agent conversation
inputs:
  conversation: {default: review}
tasks:
  - draft:
      description: Draft an approach
      tool: harness:codex
      session: "{{inputs.conversation}}"
      task: Describe an approach to the requested change.
  - refine:
      description: Refine the same approach
      tool: harness:codex
      session: "{{inputs.conversation}}"
      depends_on: [draft]
      task: Refine your earlier approach and explain the tradeoff.
```

`depends_on` orders these turns. A session name can be a literal such as
`review`, or a template using inputs or earlier outputs, just like `task`.
Names are stripped of surrounding whitespace. A changed name selects another
conversation; returning to an existing name can reuse it. An empty *rendered*
name means no shared session. A literal blank `session` fails validation with
`session must not be empty`; using it on a non-harness task fails with
`session requires a harness:<name> tool`.

Continuation is best effort: if the harness cannot reload the saved session or
refuses it, Atelier logs a warning and starts a fresh conversation. Do not rely
on earlier context always being available. The automatic-goal package's
`goal_iteration` conduit uses the same pattern: `session: manager` on its
director tasks, and `session: '{{milestone_session.output}}'` on its worker.

## Agent permission levels

**Agents run with full permissions by default.** An agent task can edit any
file and run any command. Atelier switches the agent to the most permissive
mode it knows, such as Claude Code's `bypassPermissions`, and approves every
permission request the agent sends. A prompt, or text the agent reads in the
project, can lead it to do damage. Limit it with the task field `permissions`:

| Value | What the agent may do without asking |
|---|---|
| `full` | Everything. This is the default. |
| `edits` | Read and change files. Atelier picks an accept-edits mode when the agent has one, such as Claude Code's `acceptEdits`, else a read-only mode that asks before each edit, such as Codex's `read-only`. It allows requests to read, search, edit, move or delete files, and rejects the rest, such as running a command or fetching a URL. |
| `read-only` | Only read, as far as Atelier is asked. Atelier picks a read-only mode such as Codex's `read-only`, else keeps the agent's own mode (leaving a bypass mode first), and rejects every request. |

Set it on one task with `permissions:`, or for every agent task with
`ATELIER_AGENT_PERMISSIONS` in the environment or in `.env`. The task field
wins. It is valid only on `harness:<name>` tasks; elsewhere `atelier check`
fails with `permissions requires a harness:<name> tool`. `atelier plan` shows
the level of each agent task. `atelier harness check` shows the mode runs will
use at the `ATELIER_AGENT_PERMISSIONS` level.

```yaml
- review:
    description: Review the change
    task: Review the last commit and list what must be fixed.
    tool: harness:codex
    permissions: read-only
```

While neither is set, each run prints one line that says agents have full
permissions. Setting either one, even to `full`, removes that line.

**The levels are not a sandbox.** Atelier only chooses the agent's mode and
answers the requests the agent sends. An agent can still do what its own mode
allows without asking: Codex in its `read-only` mode still runs commands that
only read, inside its own sandbox. The agent's own settings also apply at every
level. Claude Code loads your user settings and the project's
`.claude/settings.json` and `.claude/settings.local.json`; tools their allow
rules pre-approve run without asking, and their hooks run shell commands by
themselves. A checkout you do not trust can ship such a file, so `read-only`
does not make it safe to review: check its `.claude/` folder first, or run the
agent in a container or a virtual machine.

The level and the [interaction policy](#interaction-policy) below work
together. The level decides what is allowed at all: a request it does not
allow is rejected without asking anyone. `interaction.permissions` decides who
answers the rest. With `edits` or `read-only` and a `human`, `supervisor` or
`hybrid` policy, Atelier takes a read-only mode when the agent has one, so the
person or supervisor is still asked about each edit.

## Interaction policy

**By default, agent permission requests are approved automatically.** Set
`interaction.permissions: human` to ask a person instead, or choose `supervisor`
or `hybrid` and configure a supervisor. This policy applies to harness tasks.
It does not limit what the agent may do; the task field `permissions` does that
(see [Agent permission levels](#agent-permission-levels)).

`interaction` is a conduit-level block. Questions and permissions have separate
policies:

| Field | Values | Default |
|---|---|---|
| `questions` | `human`, `supervisor`, `hybrid` | `human` |
| `permissions` | `approve_all`, `human`, `supervisor`, `hybrid` | `approve_all` |
| `supervisor` | configuration below | absent; required for either supervised mode |

- `human` asks the person running the flow. For a permission request, enter an
  offered option ID or `cancel` to deny it.
- `supervisor` asks the configured agent to answer or select a permission
  option. It must decide; escalation to a human is unavailable. A supervisor
  error fails the interaction.
- `hybrid` asks the supervisor first. It can escalate a decision to a human;
  supervisor errors, timeouts and exhausted limits also fall back to a human.
- `approve_all` applies only to permissions and approves requests automatically.

Questions route through this policy on tasks with `interactive: true` (or when
interactive harness mode is enabled for the run). Setting `questions` alone
does not enable interactive turns. Permission requests use their policy in
both single-turn and interactive tasks. Keep a terminal/input channel available
for `human` and `hybrid` policies.

### Supervisor configuration

| Field | Type | Default | Rules |
|---|---|---|---|
| `tool` | str | required | `harness:<name>`, using the same harness tool syntax as tasks |
| `instructions` | str | `""` | instructions for decisions on the user's behalf |
| `max_replies` | int | `8` | `>= 1`; supervisor attempts per worker invocation, shared by questions and permissions |
| `timeout` | int | `120` | `>= 1`, seconds per supervisor call, capped by the worker task's timeout |
| `max_context_chars` | int | `200000` | `>= 1`; maximum assembled supervisor prompt, including task, inputs, session and request |

The supervisor receives the task and conversation to decide on the user's
behalf. Its decision runs in a separate session from the worker. An attempted
supervisor reply consumes the reply budget even if it fails.

Save this as `.atelier/conduits/supervised/conduit.yaml`:

```yaml
name: supervised
description: Route worker questions and permissions through a supervisor
interaction:
  questions: hybrid
  permissions: supervisor
  supervisor:
    tool: harness:codex
    instructions: Answer within the stated task. Escalate missing requirements to the user.
    max_replies: 4
    timeout: 60
    max_context_chars: 100000
tasks:
  - worker:
      description: Work with supervised interaction
      tool: harness:codex
      interactive: true
      task: Inspect the project and explain one improvement. Ask about missing requirements.
```

Here, questions can reach a human, while permission decisions must come from
the supervisor. Instructions allowing escalation apply only to the `hybrid`
question policy.

### Limits and validation errors

Once the reply budget is spent, the next supervisor request raises
`supervisor reply limit (4) reached` for the example above. An oversized prompt
raises `supervisor context limit exceeded; session was not truncated`. Context
is rejected rather than silently trimmed. Both errors fail a `supervisor`
interaction; `hybrid` asks a human instead. Increase the relevant limit or
choose a policy that can reach a human when needed.

Choosing `supervisor` or `hybrid` without a `supervisor` block fails validation:

```text
supervisor configuration is required for supervisor/hybrid modes
```

An invalid `questions` value, such as `automatic`, reports:

```text
Input should be 'human', 'supervisor' or 'hybrid'
```

Check these complete examples before running them:

```bash
atelier check shared_session
atelier plan shared_session
atelier check supervised
atelier plan supervised
```

These commands validate the definitions and show the task order without
starting agents; they do not prove that an agent can continue a session or
answer a supervisor request at runtime.

## Dependencies and conditions

```
<task>                              # plain: wait for it to complete
<task>.output.match(<regex>)        # met if the regex matches its output
<task>.output.not_match(<regex>)    # met if the regex does NOT match
```

The regex is everything between the marker's `(` and the **last** `)` in the
string. Python `re.search` semantics. Surrounding quotes are optional and
stripped, so `match(PASS)` and `match("PASS")` are identical; to match a literal
quote, escape it (`match(\"PASS\")` looks for `"PASS"` with quotes).

Resolution per dependency:

| Upstream status | Result |
|---|---|
| pending / running | wait |
| completed, condition met | satisfied |
| completed, condition not met | **skip** this task (not a failure) |
| failed / cancelled | skip |
| skipped | skip |
| unknown task name | skip |

Skips propagate: anything depending on a skipped task also skips. This is what
makes mutually exclusive branches work - the untaken branch is quietly skipped.

Quote conditional dependencies in YAML. `- 'code_review.output.match(VERDICT:\s*APPROVE)'`
needs the quotes because of the `:` and to keep `\s` literal.

Output matching is capped at the first **1,000,000 characters** of a task's
output.

## Loops

`repeat: N` runs a *succeeding* task up to N times. This is not `retries`, which
re-runs a *failing* task.

```yaml
repeat: 10
until: 'output.match(PASS)'        # break as soon as an output matches
until: 'output.not_match(ERROR)'   # break as soon as no output matches
while: 'output.match(^429$)'       # keep going while an output matches
while: 'output.not_match(ready)'   # keep going while no output matches
```

Set at most one of `until` / `while`. **The first iteration always runs** before
the predicate is checked.

### Break truth table

"any-match" = at least one output matches; "every-match" = all of them do. For a
simple task there is exactly one output; for `tool:conduit` there is one entry
per nested sub-task output of that iteration.

| Mode | Predicate | Breaks when |
|---|---|---|
| `until` | `match` | any-match |
| `until` | `not_match` | not any-match |
| `while` | `match` | not any-match |
| `while` | `not_match` | every-match |

An empty output list never breaks - the loop waits for data on the next
iteration.

### Failed tries

A try that fails does not end a loop that has `until` or `while`. When a try
still exits nonzero after its `retries`, `until` and `while` are not checked
on it: the try counts toward `repeat`, and the next try starts. **If the last
try still fails, the task fails, whatever `on_exhaust` says**, so a red test
loop still stops its dependents. Up to 0.12, a failed try ended the loop at
once and failed the run.

The next try sees what went wrong through `{{loop.previous}}`: a first line
`[this try failed with exit code N]`, then the try's output, then its error
text. For a shell step that is its stdout and stderr. For a `tool:conduit`
body it is the output of the body task that failed (and its stderr, when that
task is a shell step), then a line that names that task and its error; the exit
code is the body's as a whole, usually 1. That text is raw, whatever the
command or the agent printed, so a shell step must read it as
`"$LOOP_PREVIOUS"` (or as `"$INPUT_<NAME>"` when a loop body gets it
forwarded), never as `{{loop.previous}}` in the command.

Some failures still end the loop at once:

- With a plain `repeat` and no `until` or `while`, the first failure fails the
  task.
- A `tool:hitl` step that gets no answer fails at once, also inside a
  `tool:conduit` body.
- A `tool:conduit` body that cannot start, for example because it misses a
  required input.

An agent that runs out of usage waits for the reset and never spends a try.
`stagnation_limit` counts failed tries too. If an agent fails inside a
`tool:conduit` loop, that try fails and the next one starts a fresh body; when
the loop still fails, `atelier diagnose` names the child task, agent and loop
iteration.

### Exhausting the budget

By default a loop that runs all `repeat` iterations **without ever matching its
predicate completes successfully**, as long as its last try exited 0, and its
dependents receive that last output. That silence is the most common authoring
trap: the loop looks like it worked, and a downstream conditional dependency
then skips, or an unconditional one (a deploy, a merge) runs on a result that
never met the condition. `atelier check` and `atelier plan` warn when such a
loop has dependents:

```
⚠ looped uses default on_exhaust: complete and may finish after 3 iterations
without meeting until: output.match(x); dependent tasks tail then run on its
last output. Set on_exhaust: fail on looped to stop the run.
```

```yaml
on_exhaust: fail    # instead: fail the task, and the flow
```

Set it whenever a deploy-like step follows the loop. `on_exhaust: complete`
only covers a last try that exited 0 without meeting the condition; a last try
that failed fails the task either way. The failure reads:

```
flow failed: task 'never' exhausted 3 iterations without matching its loop predicate
```

When the last try failed, the reason goes on with `; the last try failed:
exit=<code> stderr=<error text>`.

### Stagnation

```yaml
repeat: 20
until: 'output.match(DONE)'
stagnation_limit: 3     # fail after 3 identical consecutive outputs
```

Fails the task with `stagnated: N identical consecutive outputs`, even with
`on_exhaust: complete`, so its dependents do not run. Use it when a looping
agent can get stuck repeating itself and burning tokens. Must be `>= 2` and
requires `repeat > 1`.

### Loop templating

`{{loop.previous}}` is the prior iteration's output, empty before the first
completes. After a failed try it holds that try's failure text (see
[Failed tries](#failed-tries)), not the last good output. So a loop that
carries state from try to try (a counter, a list of what was tried) should
read it from `{{loop.history}}`, which keeps the earlier tries too. In a shell
step read them as `"$LOOP_PREVIOUS"` and `"$LOOP_HISTORY"`.
`{{loop.history}}` renders every prior iteration as numbered blocks:

```
--- iteration 1 ---
<output>

--- iteration 2 ---
<output>
```

History is trimmed by two settings: `ATELIER_LOOP_HISTORY_LIMIT` (default `10`
iterations, newest kept) and `ATELIER_LOOP_HISTORY_ENTRY_CHARS` (default `40000`
chars per entry, truncated head-and-tail around a marker). Values `<= 0` mean
unlimited.

## Templating

| Expression | Resolves to | On failure |
|---|---|---|
| `{{inputs.<name>}}` | conduit input or HITL answer | **fails** the task |
| `{{<task>.output}}` | that task's output | **skips** the task if the target was skipped/failed/incomplete |
| `{{loop.previous}}` | prior iteration output | `""` before the first iteration |
| `{{loop.history}}` | numbered prior iterations | `""` before the first iteration |
| `{{conduit_dir}}` | absolute dir of the running conduit | unknown-expression error if unavailable |

Anything else inside `{{ }}` is an error: `unknown template expression`.

`{{conduit_dir}}` is how a conduit reaches helper scripts that ship beside it,
which is what makes a package relocatable:

```yaml
task: |
  python3 "{{conduit_dir}}/scripts/pick.py" "$INPUT_PROJECT_DIR"
```

A task referencing `{{other.output}}` must list `other` in `depends_on` - the
reference alone does not create the edge.

## Values in shell steps

In a `tool:bash` step, read values from environment variables, not from
`{{...}}`. Atelier puts a `{{...}}` value into the command text before bash
reads it, so bash runs any `$(...)`, `;` or backtick in the value, even inside
quotes. An input, a human answer or an agent's output can then run commands
on the machine. Bash never runs what is inside a variable. Keep the variable in
double quotes, so spaces and `*` in the value stay as they are:

```yaml
- greet:
    description: greet someone
    tool: tool:bash
    task: echo "hello $INPUT_NAME"
```

Every shell step gets these variables on top of the normal environment:

| Variable | Value of | Present |
|---|---|---|
| `INPUT_<NAME>` | `{{inputs.<name>}}` | for each input, and each HITL answer once given |
| `OUTPUT_<TASK>` | `{{<task>.output}}` | for each finished task in the step's `depends_on` chain |
| `LOOP_ITERATION` | the try number, 1, 2, ... | in a looping task (`repeat > 1`) |
| `LOOP_PREVIOUS` | `{{loop.previous}}` | in a looping task |
| `LOOP_HISTORY` | `{{loop.history}}` | in a looping task |

- **Names.** Upper case, and every character that is not a letter, a digit or
  `_` becomes `_`, so input `repo-url` is `$INPUT_REPO_URL`. If two names give
  the same variable, or one name's variable is the other's `_FILE` form
  (`report` and `report_file`), the name that comes first in sorted order keeps
  it, and the other value is only reachable through `{{...}}`.
- **Large values: the `_FILE` form.** Each value is also written to a file, and
  `<NAME>_FILE` holds its path, for example `cat "$INPUT_NAME_FILE"`. The plain
  variables of one step share one budget of 100,000 bytes. Values the command
  names come first, then the others in name order. A value that does not fit,
  or that has a NUL byte or a broken character, gets only the file form and
  leaves `<NAME>` unset. So read the file when a value can be large, for
  example `< "$OUTPUT_DRAFT_FILE"`. When the command names a variable left
  unset this way, the step's error output starts with a line that says so. The
  files are removed when the step ends.
- **Exact values.** `$OUTPUT_<TASK>` keeps the newline that `echo` printed at
  the end; an unquoted `{{<task>.output}}` only seemed to drop it.
- **They win over your environment.** They replace any variable of the same
  name already set; everything else passes through. A step that read, say,
  `$INPUT_TOKEN` from your environment now gets the `token` input instead when
  the conduit has one.
- **Declare run inputs.** Declare each run input the step reads under
  `inputs:`, so `atelier run` accepts it. A `tool:hitl` answer needs no
  declaration: `$INPUT_<NAME>` holds it once the human answers.
- **Loop bodies.** A step inside a `tool:conduit` loop body does not loop
  itself, so it gets no `LOOP_*` and no `OUTPUT_<TASK>` of the enclosing
  conduit. Forward them under the calling task's `inputs:`
  (`feedback: '{{loop.previous}}'`) and read `"$INPUT_FEEDBACK"`. A variable a
  step does not get is empty.
- **Big commands.** A command up to 32,000 bytes runs as `bash -c`. A bigger
  one runs from a temporary script file; there `$0` names that file. Use
  `"$BASH"`, not `$SHELL`, to start the running bash again.
- **Version.** Atelier 0.12 and earlier set none of these variables, so there
  the step sees them empty. Upgrade before using them.

`{{...}}` still works in shell steps. `atelier check` warns when a shell step
puts `{{inputs.*}}`, `{{<task>.output}}` or `{{loop.*}}` straight into its
command, and names the variable to use instead:

```
⚠ greet: use "$INPUT_NAME" instead of {{inputs.name}}, so the value cannot
run as a command; a value past the step's 100,000-byte budget comes only as
"$INPUT_NAME_FILE"
```

`{{conduit_dir}}` and `{{<task>.workspace}}` are paths you control, so they are
fine in a command. `{{...}}` is also fine where no shell reads it: agent
prompts, HITL prompts, `session`, and the `inputs:` map of a `tool:conduit`
task.

When an input is meant to be shell code, such as a test command, run it
explicitly with `eval "$INPUT_TEST_COMMAND"`, so a reader sees that this one
value runs as code.

## Sinks - what a conduit "returns"

A **sink** is a task no other task depends on. A conduit's output is its sinks'
outputs. This matters in two places:

- A parent `tool:conduit` task's `until` / `while` predicate matches against the
  nested run's outputs and fires on **any** match.
- `outputs.yaml` records every task, but a caller reads the sinks.

Design a sub-conduit so the value you want to carry upward is emitted by a sink
task. If several tasks are sinks, all of their outputs are in scope.

## `tool:hitl`

```yaml
- approve:
    description: human gate
    task: "I need a final confirmation"     # the prompt shown
    tool: tool:hitl
    depends_on: [run_tests]
    inputs:
      confirm: "Type 'yes' to approve deploy"
      reason: "Short reason for the decision"
```

At runtime flow-atelier prints the prompt, asks for each named input on the
terminal, and saves the answers. Downstream tasks read them as
`{{inputs.confirm}}`, and a downstream shell step as `"$INPUT_CONFIRM"` - HITL
answers land in the same namespace as conduit inputs, so avoid names that
collide with declared inputs. Do not declare them under `inputs:` either: that
makes the run ask for them before it starts.

The run blocks until answered. Over the WebSocket API the same gate is delivered
as a message and answered by the client.

## `tool:conduit`

```yaml
- deploy:
    description: Run the deploy sub-conduit
    task: deploy_to_env          # a conduit NAME, not a command
    tool: tool:conduit
    depends_on: [approve]
    inputs:
      target_env: "{{inputs.env}}"
      build_path: /tmp/build
```

The nested run gets its own flow directory under
`.atelier/flows/<parent>/flows/<child>/`. Its `inputs` are resolved in the
parent's template scope before being passed down, so you can thread parent
inputs and upstream task outputs into a child.

Loop a sub-conduit exactly like any other task - see the sinks note above for
what its predicate sees.

## Validation before running

```bash
atelier check              # validate every conduit
atelier check <name>       # just one
atelier plan <name>        # render the DAG, run nothing
```

`atelier check` reports per conduit and names its required inputs:

```
hello [project] - OK
    requires --input: name
loopdemo [project] - OK
```

`atelier plan` validates identically, then renders waves with loop annotations,
conditional edges, gates and sinks:

```
Wave 0
  tick  [tool:bash]  x10 until output.match(done)   gate
      ! if this output misses, it prunes 1 task(s): after

Wave 1
  after  [tool:bash]   sink
      -> tick  ?match(done)
```

Waves are longest-path layering - a static structural view, not a runtime trace.
Real parallelism is also bounded by `max_concurrency` and by conditional skips.
