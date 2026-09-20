---
name: goal-monitor
description: Open the read-only local automatic-goal session dashboard showing completed changes, open work, outcome status, evidence, priorities and saved technical history.
---

# Goal monitor

Locate the project and its installed `.atelier/conduits/goal_loop/scripts/observe.py`.
Use a Python interpreter with PyYAML, such as Atelier's environment. If absent, inspect
the installed package and local edits before installing/updating `Andesprit/automatic-goal`.
Do not replace conduits underneath an active run; upgrade goal_loop and goal_iteration
together after existing runs are finished or inspected. Legacy KEEP/DISCARD flows must
not resume using the new stage-based conduits.

```sh
python /path/to/observe.py serve --root /path/to/project --port 8765
```

Keep the server in a managed terminal session and open the printed localhost URL.
If the port is occupied, choose another; do not kill unrelated processes. Verify the
page and `/api/snapshot` respond before claiming availability. Give the URL and explain
that it lasts while the server process remains running.

The dashboard refreshes saved records across Git worktrees every three seconds. Select
the requested session by date and goal. Its first view shows the outcome status, elapsed
time, every completed improvement, still-open work and current priority when active.
Each completed change has a paragraph explaining what changed, why it matters and how
it works. Evidence and validation, explored-but-not-kept approaches, and technical
history are expandable. Discarded ideas retain their attempted approach and benefit
alongside the evidence and reason for rejection. Older records may have less detail;
do not infer missing explanations.

ACCEPT milestones are not proof of ACHIEVED outcomes. Repairs do not count as separate
completed improvements; DEFERRED is distinct from ABANDON. Legacy kept/discarded records
remain readable without implying whole-goal completion. Interrupted or missing reports
are identified explicitly. Usage is the last saved stage check, not a provider poll;
recorded runner status is not a health probe. Failed refreshes retain the last view and
show a retry message. Stage time includes recovery and waits, and wall time includes pauses.

The server is read-only, binds to 127.0.0.1, and exposes the dashboard and snapshot.
Do not publish it: evidence may contain private project information. Monitoring does
not authorize starting/resuming/stopping goals or changing usage floors. Use the shared
reader's `report` mode for a written retrospective; `--details` includes full records.
