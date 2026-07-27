# How a tick actually works

Read this when debugging the package itself, changing a conduit, or explaining
why a branch behaved the way it did. For everyday setup and running, `SKILL.md`
is enough.

Everything lives under `.atelier/conduits/` in the package.

## The DAG

One `atelier run autonomous-projects` is one tick:

```
dep_guard --+--> counts ------------------+
            +--> usage_ideas              +--> generate_ideas      (n_ideas>0   & ok)
            +--> usage_adhd               +--> generate_adhd_ideas (n_adhd>0    & ok)
            +--> usage_reviews            +--> generate_reviews    (n_reviews>0 & ok)
            +--> usage_improve            +--> improve_tasks       (n_improve>0 & ok)
            +--> usage_todo               +--> do_tasks            (n_todo>0    & ok)
```

`max_concurrency: 3`, so the three proposal branches run at the same time and a
tick costs about as long as its slowest branch. `improve_tasks` and `do_tasks`
are declared last and take slots as the proposal branches finish. Within a
branch, iterations are sequential, so each new idea sees the ones before it.
Across branches they do not - an idea and an adhd idea from the same tick cannot
read each other, so occasionally two land on the same theme. Triage catches it.

**The engine is fail-fast**: a task that fails cancels every sibling still
running. That constraint explains most of the defensive design below.

### `dep_guard`

The DAG root. Fails the tick, with a named message, on:

- a missing hard dependency on `PATH`: `python3`, `npx`, `claude`
- a `project_root` with no `.atelier/project/project.md` in it

Everything else only warns: missing `node` (the usage gate stops throttling),
a missing agent-skills plugin, a missing `adhd` skill. Those degrade one step
rather than breaking the tick.

### `counts`

Echoes the per-tick counts so each branch can gate on its own count being
non-zero. A `depends_on` cannot read a run input directly, but it can match a
task's output, hence the echo:

```
n_ideas: 2
n_adhd: 0
...
```

Each branch depends on `counts.output.match(n_ideas:\s*[1-9])`.

### `usage_*` - the only gate

For each activity a `usage_*` task resolves the harness declared in that
activity's sub-conduit, reads its live 5h usage percentage via `scripts/usage.mjs`
(Claude Code's own local rate-limit cache, no network), and prints `ok: true`
while under `max_usage`, else `ok: false`.

Everything about this fails open. Unreadable usage, an unknown harness, an
unparseable ceiling: all produce `ok: true`, and the check always exits 0. A
broken reading must never block work.

That check runs once, before the branch starts, which is not enough on its own:
`n_ideas=10` is a branch that can run for an hour, starting under the ceiling and
spending well past it. So the ceiling is re-read **inside** each branch too - the
same `count` step that stops the loop at `n_*` also calls the usage gate and
emits `stopped: usage ceiling reached` at the first iteration at or over the
ceiling. The branch ends there with its finished work kept.

## How a loop stops at N

The engine requires `repeat:` to be a literal integer and `until:` a fixed
regex - neither can read a runtime `--input`. So each branch loops to a literal
`repeat: 50` safety ceiling and a counter inside the sub-conduit stops it at the
requested `n_*`:

- A leading `count` step reads the tally carried in `{{loop.previous}}` and, once
  `n_*` activities have run, emits `remaining: 0`, which trips the branch's
  `until: output.match(remaining:\s*0)`.
- A trailing `advance` step bumps the tally (`made: K`) and recomputes
  `remaining`, so the next iteration sees the new count.

`improve_tasks` and `do_tasks` also stop when their queue drains, via
`task_counter: 0`, so each runs `min(n_*, work available)`.

The consequence worth remembering: **`n_* > 50` is silently capped at 50.**

## Output contracts

All four generation branches gate on `require_markers.py` before storing.
`generate_idea`, `diverge` (adhd), `generate_review` and `improve_task` each have
to produce their `===...START===` / `===...END===` block plus a slug line, or the
branch stops with `remaining: 0` and stores nothing.

This exists because a step can end its turn early - the adhd one is prone to
stopping after launching its parallel branches - and the store step would then
assemble a proposal document out of model narration. In `improve-task` the stakes
are higher still: that branch deletes the raw inbox file once the card is stored,
so an ungated miss would destroy the user's original task on the way out.

The gate is deliberately **not** fatal. It always exits 0 and reports a verdict
the conduit branches on, because raising would cancel every sibling branch still
running.

## The two-agent execution loop (`work-one-todo`)

For each to-do task:

1. **Pick by priority** (`pick_next_task.py`) - sorts `01_to-do/*.md` by
   (`priority` ascending, then filename). Missing or blank priority sorts last.
2. **Build and review in a loop** - loops `task-with-review` up to 10 times until
   the reviewer returns `VERDICT: DONE`.
   - The **builder** claims the task first (moves it to `02_in-progress/` before
     anything else, so the board shows it immediately), resumes any task already
     there, reads `project.md` for the goal and binding constraints, skims
     `04_done/` and `03_to-review/` for memory, does the work, and runs the
     **full** test suite - `test_command` if set, else a conventional one. It
     records exact pass/fail counts, never moves a task with red tests, and says
     so plainly when there are no tests rather than faking a pass. It stages
     only the files it touched by explicit path: never `git add -A`, `git add .`
     or `commit -a`, because the board holds unrelated proposals dropped the same
     tick and possibly the human's own uncommitted edits.
   - The **reviewer** independently re-runs the suite itself and judges two
     things: Completion (was it actually done?) and Alignment (does it serve the
     goal and respect every constraint?). Either failing returns `NOT_DONE`, and
     the reason becomes the next iteration's priority. Skipped entirely when the
     builder reports `NOTHING TO DO`.
3. **Promote on DONE** (`promote_reviewed.py`) - moves the card from
   `02_in-progress/` to `03_to-review/`. Keeping this out of the builder's own
   "I think I am done" step is what lets a NOT_DONE verdict retry the card and
   lets the stranded sweep park it.
4. **Park stranded work** (`block_stranded.py`) - runs only when the loop ended
   without DONE. Moves anything left in `02_in-progress/` to `05_blocked/` with a
   `# Blocked` note, so it stops being silently retried every tick.
5. **Count** - `bump` advances the per-tick counter and `count_todo` emits
   `task_counter: N`, so the loop stops at whichever cap is smaller.

Whether the bot commits is auto-detected: if `project_root` is a git repository
it commits each task, otherwise it just edits files.

## Helper scripts

All pure stdlib Python, all unit-tested, all exit 0.

| Script | Contract |
|---|---|
| `usage_check.py` | `ok: true\|false` - resolves the activity's harness, fail-open |
| `usage.mjs` | `<label>: <pct>%` for claudecode, codex, opencode from local data |
| `loop_count.py` | `made:` / `remaining:` per-tick counter plus the per-iteration usage re-check |
| `require_markers.py` | `ok: true`, or `ok: false` + `remaining: 0` + `stopped: <reason>` |
| `remove_picked.py` | `removed: <path>\|none` - deletes exactly the picked inbox file |
| `count_tasks.py` | `task_counter: <int>` |
| `pick_next_task.py` | bare filename of the highest-priority to-do, or empty |
| `promote_reviewed.py` | `promoted: <path>\|none` |
| `block_stranded.py` | `blocked: <path>` per file, or `blocked: none` |
| `new_project.py` | scaffolder, atomic (builds in a temp dir, renames on success) |
| `tick_lock.py` | single-flight OS advisory lock wrapper |

Tests live in `scripts/tests/` and run from `scripts/`:

```bash
cd .atelier/conduits/autonomous-projects/scripts
uv sync --group dev
uv run pytest -q
```

Modules that live beside another conduit (`pick_next_task.py`,
`promote_reviewed.py` under `work-one-todo/scripts/`) are tested from this same
project, which reaches sideways for them. Keep new tests here so they are
actually collected.

## Known sharp edges

Real, in the shipped design, worth knowing before blaming your own setup:

- **Nested timeouts do not compose.** `work-one-todo` has `timeout: 7200`, but it
  loops `task-with-review` (`timeout: 3600`) up to 10 times. Worst case is 10h
  inside a 2h budget, so the advertised 10 retries is unreachable - you get two
  or three slow iterations and then a timeout kill. Same shape at the parent:
  `n_todo=5` at 2h each against a 6h tick timeout.
- **`# What was done` is a dead section.** It is in `task_template.md` and the
  generation prompts describe it as recording the result of finished tasks, but
  no step ever writes it. Only `# How was done and tested` gets filled.
- **`count_tasks.py` conflates "drained" with "unreadable".** Any exception
  returns `task_counter: 0`, which the parent reads as *queue empty, stop*. A
  permissions problem on `01_to-do/` looks exactly like an empty queue.
- **`promote_reviewed.py` promotes `sorted(cards)[0]`,** not necessarily the card
  the builder worked. Only reachable when two ticks overlap, but under that race
  it promotes an unfinished card and leaves the finished one to be re-worked.
- **Overlapping ticks are not guarded by `atelier scheduler`.** `tick_lock.py`
  wraps a command, so it covers cron and custom timers only.
