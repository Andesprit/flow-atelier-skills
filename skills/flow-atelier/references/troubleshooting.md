# Troubleshooting

## Reach for these first

```bash
atelier check <conduit>      # schema, deps, loop predicates, template refs
atelier plan <conduit>       # the DAG as waves, with gates and sinks marked
atelier status <flow_id>     # per-task state of a run
atelier logs <flow_id> -t <task> -s all
atelier outputs <flow_id> -t <task>
atelier timing <flow_id>     # where the time actually went
```

`check` and `plan` run no tasks and cost nothing. Run both before blaming the
engine.

## Authoring errors

| Message | Cause | Fix |
|---|---|---|
| `invalid task name 'my-task'` | task names are `[A-Za-z0-9_]` only | use `my_task`. Conduit names may contain hyphens; task names may not |
| `invalid conduit name` | name has `/`, `.`, or `..` | conduit names are `[A-Za-z0-9_-]` - they become a path component |
| `invalid tool 'harness:My_Agent'` | harness names are `^[a-z0-9][a-z0-9-]*$` | lowercase, digits, hyphens |
| `duplicate task names: [...]` | two tasks share a `name` | rename one |
| `until and while are mutually exclusive` | both set | keep one |
| `until requires repeat > 1` | loop predicate on a single-run task | add `repeat: N` |
| `on_exhaust requires until or while` | `on_exhaust` with no predicate | remove it or add a predicate |
| `stagnation_limit requires repeat > 1` / `must be >= 2` | out of range | `>= 2`, and `repeat > 1` |
| `invalid regex in dependency` | the regex does not compile | check escaping; quote the YAML string |
| `dependency must end with ')'` | malformed condition | the regex is everything to the **last** `)` |
| `unknown template expression: 'x'` | `{{x}}` is not `inputs.*`, `<task>.output`, `loop.*`, or `conduit_dir` | fix the expression |
| `missing input: 'name'` | required input not passed | `--input name=value`, or give it a `default` |

## A task was skipped and you did not expect it

`⏭ after [tool:bash] skipped (condition not met: tick.output.match(done))`

Skipping is normal control flow, not an error. Causes, in order of likelihood:

1. **The condition genuinely did not match.** Check what the upstream task
   actually printed: `atelier outputs <flow_id> -t <upstream>`. Agent output
   drifts - a prompt asking for `VERDICT: DONE` may have produced `Verdict:
   done`. Loosen the regex or tighten the prompt.
2. **A loop exhausted without matching.** By default that **completes**
   successfully, so the downstream gate skips and nothing looks wrong. This is
   the most common trap. Add `on_exhaust: fail`.
3. **The upstream task was itself skipped or failed.** Skips propagate down the
   whole subtree.
4. **A template referenced an unavailable task.** `{{other.output}}` where
   `other` was skipped raises a skip on the referencing task, even if
   `depends_on` looked satisfied.

`atelier plan` marks gates and says what each one prunes:

```
tick  [tool:bash]  x10 until output.match(done)   gate
    ! if this output misses, it prunes 1 task(s): after
```

## The regex never matches

- The condition regex is **everything between the marker's `(` and the last `)`**.
  A regex containing `)` needs care.
- Quotes around the pattern are stripped, so `match("PASS")` looks for `PASS`.
  To match a literal quote, escape it: `match(\"PASS\")`.
- Matching is capped at the first **1,000,000 characters** of output. A very
  chatty agent can push its verdict past the cap - ask for the token first, or
  keep the response short.
- `re.search` semantics, so the pattern need not anchor. `^` and `$` are
  line-relative only with an inline flag.

## The flow failed

The run prints the failing task and a resume hint:

```
flow failed: task 'never' exhausted 3 iterations without matching its loop predicate
flow_id: 20260727_09f441fa_exhaust
-> atelier run --resume 20260727_09f441fa_exhaust
```

`--resume` picks up where it stopped. `--again` starts fresh with the same
inputs. Both take a flow id prefix.

Other failure sources:

- **`stagnated: N identical consecutive outputs`** - a looping task produced the
  same output N times. Usually an agent stuck in a rut, or a bash step whose
  state never changes.
- **A task timed out.** The conduit `timeout` (default 3600s) applies per task
  unless the task overrides it. Nested conduits have their own budget - a parent
  looping a 1h child 10 times inside a 2h parent budget will not get 10
  iterations. **Nested timeouts do not compose; check the arithmetic.**
- **Fail-fast.** A failed task cancels siblings still running. If a long branch
  keeps dying with nothing obviously wrong in it, look at what failed elsewhere
  in the same wave. When one branch's failure should not kill the others, make
  its check non-fatal: exit 0 and emit a value the next task gates on.

## Harness problems

A harness task failing usually is not a conduit problem.

```bash
atelier harness check <name>      # costs no tokens
```

| Result | Fix |
|---|---|
| not found on PATH | install the agent yourself |
| started but did not speak ACP | wrong entry point - most CLIs need `--acp` |
| could not open a session | not logged in; the check lists the auth methods |

Failures include the tail of the agent's own stderr. `atelier harness list --ready`
shows what actually runs on this machine. If a name resolves to an `npx`/`uvx`
agent, Node.js or uv must be on PATH.

## The wrong conduit ran

Conduits resolve **project first, then global**. A `./.atelier/conduits/<name>/`
silently overrides `~/.atelier/conduits/<name>/`. `atelier list conduits` shows
each one's source, tagged `[project]` or `[global]`.

Flows are always written relative to the working directory you ran `atelier`
from, so running the same conduit from two directories scatters the flow history.

## A package upgrade did nothing

`atelier add` **skips** conduits that already exist. Re-running it after a release
changes nothing. Use `atelier update <package>`, or `atelier add <source> --force`.

`atelier remove <package>` deletes only conduits the install actually wrote, so
one skipped on collision survives an uninstall.

## The scheduler is not firing

- `atelier scheduler status` reads the files directly and **does not contact a
  daemon**. It cannot tell you the daemon is alive - check the process.
- New or removed schedules are picked up on the next reload tick (default 30s).
- A `once` schedule whose `run_at` is in the past is rejected at install time; one
  that already fired is remembered in `.atelier/scheduler_state.json` and never
  re-runs.
- Each schedule runs at most one instance at a time, and missed fires are
  coalesced rather than queued.
- The CLI installs to `./.atelier/schedules/`; `atelier serve` reads
  `~/.atelier/schedules/`. A schedule added on the CLI in a project directory
  will not show up in the UI.

## Reading a finished run

```
.atelier/flows/<YYYYMMDD>_<uuid8>_<conduit>/
  input.yaml       the inputs this run was given
  logs.jsonl       append-only, one JSON object per line
  progress.json    live per-task status
  outputs.yaml     per-task outputs, written as tasks finish
  flows/<child>/   nested tool:conduit runs, same shape
```

`outputs.yaml` keeps only the **last** iteration of a looped task and records
`null` for skipped ones:

```yaml
tick: 'tick 1

  '
after: null
```

For per-iteration detail use `atelier logs <flow_id> -t <task> -s all`. For
nested runs, `GET /flows/:id/logs` returns the whole descendant tree in one
response; on the CLI, descend into `flows/<child_flow_id>/` yourself.
