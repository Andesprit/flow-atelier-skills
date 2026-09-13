# Diagnostics and board recovery

The symptom table in `SKILL.md` covers the common cases. This file is for when
that is not enough: how to inspect a board by hand, how to recover a stuck one,
and how to read what a tick actually reported.

## First: look at the board, not the logs

Almost every "it did nothing" report is answered by listing the stage folders.

```bash
P=/abs/path/to/your/repo/.atelier/project
for d in 00_tasks 00_backlog 01_to-do 02_in-progress 03_to-review 04_done 05_blocked; do
  printf '%-16s %s\n' "$d" "$(ls -1 "$P/$d" 2>/dev/null | wc -l | tr -d ' ')"
done
```

How to read it:

- `00_backlog` growing, `01_to-do` empty: working as designed. Nothing happens
  until the human triages proposals into `01_to-do/`.
- `01_to-do` non-empty across several runs: the runs are not naming `n_todo`. It
  defaults to `0`.
- A card sitting in `02_in-progress` between ticks: a run was cut off before the
  stranded sweep. The next tick's builder resumes it, which is the intended
  recovery. Leave it alone unless it has been stuck for several ticks.
- `05_blocked` growing: the reviewer keeps refusing to sign off. Read the cards.
- Everything empty after a run that reported success: wrong `project_root`. Check
  whether a stray `.atelier/project/` was created somewhere unexpected.

## Reading a tick's output

The helper scripts have fixed stdout contracts. Grep for these:

| Line | Meaning |
|---|---|
| `deps ok` | `dep_guard` passed |
| `warning: ...` | A soft dependency is missing. The tick continues, degraded |
| `ok: true` / `ok: false` | Usage gate before a branch |
| `made: N` / `remaining: N` | Per-tick counter. `remaining: 0` ends that branch |
| `stopped: usage ceiling reached` | Branch hit `max_usage` mid-loop |
| `stopped: missing ===IDEA START===` | Generation step returned no usable block |
| `task_counter: N` | Files left in the queue or inbox. `0` ends that branch |
| `promoted: <path>` | A card moved to `03_to-review/` |
| `blocked: <path>` | A card was parked in `05_blocked/` |
| `removed: <path>` | A raw inbox file was deleted after being spec'd |

`remaining: 0` stops one branch and deliberately leaves the others running. A
branch stopping is not a tick failing.

## Recovering a stuck board

All of it is files. Move them by hand.

**A card is wrongly in `05_blocked/`.** Read its `# Blocked` note and
`# How was done and tested` to see what the reviewer kept rejecting. Fix the
blocker (usually a failing test suite or a constraint conflict), delete the
`# Blocked` section, and move the card back to `01_to-do/`.

**A card is stuck in `02_in-progress/`.** Decide whether the work landed. Check
the repo's git log for the task's commits and read the card's
`# How was done and tested`. If the work is done, move it to `03_to-review/`
yourself. If not, move it back to `01_to-do/` so the next tick restarts it
cleanly.

**Two cards are in `02_in-progress/`.** That means two ticks overlapped. Sort out
which is real by git log, move the finished one to `03_to-review/` and the other
back to `01_to-do/`, then widen the schedule spacing before running again.

**The same idea keeps getting proposed.** The generation steps read
`00_abandoned/` and respect the reasoning in each file. Move the unwanted
proposal there and **write why** in the file. An abandoned file with no
explanation teaches the bot nothing.

**The board is fine but proposals are vague.** That is `project.md`. An empty
`# Goal` produces generic ideas. Fill in the goal and constraints; they are the
only steering the generation steps get.

## Cost control

Ordered by how much they save:

1. `--input n_adhd=0`. The divergent branch is roughly 10 agent calls per idea,
   so the default `3` is about 30 calls before anything else runs.
2. Lower `n_ideas`. The default `10` is ten sequential activities in one branch.
3. Lower `max_usage` (say `60`) so branches bow out earlier. Note this is a
   ceiling check, not a budget: it stops new activities, it does not cap a
   running one.
4. Split proposal ticks from execution ticks. Run
   `n_ideas=2 n_adhd=0 n_reviews=1 n_todo=0` to top up cheaply, and a separate
   `n_ideas=0 n_adhd=0 n_reviews=0 n_todo=3` to burn down the queue.

If `max_usage` never seems to throttle: it fails open by design. Check `node` is
on `PATH`, and look for `warning: no usage label for harness <name>`, which means
a conduit's `tool:` was renamed without updating the label map in
`usage_check.py`.

## When the tests are the problem

The builder will not move a task with red tests, and the reviewer independently
re-runs the suite before signing off. So a project with a flaky or broken suite
produces tasks that loop to the retry cap and land in `05_blocked/`.

Check by running the project's own `test_command` by hand. If the suite is red
before the bot touches anything, fix that first - no amount of tuning gets work
through the gate while it is failing.

If the project genuinely has no automated tests, leave `test_command` empty. Both
agents are instructed to state that plainly rather than claim a pass, and a DONE
verdict is never allowed on the builder's self-reported result alone.

## Escalation checklist

Before concluding the package is broken:

1. `atelier list conduits` shows `autonomous-projects`.
2. `python3`, `npx`, `claude` and `node` are all on `PATH`.
3. `/agent-skills:` lists `spec`, `plan`, `review`, `build` inside Claude Code.
4. `<project_root>/.atelier/project/project.md` exists and has a real `# Goal`.
5. `project_root` is absolute and points at the repo you expect.
6. The package's own suite passes:
   `cd .atelier/conduits/autonomous-projects/scripts && uv run pytest -q`.
