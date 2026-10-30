---
name: managing-managers
description: Turn a conversation about one or more improvements into a confirmed, ordered queue of small written briefs, then run them with the managing-managers Flow Atelier package - an Opus manager plans and judges, Codex workers build, fresh Codex reviewers review, and each brief ends in its own stacked pull request. Use when the user wants several changes built from written briefs, says "managing managers", "make briefs", "brief queue", "run these briefs", or asks for brief-driven work that stops when the brief is met. Also use to inspect, resume or troubleshoot a managing_managers run. Distinct from automatic-goal, which works against a clock.
---

# Managing managers

Source: https://github.com/Andesprit/managing-managers

A written brief, not a clock, decides what gets built and when work stops. This skill writes
the briefs with the user, then starts the `managing_managers` conduit. Installing or inspecting
does not authorize starting agents: start a run only after the user confirms the queue.

## 1. Write the briefs

1. Let the user describe what they want, often several things at once.
2. Ask short clarifying questions, at most three per brief. Ask what "done" looks like when it is
   not clear, and which files or areas must not change.
3. Write one brief per item. Keep each brief small: if an item needs more than about six
   outcomes or touches unrelated areas, split it into several briefs.
4. Show the queue in order (number, title, one-line goal) and ask the user to confirm or reorder.
   Later briefs stack on earlier ones, so put foundations first.

Each brief is a Markdown file in `.atelier/briefs/` of the run's worktree, named
`NN-short-name.md` (lowercase letters, digits and dashes). The file order is the queue order.
The files are untracked, so they never land in a pull request, and the user may edit them
between runs. Use exactly these headings; the controller reads the title, Goal, In scope,
Allowed paths and Definition of done:

```markdown
# Show a clear message on a wrong password

## Goal
Users who mistype their password see why login failed, instead of a stack trace.

## In scope
- The login form's error handling

## Out of scope
- Password reset
- Rate limiting

## Constraints
- No new dependencies

## Allowed paths
- src/login/*
- tests/test_login.py

## Definition of done
- The test suite passes
- A wrong password shows "Wrong password" and no stack trace

## Notes
The message text is already in src/login/messages.py.
```

- Definition of done: one to six `- ` items, each checkable. Each is later measured by a command
  or judged by the manager against stated evidence. Avoid vague words such as "polished" or
  "better".
- Allowed paths is optional. When present, the controller rejects any change outside these glob
  patterns (`*` also matches `/`). Leave it out when the user cannot say which files will change.

## 2. Prepare the worktree

Runs need a clean, dedicated linked worktree on its own branch; the main checkout, detached HEAD
and tracked `.atelier/` files are refused. Each brief gets a branch `mm/<brief-name>` created from
the previous brief's branch.

```bash
cd /path/to/project
git worktree add ../project-briefs -b mm/run
cd ../project-briefs
atelier add Andesprit/managing-managers --project
atelier harness sync
atelier check managing_managers --recursive --probe
```

Write the brief files into this worktree's `.atelier/briefs/`. Check `atelier --version`
(0.12.0 or newer). `atelier harness sync` refreshes the agents before an unattended run; the
probe opens each agent's session without sending a prompt. For pull requests, `origin` must exist
and `gh auth status` must pass; otherwise branches stay local and the run says why.

## 3. Run

```bash
CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 atelier run managing_managers
```

Useful inputs (`--input name=value`), all trusted operator values:

| Input | Default | Meaning |
| --- | --- | --- |
| `hours` | 12 | Safety cap for the whole run; never a reason to keep working |
| `max_review_rounds` | 6 | Hard cap on review rounds per brief |
| `max_task_turns` | 6 | Worker turns per task before the manager must accept, abandon or pause |
| `pull_request` | true | Push each finished brief and open its pull request |
| `pull_request_base` | default branch | Target of the first brief's pull request |
| `min_claude_weekly_remaining`, `min_claude_5h_remaining`, `min_codex_remaining` | 40, 30, 30 | Usage floors; below one the run waits instead of failing |
| `claude_weekly_model` | all | Claude weekly meter the floor reads (`all` or a model display name) |

To change who manages, works or reviews, pass `--agent` and never edit the conduits. Keep the
manager on one agent so it keeps one conversation per brief:

```bash
--agent queue.brief.manage=claude-code:opus:xhigh \
--agent queue.brief.work=codex:<model> --agent queue.brief.review=codex:<model>
```

Take model names from `atelier harness check <agent>`.

## How a brief runs

1. Plan: the manager turns the definition of done into a scorecard and small tasks, each tied to
   an outcome. The controller runs measured outcomes itself.
2. Work: a Codex worker builds one task in its own conversation. It may stop with a question; the
   manager answers and the same conversation continues.
3. Check: the manager accepts (naming the outcome the task advances), sends it back, abandons it
   (commits kept under `refs/managing-managers/...`) or pauses for the user.
4. Review: a fresh Codex reviewer reviews the whole brief each round. Findings are critical, high,
   medium or low, and tied to the brief or to correctness; anything else is a suggestion.
   Critical and high findings go back to the worker conversation that built that code.
   - Rounds 1-3 close when there is no critical and no high finding.
   - After round 3 the loop closes when there is no critical finding; remaining high findings are
     listed in the pull request.
   - If critical findings remain after the last round, the brief pauses and the queue stops.
5. Finish: the manager judges the outcomes and writes the pull request. The controller appends
   its report: definition of done met or not, review rounds, remaining findings, out-of-scope
   suggestions, and up to three questions. A brief whose definition of done is not met opens a
   draft pull request.

## Inspect and recover

- `.atelier/mm/summary.md`: one line per brief with status and pull request.
- `.atelier/mm/briefs/<id>/report.md`: the brief's report; `state.json`: full record.
- `atelier status` and `atelier diagnose <flow_id>` for engine-level failures; resume with
  `atelier run --resume <flow_id>`.
- A paused brief stops the queue. After reading its report, start it over by deleting
  `.atelier/mm/briefs/<id>/` and branch `mm/<id>` (check out the previous brief's branch first),
  then run again. A rerun skips finished briefs and adds new brief files to the end of the queue.

Report results in plain words: what each brief changed, which outcomes are met, what the
reviewers left open, and which pull requests need the user.
