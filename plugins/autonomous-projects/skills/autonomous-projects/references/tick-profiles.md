# Tick profiles: run only the work you asked for

Every profile names `project_root` and all five counts. A count you leave out
keeps its default, and the proposal defaults are `n_ideas=10`, `n_adhd=3`,
`n_reviews=5`. So `--input n_todo=3` on its own still leaves up to 10 ideas, 3
divergent ideas and 5 reviews enabled next to the approved work.

To adapt a profile, change only the count of the job you want. Keep the other
counts at `0`. Write plain integers such as `3`, not `03`: the tick reads a
count that starts with `0` as disabled.

## Approved work only

Advance existing cards in `01_to-do/` (and resume a card already in
`02_in-progress/`).

```bash
atelier run autonomous-projects --input project_root=/abs/path/to/your/repo \
  --input n_ideas=0 --input n_adhd=0 --input n_reviews=0 --input n_improve=0 --input n_todo=3
```

Board result: each card it picks goes `01_to-do/` -> `02_in-progress/` ->
`03_to-review/` on a DONE verdict, or to `05_blocked/` with a note when the
reviewer never says DONE. Nothing reaches `04_done/`; that stays the human's
move. No new proposals are written.

Stops early when `01_to-do/` runs out of cards, a branch hits `max_usage`, or a
task is blocked.

**Check the queue first.** When approved work is the only job requested, look
before you start the tick:

```bash
b=/abs/path/to/your/repo/.atelier/project
for d in 01_to-do 02_in-progress; do
  if [ -d "$b/$d" ] && [ -r "$b/$d" ] && [ -x "$b/$d" ]; then
    printf '%s: %s\n' "$d" "$(find "$b/$d" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
  else
    printf '%s: unreadable\n' "$d"
  fi
done
```

- Both folders read `0`: report "no approved or in-progress work" and skip the
  tick, unless the user asked to run it anyway. Without this check, an empty
  queue can still launch a worker. The package tells that worker to answer
  `NOTHING TO DO`, but its responses and retries are not fixed.
- Either folder reads `unreadable`: that is not an empty queue. Treat it as a
  setup problem (wrong `project_root`, or the board was never scaffolded) and
  use the setup steps in `../SKILL.md`.
- The check is a snapshot. It is not a lock, and another tick or the human can
  change the board right after it.

Do not use this shortcut for proposal, inbox or mixed requests. Those
authorize other work too.

## Proposals only

Top up `00_backlog/` with new ideas and reviews for the human to triage.

```bash
atelier run autonomous-projects --input project_root=/abs/path/to/your/repo \
  --input n_ideas=2 --input n_adhd=0 --input n_reviews=1 --input n_improve=0 --input n_todo=0
```

Board result: new `idea_*.md` and `review_*.md` (and `adhd_*.md` if you raise
`n_adhd`) in `00_backlog/`. No code changes, and no card moves.

Stops early when a branch hits `max_usage`, or prints `stopped: missing ...`
because a generation step ended before finishing.

## Raw tasks to specs only

Turn the rough `.md` notes in `00_tasks/` into full `task_*.md` cards.

```bash
atelier run autonomous-projects --input project_root=/abs/path/to/your/repo \
  --input n_ideas=0 --input n_adhd=0 --input n_reviews=0 --input n_improve=3 --input n_todo=0
```

Board result: each raw note gets a spec and a plan and is stored as
`task_*.md` in `00_backlog/`, with your wording kept in `# Description`. After
the card is stored, the raw file is deleted from `00_tasks/`. Nothing is
implemented: triage the card to `01_to-do/` and run the approved-work profile.

Stops early when `00_tasks/` is empty (no agent step runs for an empty inbox),
or when a branch hits `max_usage`.

## Mixed requests

When the user names several jobs or exact counts, use exactly their values and
set the counts they did not mention to `0` unless they asked for the defaults.
Keep their `max_usage` if they gave one. Example: "spec the inbox and work two
tasks" is

```bash
atelier run autonomous-projects --input project_root=/abs/path/to/your/repo \
  --input n_ideas=0 --input n_adhd=0 --input n_reviews=0 --input n_improve=5 --input n_todo=2
```

The two queue branches can run side by side. A task spec'd in this tick lands
in `00_backlog/`, not `01_to-do/`, so it is not worked in the same tick.

## What the counts do not limit

Counts limit **activities**, not prompts, time or money.

- One activity can take many agent calls. A divergent idea is about 10. An
  approved task loops builder and reviewer up to 10 rounds, and agent steps can
  retry after errors.
- `max_usage` is a threshold, not a budget. It is checked before a branch and
  before each round. Work already running finishes even if it crosses the
  line. When usage cannot be read (no `node`, unknown harness), the check lets
  the work through.
- Counts above `50` are capped by the branch's `repeat: 50` ceiling.
- Only a count of `0` guarantees that its activity starts no agent work.
