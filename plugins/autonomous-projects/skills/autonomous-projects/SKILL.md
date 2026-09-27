---
name: autonomous-projects
description: Set up, run, tune, schedule and debug the autonomous-projects flow-atelier package - the tick-based bot that proposes ideas and code reviews into a repo's .atelier/project/ board and implements approved tasks behind a two-agent review gate. Use when the user mentions autonomous-projects, running a "tick", the .atelier/project/ board or its numbered stage folders (00_backlog, 00_tasks, 01_to-do, 02_in-progress, 03_to-review, 04_done, 05_blocked), the n_ideas/n_adhd/n_reviews/n_improve/n_todo counts, max_usage, scaffold-project, work-one-todo, or asks why a tick produced nothing, stalled, parked a task as blocked, or burned through their quota. Also use when setting the board up on a new repo, feeding it tasks, triaging its proposals, or scheduling ticks.
version: 1.0.0
---

# autonomous-projects

A flow-atelier package that turns a repo into a stream of small, reviewed
improvements. Each **tick** studies the project, proposes ideas and code
reviews, specs raw tasks, and advances approved work - with a second agent
re-running the tests before anything reaches the human.

Source: <https://github.com/LGuillermoAngaritaG/autonomous-projects>

## The one mental model

**The bot proposes and implements. The human decides what is worth doing and
what is actually done.**

Proposals land in `00_backlog/`. The human drags good ones into `01_to-do/`.
The bot works those, and parks the finished card in `03_to-review/`.

Three rules that are not negotiable when you are helping someone with this:

- **Never move a card to `04_done/`.** That is the human's judgment, always.
  Do not do it for them, even when the work obviously looks finished.
- **`project.md` belongs to the human.** Read it, never edit it. Its
  `# Constraints` are binding on every task.
- **Do not pre-fill `# Spec` / `# Plan` / `# What was done` /
  `# How was done and tested`.** Those are the bot's to write. The human owns
  `project.md` and a task's `# Description`.

## Setup on a new repo

Four things, in order. Verify each before moving on - the failures are much
cheaper to catch here than mid-tick.

**1. flow-atelier and the package**

```bash
uv tool install flow-atelier
atelier add LGuillermoAngaritaG/autonomous-projects
atelier list conduits
```

`atelier list conduits` must show `autonomous-projects`. Note `atelier add`
skips conduits that already exist, so re-running it after a release changes
nothing - use `atelier update autonomous-projects` or `atelier add --force`.

**2. The agent-skills plugin** (inside Claude Code, both lines)

```
/plugin marketplace add addyosmani/agent-skills
/plugin install agent-skills@addy-agent-skills
```

This must be the **plugin** install. `npx skills add addyosmani/agent-skills`
installs the skills but not the slash commands, so the conduits'
`/agent-skills:spec|plan|review|build` lines will not resolve. Verify by typing
`/agent-skills:` in Claude Code and confirming `spec`, `plan`, `review` and
`build` are listed.

**3. The adhd skill** (drives the divergent-ideation branch)

```bash
npx skills add UditAkhourii/adhd
```

This one is a skill, not a plugin command. Without it the `n_adhd` branch
degrades to an ordinary single-shot idea. Skip the install and run with
`--input n_adhd=0` if that branch is not wanted.

**4. Scaffold the board into the target repo**

```bash
atelier run scaffold-project --input project_root=/abs/path/to/your/repo
```

Then open `<repo>/.atelier/project/project.md` and fill in `# Goal` and
`# Constraints`, optionally a `test_command:` in the frontmatter. An empty
goal produces vague proposals; this file is the single thing steering quality.

`project_root` must be an **absolute** path. The tick fails fast with
`no project at <path>/.atelier/project/` when it points somewhere without a
board, so a typo stops up front instead of writing a board where it does not
belong.

## Run a tick

```bash
atelier run autonomous-projects --input project_root=/abs/path/to/your/repo \
  --input n_ideas=2 --input n_adhd=0 --input n_reviews=1 --input n_todo=3
```

| Input | Default | What it does |
|---|---|---|
| `project_root` | *required* | Absolute path to the repo holding `.atelier/project/`. This is the codebase the bot edits. |
| `n_ideas` | `10` | Straightforward ideas into `00_backlog/` |
| `n_adhd` | `3` | Divergent (adhd skill) ideas into `00_backlog/`. **Roughly 10 agent calls each.** |
| `n_reviews` | `5` | Code reviews into `00_backlog/` |
| `n_improve` | `0` | Raw tasks drained from `00_tasks/` and spec'd into `00_backlog/` |
| `n_todo` | `0` | Approved tasks advanced from `01_to-do/` |
| `max_usage` | `80` | Skip an activity when its harness's live 5h usage is at or over this percentage |

Naming a count overrides its default; unnamed ones keep theirs. Set any to `0`
to skip that activity.

**Show the run page.** When the tick starts it prints
`· run page http://127.0.0.1:8000/runs/<flow_id>`: a live map of the tick's
activities with each agent's log, much like an artifact. Give the user that link
as soon as the flow starts and again in your report. The page loads only while
`atelier serve` runs from the directory you ran `atelier run` in (flows live
there, not under `project_root`). Check it with
`curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/flows/<flow_id>`:
`200` is ready; `401` means `ATELIER_API_TOKEN` is set and the page asks for it
once. Otherwise start a server from that directory with
`nohup atelier serve --idle-exit 30 > .atelier/serve.log 2>&1 &` (add
`--port <free port>` and change the link if 8000 answers `404`, which means it
serves another directory). It stops by itself 30 minutes after the tick ends and
the page is closed; if the installed atelier rejects `--idle-exit`, drop the flag
and tell the user it keeps running until they stop it. Tell the user you started
it and that, while up, it also fires the schedules in `~/.atelier/schedules/`. No
`run page` line means
the installed atelier (0.7.0 or earlier) has no page; say so instead of sending a
dead link.

**A bare run is not cheap.** The proposal counts default to 10 / 3 / 5, which is
18 AI activities, and the divergent ones are about 10 agent calls apiece. Expect
a long, quota-hungry tick. Only the queue counts (`n_improve`, `n_todo`) default
to `0`, so a bare run tops up the backlog and never touches approved work.

Counts above `50` are silently capped: each branch loops to a literal `repeat: 50`
safety ceiling.

## The board

```
bot:  00_backlog/  ---->  02_in-progress/  ---->  03_to-review/
you:        \----> 01_to-do/                            \---> 04_done/
you drop raw tasks > 00_tasks/ --(bot specs them)--> 00_backlog/
stalled task > 05_blocked/ (bot parks what it could not finish, with a note)
```

- Bot writes `idea_*.md`, `adhd_*.md`, `review_*.md`, `task_*.md` into `00_backlog/`.
- Human triages: good to `01_to-do/`, bad to `00_abandoned/`. **Leave a why-note
  in the abandoned file** - the generation steps read that folder and steer away
  from that kind of proposal.
- Bot picks the lowest `priority:` number in `01_to-do/` (ties by filename,
  blank sorts last), moves it to `02_in-progress/`, builds it, then a second
  agent independently re-runs the tests and returns DONE or NOT_DONE, up to 10
  retries. On DONE the card moves to `03_to-review/`.
- Human approves: `03_to-review/` to `04_done/`.

`05_blocked/` is created on demand, not at scaffold time, so an untouched board
has no empty "something went wrong" folder.

Generated proposals get default priorities: **tasks 1, reviews 2, ideas 3**. Set
`priority:` by hand to override what runs first.

## Getting work actually done

This is the most common point of confusion. Proposals in `00_backlog/` are
**not** a queue. Two ways to get the bot to do work rather than propose it:

1. **Drop a raw task** into `00_tasks/` - a `.md` file with whatever you want,
   even one rough line, no frontmatter needed. Run with `--input n_improve=N`.
   The bot runs spec + plan on it, writes a polished `task_*.md` into
   `00_backlog/` with your wording carried verbatim into `# Description`, and
   deletes the raw file. Then triage it to `01_to-do/` like any proposal.
2. **Write a ready task** straight into `01_to-do/` and run `--input n_todo=N`.
   Skips the spec/plan step. Copy the shape of the package's
   `.atelier/conduits/autonomous-projects/references/task_template.md`; you only
   need to fill `# Description` and set `priority`.

Either way, **`n_todo` defaults to `0`** - a task sitting in `01_to-do/` is
never touched until a run names `n_todo`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no project at <path>/.atelier/project/` | `project_root` is wrong, relative, or never scaffolded | Use an absolute path; run `scaffold-project` |
| `missing dependency: python3 \| npx \| claude` | Hard dep off `PATH` | Install it. These three stop the tick by design |
| Ran a tick, `00_backlog/` is empty | Branch stopped early | Look for `stopped:` in the output - see the two rows below |
| `stopped: usage ceiling reached` | Harness at or over `max_usage` | Wait for the 5h window, or raise `max_usage` |
| `stopped: missing ===IDEA START===` | Generation step ended its turn before finishing | Re-run. Finished work from that branch is kept |
| Approved task never got implemented | `n_todo` defaults to `0`, or the card is still in `00_backlog/` | Move it to `01_to-do/` and run with `n_todo=N` |
| Task ended up in `05_blocked/` | Reviewer never returned DONE within 10 retries, or the run was cut off | Read the `# Blocked` note and `# How was done and tested`, fix the blocker, move it back to `01_to-do/` |
| Quota disappeared | `n_adhd` is ~10 agent calls per idea | Run with `n_adhd=0` |
| `warning: adhd skill not found` | Skill not installed | `npx skills add UditAkhourii/adhd`, or accept the single-shot degrade |
| `/agent-skills:*` did not resolve | Installed as skills, not as a plugin | Use `/plugin install agent-skills@addy-agent-skills` |
| `max_usage` never throttles anything | `node` missing, or `warning: no usage label for harness` | Install node. The gate fails open by design, so it never blocks work |
| Two ticks raced over the same board | Schedule interval shorter than the real tick duration | Widen the spacing. `tick_lock.py` wraps a *command*, so it covers cron but not `atelier scheduler` |

Reading tick output: `ok: true|false` is a usage gate, `made: N` / `remaining: N`
is the per-tick counter, `task_counter: N` is a queue-drain check, and
`stopped: <reason>` says why a branch ended early. `remaining: 0` stops one
branch and leaves the others running.

Deeper diagnostics, including how to inspect a stuck board by hand:
`references/troubleshooting.md`.

## Schedule it

One schedule file per repo:

```yaml
conduit_name: autonomous-projects
run_path: /abs/path/to/your/repo
inputs:
  project_root: /abs/path/to/your/repo
  n_ideas: "2"
  n_adhd: "0"
  n_reviews: "1"
  n_todo: "5"
  max_usage: "80"
schedule:
  mode: interval
  name: autonomous-projects-30min
  every_minutes: 30
  timezone: America/Bogota
```

```bash
atelier schedule add path/to/schedule.yaml
atelier scheduler start
```

Name every count you care about - anything omitted keeps its default, so
leaving out `n_adhd` schedules 3 divergent ideas (about 30 agent calls) every
tick. Four ready-to-edit example profiles ship in the package under
`.atelier/schedules/`, but they are examples, not installed state.

**Overlap matters.** A tick can run for hours. On a short interval a slow tick
is still working when the next fires, and the two race over the same board -
most visibly `02_in-progress/`, which the stranded-task sweep clears wholesale.
Set the interval wider than a real tick. To make it airtight, drive ticks from
cron wrapped in the package's `tick_lock.py` instead of `atelier scheduler`:

```bash
python3 <package>/.atelier/conduits/autonomous-projects/scripts/tick_lock.py \
  atelier run autonomous-projects --input project_root=/abs/path/to/your/repo
```

## References

- `references/architecture.md` - the tick DAG, the usage gates, how a loop stops
  at N, the two-agent execution loop, and the helper scripts. Read this when
  debugging the package itself or changing a conduit.
- `references/troubleshooting.md` - expanded diagnostics, board recovery by
  hand, and known sharp edges.
