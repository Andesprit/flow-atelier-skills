# Automatic-goal refusals and pauses

For a failed flow, first run `atelier diagnose <flow_id>` from the worktree holding
its flows. Follow a child-diagnose command if one is printed. Setup stops at the
first refusal: fix that cause, then retry with the same intended goal and inputs.
Inspect the saved checkpoint before resuming or starting another loop.

The tables distinguish the `goal_loop` setup shell from `run.py` initialization.
**Reproduced** means exercised in an isolated scratch repository using the installed
setup shell or direct `run.py init`, without entering `route` or starting an agent.
**Source** means inspected only. Source paths are relative to `.atelier/conduits/`;
line numbers refer to the package inspected for this update and may move on upgrade.
Values such as `unset`, `nope` and `0` are the reproduced examples; your value and the
dirty-file listing can differ. The `...` in the environment error is literal CLI text.

## Setup shell

| Message | Cause | Fix | Verification |
|---|---|---|---|
| `goal_loop: CLAUDE_CODE_DISABLE_BACKGROUND_TASKS must be exactly 1 (got 'unset'); run: CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 atelier run goal_loop ... - otherwise claude-code backgrounds its tests and ends its turn before they finish (https://code.claude.com/docs/en/env-vars)` | The runner did not inherit the required value `1`. | Prefix the run or resume command with `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`. | Reproduced: `env-var`; `goal_loop/conduit.yaml:28–29`. |
| `goal_loop: hours must be a number up to 720 with at most 4 decimals (e.g. 4 or 1.5), got 'nope'` | The duration format is invalid. | Pass a trusted positive numeric value, for example `--input hours=1.5`, with at most four decimal places. | Reproduced: `hours-format`; `goal_loop/conduit.yaml:30–32`. |
| `goal_loop: hours must be more than 0 and at most 720, got '0'` | The duration rounds below one second or exceeds 720 hours. | Choose a duration of at least one second and at most 720 hours. | Reproduced: `hours-range`; `goal_loop/conduit.yaml:33–36`. |
| `goal_loop: not inside a git worktree` | The current directory is outside Git. | Resolve the target repository, create a dedicated linked worktree there, and run from its root. | Reproduced: `outside-git`; `goal_loop/conduit.yaml:37`. |
| `goal_loop: run from the worktree root` | The current directory is a subdirectory of the worktree. | Change to the root reported by `git rev-parse --show-toplevel`. | Reproduced: `non-root`; `goal_loop/conduit.yaml:39`. |
| `goal_loop: this is a main checkout or a submodule; use a dedicated linked worktree (git worktree add ../<dir> -b <branch>)` | The run is in the main checkout or a submodule. | From a normal main checkout, create a new linked worktree with `git worktree add ../project-goal -b goal/improvement`, adapting unused names, then enter it. | Reproduced: `main-checkout`; `goal_loop/conduit.yaml:40–42`. |
| `goal_loop: detached HEAD; check out a dedicated branch` | The linked worktree has no branch. | Preserve any work, then attach a dedicated branch, for example `git switch -c goal/improvement` with an unused name. | Reproduced: `detached-head`; `goal_loop/conduit.yaml:43`. |
| `goal_loop: submodules are not supported` | The Git index contains a submodule entry. | Use a project without tracked submodules; this package cannot safely discard work in this layout. | Reproduced: `tracked-submodule`; `goal_loop/conduit.yaml:44`. |
| `goal_loop: tracked files under .atelier/ would be lost on discard; untrack them first` | Git tracks package files or other data under `.atelier/`. | Preserve that data and arrange for `.atelier/` to be untracked and ignored in both the target worktree and main checkout before retrying. Install into the project being improved, not the package's own checkout. | Reproduced: `tracked-atelier`; `goal_loop/conduit.yaml:45`. |
| `goal_loop: worktree is not clean (only untracked .atelier/ is allowed):` followed by the Git status listing | Tracked edits, staged changes or other untracked files exist. | Inspect `git status`; preserve and commit or move unrelated work before retrying. Do not reset or delete it to make the guard pass. | Reproduced: `dirty-tree`; `goal_loop/conduit.yaml:46–47`. |

## Initialization and checkpoint guards

`run.py` errors carry the prefix `automatic-goal:` and suffix `; work preserved`.
It repeats the environment, worktree-root, dedicated-worktree, submodule and tracked
`.atelier` guards above with shorter wording (`goal_iteration/scripts/run.py:72–90`). Its dirty-tree message
is `automatic-goal: worktree is not clean; work is preserved; work preserved`.
Apply the same fixes. These shorter variants are **Source**, except the rows below.

| Message | Cause | Fix | Verification |
|---|---|---|---|
| `automatic-goal: unsupported branch name; work preserved` | The branch contains characters outside letters, digits, `.`, `_`, `/` and `-`. Git itself permits more characters. | Use a dedicated branch with supported characters, such as `goal/improvement`; preserve the existing branch and work. | Reproduced: `bad-branch` using `goal+unsupported`; `goal_iteration/scripts/run.py:82–84`. |
| `automatic-goal: deadline must be in the future; work preserved` | A direct initialization supplied an expired epoch deadline. Normal `goal_loop` setup computes a future one. | For a new run, calculate a future deadline; for an existing run, inspect its checkpoint and retain its original deadline when resuming. | Reproduced: `past-deadline` via direct init; `goal_iteration/scripts/run.py:164–168`. |
| `automatic-goal: reserve must be 5–50, max_revisions 0–5, usage buffer 0–25; work preserved` | A budget input is outside its allowed range. | Set `finish_reserve_percent` to 5–50, `max_revisions` to 0–5 and `usage_reserve_percent` to 0–25, using trusted integer inputs. | Reproduced: `invalid-reserve`; `goal_iteration/scripts/run.py:169–170`. |
| `automatic-goal: unfinished goal exists; resume that flow or inspect its checkpoint first; work preserved` | This worktree already has a nonterminal checkpoint. | Read `.atelier/goal/handoff.md` and inspect the recorded flow. Resume it if appropriate; do not remove the checkpoint or launch a duplicate loop. | Reproduced: `duplicate-goal`; `goal_iteration/scripts/run.py:171–175`. |
| `automatic-goal: no goal checkpoint; initialize a run first; work preserved` | A standalone iteration or recovery command has no checkpoint link. | Check that you are in the original worktree. For a genuinely new run, use `goal_loop`; inspect existing history before initializing again. | Source: `goal_iteration/scripts/run.py:94–97`. |
| `automatic-goal: goal checkpoint belongs to another worktree; work preserved` | The checkpoint points to another worktree's run. | Return to the worktree recorded in the checkpoint and inspect it there. Do not edit its recorded path to bypass the guard. | Source: `goal_iteration/scripts/run.py:98–100`. |
| `automatic-goal: floors must be 1–100 and poll 1–3600; work preserved` | Usage inputs are out of range. | Use whole-number remaining floors from 1 to 100 and a polling interval from 1 to 3600 seconds; preserve the user's chosen limits. | Source: `goal_iteration/scripts/run.py:884–886`. |
| `automatic-goal: invalid run ID; work preserved` | A standalone iteration received an invalid identifier. | Use the saved run ID; `auto` is for initial standalone setup. Prefer resuming the recorded parent flow. | Source: `goal_iteration/scripts/run.py:887–888`. |
| `automatic-goal: invalid Claude weekly meter name; work preserved` | The meter name is empty, longer than 40 characters, or uses unsupported punctuation. | Use its display name with letters, digits, spaces, `.`, `_` or `-`, or `all`; do not silently substitute another allowance. | Source: `goal_iteration/scripts/run.py:889–890`. |
| `automatic-goal: run ID differs from the current checkpoint; work preserved` | The supplied ID and saved run disagree. | Locate the matching worktree and resume its recorded flow. | Source: `goal_iteration/scripts/run.py:768–773`. |
| `automatic-goal: deadline differs from the saved run; resume with the original deadline; work preserved` | A standalone iteration supplied a different deadline. | Resume the recorded flow with the original deadline; do not extend it by editing state. | Source: `goal_iteration/scripts/run.py:776–777`. |

Initialization also attaches shared history (`goal_iteration/scripts/run.py:176`).
These **Source** messages come from `goal_iteration/scripts/memory.py` and receive
the same `automatic-goal:` prefix and `; work preserved` suffix:

| Message body | Cause | Fix | Verification |
|---|---|---|---|
| `Shared memory requires a normal main checkout with a .git directory` | The linked worktree has an unsupported main-checkout layout. | Use a normal main checkout with a `.git` directory and a dedicated linked worktree. | Source: `goal_iteration/scripts/memory.py:65–69`. |
| `Main checkout tracks .atelier files; refusing shared memory` | The main checkout tracks `.atelier/`, even if this worktree does not. | Preserve that data and make `.atelier/` untracked and ignored in the main checkout too. | Source: `goal_iteration/scripts/memory.py:70–71`. |
| `Unexpected memory symlink: <path>; inspect it manually` | The local history link points somewhere unexpected. | Inspect the link and both histories before repairing it; preserve their contents. | Source: `goal_iteration/scripts/memory.py:90–91`; `<path>` varies. |
| `Unexpected symlink in legacy history: <path>` | Legacy history contains a symlink that cannot be safely imported. | Inspect its target and preserve the legacy history before resolving the link. | Source: `goal_iteration/scripts/memory.py:96–98`; `<path>` varies. |
| `Conflicting history: <path>` | An imported history file differs from the existing destination. | Compare and preserve both versions; resolve the conflict before retrying. | Source: `goal_iteration/scripts/memory.py:101–104`; `<path>` varies. |
| `Backup already exists: <path>; inspect before migration` | A previous migration backup already occupies the destination. | Inspect and preserve the backup and current history before arranging migration. | Source: `goal_iteration/scripts/memory.py:106–108`; `<path>` varies. |

## Usage pauses

Unreadable usage or remaining allowance below a floor normally becomes
`USAGE_PAUSE`, not a fatal setup refusal. A new feature also waits inside the usage
reserve. Read `.atelier/goal/handoff.md` for the saved run outcome and open work;
check `.atelier/goal/state.json` for `usage_text`, `usage` and `events` entries with
`kind: USAGE_PAUSE` to see why it paused. These are saved samples, not live meters.
The runner rechecks automatically; keep the floors and model choices intact.
Source: `goal_iteration/scripts/run.py:779–816` and `goal_iteration/scripts/usage.py:333–386`.
