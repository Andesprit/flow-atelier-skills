---
name: goal-report
description: Summarize an automatic-goal session's outcomes, completed changes, discarded approaches, unfinished work, evidence and elapsed time from saved records.
---

# Goal report

Use the automatic-goal package's shared reader, which also powers goal-monitor.
Locate the project and its installed `.atelier/conduits/goal_loop/scripts/observe.py`.
Use a Python interpreter with PyYAML, such as Atelier's environment. If the reader is
missing, inspect the installed version and local edits before installing/updating the
package. Do not replace conduits underneath an active run; upgrade both conduits together.
Legacy KEEP/DISCARD flows must not resume using the new stage-based workflow.

```sh
python /path/to/observe.py report --root /path/to/project
python /path/to/observe.py report --root /path/to/project --details
python /path/to/observe.py json --root /path/to/project
```

The reader discovers saved goal_loop runs across Git worktrees; exports cover all discovered
sessions. Select the requested session by path and start time in the structured snapshot
when composing a response; when unspecified, summarize the newest session. The parent flow's
`initialize` output binds modern reports to `runs/<run-id>/state.json`, not the worktree's
latest `.atelier/goal` pointer. Save exports only to a requested destination or ignored
`.atelier/` directory. `--details` adds full reviews and technical history.

## Present the whole session

Lead with the requested goal, recorded outcome status and elapsed time. Then show all
completed improvements and still-open work so the user can understand the session at a
glance. Keep short titles, with one plain-language paragraph per completed change:
what changed for the user, why it was worth doing, and how it works. Typically three to
five sentences is enough; include a meaningful tradeoff when relevant. A repaired
milestone is one completed change, summarized across its full implementation, not just
the last repair.

Give each discarded idea a paragraph too: what was attempted, the intended benefit,
how the approach worked, and the evidence and reason for dropping it. Preserve the
implementation context alongside the rejection reason. Explain deferred or unfinished
work separately; an exhausted repair budget does not establish that the idea lacked
value. Use saved implementation summaries, benefits, review reasons and evidence;
do not invent missing detail or pad older one-line records to meet a sentence count.

Follow with before/after results, demonstration evidence and remaining limitations.
Put detailed validation, usage, stage history and commit information after the outcome
summary, or provide them on request. UI demonstrations use screenshots/recordings;
agent workflows use reproducible commands. Report missing or unreadable records.

ACCEPT means a milestone was reviewed and retained; only ACHIEVED records a demonstrated
whole outcome. Verify the branch if claiming an accepted commit is still present or
merged. Legacy KEEP/DISCARD records are readable but do not assess overall outcome
completion. A stage pass or usage pause is not an idea, and a repair is not another
completed improvement. Stage duration includes recovery and waits within the stage;
elapsed wall time includes pauses. Only quantify waiting time when timestamps support it.
Usage is the last recorded sample. Recorded running status alone does not prove a live
process. An interrupted run or unavailable outcome record must not be presented as success.

Do not run agents, start/resume goals or query account credentials to produce a report.
