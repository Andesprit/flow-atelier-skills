---
name: automatic-goal
description: Install, run, inspect, and troubleshoot the automatic-goal Flow Atelier package in a Git project. Use for time-bounded outcomes, goal_loop or goal_iteration, milestone review and repair, shared decision history, and usage reserves. Distinct from the autonomous-projects backlog workflow.
---

# Automatic goal

Source: https://github.com/Andesprit/automatic-goal

This skill teaches operation. Install the executable `goal_loop` and `goal_iteration`
conduits separately with `atelier add`. Codex owns observation, priorities, review and
final demonstration; Claude Code implements and repairs.

## Prepare a project

Resolve the target repository, goal, duration and usage floors from the request and
existing context. Ask for a missing goal or duration rather than inventing an overnight
run. Installation or inspection alone does not authorize starting agents.

Inspect `git status` and `git worktree list`. Runs require a clean, dedicated linked
worktree on its own branch and a normal main checkout with a `.git` directory.
The main checkout, detached HEAD, submodules and tracked `.atelier/` files are refused.
Preserve unrelated work; allow only one loop per worktree at a time.

Check `atelier --version`, `atelier harness check claude-code`, and
`atelier harness check codex`. Both agents use their existing login. Git, Bash and
Python 3.11+ available as `python3` are required; reports also need PyYAML.

Adapt these paths and branch names to the task and actual repository state:

```bash
cd /path/to/project
git worktree add ../project-goal -b goal/improvement
cd ../project-goal
atelier add Andesprit/automatic-goal --project
atelier check goal_loop
atelier check goal_iteration
atelier plan goal_loop
```

Install into the project being improved, not the package's own checkout, which tracks
`.atelier/`. Local conduits override global copies. Inspect customizations before
replacing an installation with `--force`. Upgrade both conduits together. Finish or
inspect existing runs first: do not resume a legacy KEEP/DISCARD flow with the new
stage-based conduits. Legacy decision history remains readable.

## Run and budget

```bash
CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 atelier run goal_loop \
  --input hours=4 \
  --input goal="A new developer can run a useful workflow and recover from failure unaided"
```

Pass the goal as one safely quoted argument. Numeric inputs must be trusted numeric
values: the conduit interpolates them into shell before validation. The environment
variable keeps Claude's implementation and checks in the foreground until the turn ends.

| Input | Default | Meaning |
|---|---|---|
| `hours` | required | Positive wall-clock hours, decimals allowed, up to 720 |
| `goal` | required | User outcome sought |
| `finish_reserve_percent` | 20 | Last 5–50% of time reserved for integration, repairs and demonstration |
| `max_revisions` | 2 | 0–5 repair rounds per milestone; also bounds integration repair milestones |
| `usage_reserve_percent` | 5 | 0–25 extra percentage points above each floor needed to start features |
| `min_claude_fable_remaining` | 50 | Claude model-specific Fable weekly remaining floor |
| `min_claude_5h_remaining` | 50 | Claude five-hour remaining floor |
| `min_codex_remaining` | 30 | Codex weekly remaining floor |
| `usage_poll_seconds` | 300 | Seconds between paused checks, 1–3600 |

Floors refer to remaining percentages. Fable is the specific model meter, not Claude's
all-model total. All three meters must be readable and at or above their floor to run
a stage. New features additionally require the usage reserve; review, repairs and
final demonstration can use that buffer but must still respect the floors. Unknown
telemetry pauses. Preserve user overrides; do not lower floors, switch models, purchase
credits or reset usage to force progress.

Planning and pauses consume the same wall-clock budget. New milestone estimates include
implementation and review and must fit before the finishing reserve. Repairs must leave
a final handoff allowance (5% of the run, capped at five minutes). These are planning
constraints, not speed guarantees. At the deadline the controller writes a partial
handoff without starting another agent. Already-started agent turns have a soft deadline:
Codex stages have an 1800-second cap, implementation 3600, with one transport retry and
a 7200-second outer cap per pass. The parent allows 500 passes including pauses.
Check installed YAML before promising exact stopping times.

For unattended execution, use a supported persistent job mechanism. Record the worktree,
branch, flow ID, job/PID, output log, start time and deadline. Verify the process and
initial flow progress before saying it is running. Create schedules only when requested.

## Outcome workflow

Each `goal_iteration` executes one stage or one usage pause, not one idea or commit:

1. **SUPERVISE:** inspect the actual user path and record its baseline, success criteria
   and behavior to preserve. Normally compare three to five opportunities (at least two
   credible alternatives) by benefit, evidence, effort and uncertainty. Choose a primary
   and fallback and explain why the primary deserves the time. Use competitor research
   to resolve a named uncertainty when useful. Retain the brief across milestones;
   changing it requires an evidence-backed replan. At checkpoints choose to build,
   simplify, switch, finish or report a blocker.
2. **IMPLEMENT:** Claude completes a coherent, independently useful milestone across as
   many files and focused commits as needed. Commits extend its recorded base without
   merging or rewriting history. Match checks to risk and scope; record evidence and
   elapsed time. A repair continues the same milestone and addresses review findings.
3. **REVIEW:** Codex independently assesses correctness and contribution to the user
   outcome. ACCEPT retains useful, reliable work. REVISE sends concrete findings and
   completion criteria to Claude for bounded repair. ABANDON records weak value, a
   disproven hypothesis or unjustified repair cost. Exhausted repair budgets become
   DEFERRED rather than a claim that the idea was bad. Before rollback, abandoned or
   deferred commits are saved under `refs/automatic-goal/<run-id>/<milestone-id>`;
   earlier accepted work remains. Unexpected or dirty Git state is preserved for inspection.
4. **FINALIZE:** revisit the original user path on the accepted branch. Demonstrate each
   success criterion with before/after evidence, integrated checks and limitations.
   Use screenshots/recordings for UI work and reproducible commands for agent workflows.
   Narrow integration repairs can use the reserve. ACHIEVED requires evidence for every
   criterion; PARTIAL/BLOCKED identify what remains. Passing tests, elapsed time and
   accepted commit counts do not establish outcome achievement. Finishing early is valid.

Nothing is pushed or deployed by the conduit. Agents write request-bound JSON following
`.atelier/conduits/goal_iteration/stage-results.md`; final chat markers do not control it.
Missing, malformed or stale results get two recovery attempts with the same request ID
and actual Git state, so completed implementation is not repeated. Exhaustion becomes
OPERATIONAL_FAILURE, not ABANDON. A genuine implementation blocker preserves the work.

## Records, reports and recovery

The main checkout holds `.atelier/implementations/index.md`, numbered milestone Markdown
records, and `runs/<run-id>/` containing `state.json`, `request.json`, `result.json`,
`usage.json`, `handoff.md` and `evidence/`. The worktree's `.atelier/implementations`
links to shared history; `.atelier/goal` points to its current run. The parent flow's
`initialize` output identifies the correct run when inspecting an older session.
The handoff is regenerated at each checkpoint, including incomplete runs.

Read relevant accepted, abandoned and unfinished history before repeating work. Verify
which commits actually exist on this branch; a historical acceptance does not prove
presence here. Require new evidence before retrying a rejected approach. Legacy records
can be imported with `python3 .atelier/conduits/goal_iteration/scripts/memory.py attach`;
originals remain in `.atelier/implementations-local-backup/`. Never stage journals or raw
logs. Shared records and checkpoint refs survive worktree deletion but remain local;
normal Git pushes do not transfer them. Flow logs stay in their originating worktree.

For reports use the installed `goal_loop/scripts/observe.py` with `report`, `json` or
`serve`. Start with outcome status, elapsed time, all completed improvements and still-open
work. Each completed change gets a paragraph explaining what changed, why it matters and
how it works. Each discarded idea retains the attempted approach and intended benefit,
plus the evidence and reason for dropping it. Keep technical history secondary;
`report --details` includes the full records. Never invent missing historical detail.

Inspect before resuming:

```bash
git status
atelier status <flow_id>
atelier outputs <flow_id>
atelier logs <flow_id>
cat .atelier/goal/handoff.md
CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 atelier run --resume <flow_id>
```

Resume preserves the original deadline and checkpoint. A terminal BLOCKED or
OPERATIONAL_FAILURE run needs inspection and an explicit decision about preserved changes
before a fresh run. Do not reset unfinished work, edit canonical state blindly or launch
a duplicate loop. Use `atelier stop <flow_id>` to stop a requested run and verify its
terminal status; stop only its recorded process if a supervisor remains alive.
Usage is the last saved sample, not current account usage. Recorded running status is
not a health probe. Logs may contain secrets; share only relevant redacted excerpts.
