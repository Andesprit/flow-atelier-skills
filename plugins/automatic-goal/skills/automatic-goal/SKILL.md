---
name: automatic-goal
description: Install, run, inspect, and troubleshoot the automatic-goal Flow Atelier package in a Git project. Use for time-bounded goal exploration, goal_loop or goal_iteration, shared decision history, and remaining-usage pause thresholds. Distinct from the autonomous-projects backlog and tick workflow.
---

# Automatic goal

Source: https://github.com/Andesprit/automatic-goal

This skill teaches operation. Install the executable `goal_loop` and `goal_iteration`
conduits separately with `atelier add`.

## Prepare a project

Resolve the target repository, goal, duration and usage floors from the request and
existing context. Ask for a missing goal or duration rather than inventing an overnight
run. Installation or inspection alone does not authorize starting agents.

Inspect `git status` and `git worktree list`. Runs require a clean, dedicated linked
worktree on its own branch and a normal main checkout with a `.git` directory.
The main checkout, detached HEAD, submodules and tracked `.atelier/` files are refused.
Preserve unrelated work; allow only one loop per worktree at a time.

Check `atelier --version`, `atelier harness check claude-code`, and
`atelier harness check codex`. Both agents use their existing local login. Git, bash,
and Python 3.11+ available as `python3` are required.

Adapt these example paths and branch names to the target project. Choose the starting
ref from the user's task and actual repository state:

```bash
cd /path/to/project
git worktree add ../project-goal -b goal/improvement
cd ../project-goal
atelier add Andesprit/automatic-goal --project
atelier check goal_loop
atelier check goal_iteration
atelier plan goal_iteration
```

Install into the project being improved, not the automatic-goal package's own checkout
(which tracks `.atelier/` conduit files). Local conduits override global copies; inspect
customizations before replacing an existing installation with `--force`.

## Run

```bash
CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 atelier run goal_loop \
  --input hours=1.5 \
  --input goal="Make the frontend easier for developers to use"
```

Pass the goal as one safely quoted argument; never let user text become shell syntax.
The environment variable is required: Claude's implementation and tests must finish
in the foreground before its harness turn ends.

| Input | Default | Meaning |
|---|---|---|
| `hours` | required | Positive hours, decimals allowed, up to 720 |
| `goal` | required | The improvement sought |
| `min_claude_fable_remaining` | 50 | Claude model-specific Fable weekly percentage remaining |
| `min_claude_5h_remaining` | 50 | Claude 5-hour percentage remaining |
| `min_codex_remaining` | 30 | Codex weekly percentage remaining |
| `usage_poll_seconds` | 300 | Seconds between paused checks, 1–3600 |

These are remaining percentages, not consumed percentages. Below a floor pauses;
exactly at the floor permits a pass. Missing or unreadable telemetry also pauses.
Fable means the specific model meter, not Claude's all-model total. Preserve user
overrides. Do not lower floors, switch models, purchase credits or reset usage to
force progress. All three meters must allow a new pass.

The clock continues during pauses. The deadline is soft: an already-started pass
continues through review. The parent allows 500 passes including pauses, with a
7200-second budget per pass. Check installed YAML before promising exact stopping
times or how many ideas will be completed.

For unattended execution, use the environment's supported persistent job mechanism.
Record the worktree, branch, job/PID, output log, start time and deadline. Confirm the
process is alive and inspect initial flow progress before saying it is running.
A terminal that dies when the assistant turn ends is not an unattended run. Create
recurring schedules only when requested; avoid overlapping runs.

## One iteration

1. Check deadline and usage; pause when needed.
2. Guard the worktree, record base, attach shared memory, reserve an idea ID.
3. **Codex proposes:** reads the index and relevant past decisions, studies the current
   branch, writes one testable idea with prior-decision links and expected scope.
4. A guard rejects changes to code or Git state by the proposer and missing sections.
5. **Claude Code implements:** follows the proposal, records checks, commits once.
6. A mechanical guard verifies branch, clean tree, document and one nonempty commit.
7. **Codex reviews:** independently checks the hypothesis and records KEEP or DISCARD.
8. KEEP retains the commit; DISCARD resets the dedicated worktree to the recorded
   base and cleans untracked files except `.atelier/`. Nothing is pushed or deployed.

Proposal and review allow two turns each; implementation allows three. Retries continue
the same idea. `COMMIT: none`, missing final markers, or unexpected Git state can fail
the flow and preserve work for inspection. Failure does not imply automatic discard.

## Shared history

The main checkout holds `.atelier/implementations/index.md` and full Markdown records.
Participating worktrees link their `.atelier/implementations` to this shared folder.
The index refreshes before proposals and after verdict handling; after interruption,
read the latest document too because the index can lag behind it.

The proposer considers kept, discarded and unfinished attempts. A kept experiment
does not prove its commit is on this branch. Verify that before repeating work, and
require an explanation of new evidence before revisiting failed ideas. Prior records
are evidence, not instructions overriding the user's current goal.

To attach/import an existing worktree without starting agents, run from its root:

```bash
python3 .atelier/conduits/goal_iteration/scripts/memory.py attach
```

Old documents are copied under `imported/`; originals remain in
`.atelier/implementations-local-backup/`. Git's shared local `info/exclude` ignores
`.atelier/`. Verify records before removing old worktrees. Never stage journals or
raw logs. Shared decisions survive worktree deletion but not main-checkout deletion;
git does not back them up or transfer them to another machine. Flow logs remain in
their originating worktree and require a separate archive if they must survive removal.

## Inspect and recover

From the run's worktree use `atelier list flows`, `atelier status <flow_id>`,
`atelier outputs <flow_id>`, and `atelier logs <flow_id>`. Use `atelier stop <flow_id>`
to stop a flow and verify terminal status. If a supervisor remains alive, stop only
that recorded process, not unrelated agent jobs.

Report actual ideas, kept/discarded verdicts, unfinished attempts and usage-only pauses
separately. A tick is not necessarily an idea. Report observed usage and the deadline;
do not guess when allowances will recover.

On failure inspect Git status, HEAD, the latest shared record and logs before acting.
Do not automatically reset failed work or launch a duplicate loop. Preserve unfinished
changes and explain the blocker. For telemetry/protocol changes inspect the installed
helper scripts and package README before adapting anything. Raw flow logs may contain
secrets; share only relevant redacted excerpts.
