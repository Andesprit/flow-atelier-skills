# Separate checkouts for tasks (optional)

By default every task of a run works in one shared directory: the directory you
ran `atelier run` from. Two tasks that write the same file overwrite each other,
and an agent task edits your project files directly.

`atelier run <conduit> --worktree <task>` gives one top-level task its own Git
checkout instead. Repeat it for each task that should be separate. Nothing is
merged back: each checkout keeps its task's edits until you read, copy or remove
them yourself.

Check that your Atelier has it: `atelier run --help` lists `--worktree`.

## Before you run

- **Only the tasks you name are separate.** Every task you do not name still
  runs in the shared directory and can edit your real files. If several tasks
  write files, name each one.
- **Later tasks do not get the files.** A task that runs after a separate task
  works in its own directory and sees only that task's printed output, not its
  files. To read them, use the path explicitly: `{{<task>.workspace}}` in a task
  body is that task's checkout path (the shared directory for a task you did not
  name). For agent tasks that quote a separate task's output, Atelier also adds
  the checkout path to the prompt.
- **Your project must be a Git repository with a commit and no uncommitted
  changes to tracked files.** Every checkout is cut from the current commit
  (`HEAD`), so uncommitted tracked edits are refused rather than silently left
  out. Untracked and ignored files are not copied either: `.env`, `node_modules`,
  a virtualenv or build output are missing in a checkout until a task creates
  them.
- **It is not a sandbox.** A checkout is an ordinary directory with a detached
  Git checkout that shares your repository's history. A task there can still
  read and write anything else your user can, use the network and spend the same
  agent quota. Each separate agent task is still a full agent run.
- **Each checkout is a full copy of the tracked files** at
  `<project>/.atelier/workspaces/<flow_id>/<task>` (ignored by Git), so it costs
  disk space and any setup your project needs.
- Only top-level `tool:bash` and `harness:` tasks can be named. Tasks inside a
  nested `tool:conduit` are part of a separate flow and are not affected.

## Try it

In a clean Git project (`git status --short` prints nothing for tracked files),
save this two-writer recipe. Both tasks write the same file name; the third task
only reads.

Save `.atelier/conduits/two_drafts/conduit.yaml`:

```yaml
name: two_drafts
description: two shell tasks write the same file, each in its own checkout
tasks:
  - draft_a:
      description: write draft A
      tool: tool:bash
      task: printf 'draft A\n' > atelier-demo.txt
  - draft_b:
      description: write draft B
      tool: tool:bash
      task: printf 'draft B\n' > atelier-demo.txt
  - compare:
      description: read both drafts without changing anything
      tool: tool:bash
      depends_on: [draft_a, draft_b]
      task: cat "{{draft_a.workspace}}/atelier-demo.txt" "{{draft_b.workspace}}/atelier-demo.txt"
```

Run it with both writers separate:

```bash
atelier run two_drafts --worktree draft_a --worktree draft_b
```

The run prints `flow_id: <id>` at the end, and `compare` prints `draft A` then
`draft B`. Your project still has no `atelier-demo.txt`.

## Find and read each result

```bash
atelier status <flow_id>           # checkout column: one path per separate task
atelier status <flow_id> --json    # the same paths under workspaces.paths
```

A blank checkout cell means that task used the shared directory. Copy a path from
the status output and read it with read-only commands. Keep the quotes:

```bash
p='<checkout path from status>'
git -C "$p" status --short         # every changed or new file, e.g. ?? atelier-demo.txt
git -C "$p" diff                   # changes to tracked files only; new files are not shown
cat "$p/atelier-demo.txt"
```

To keep a result, copy or commit it yourself. Atelier never merges, stashes,
resets or removes anything. The checkouts stay after the run, and `atelier rm`
does not delete them. When you no longer need one, remove it with
`git worktree remove '<checkout path>'` from your project.

## If something stops

| You see | What it means | Next step |
|---|---|---|
| `has no task 'X' — did you mean ...` | The name is not a top-level task | Use a name from the list it prints |
| `expected a task name only` | You passed a path or `task=...` | Pass only the task name; Atelier picks the directory |
| `has uncommitted changes to tracked files (...)` | Your project has tracked edits | Commit or stash them yourself, then run again |
| `has no commit to base a worktree on` | The repository has no commit yet | Make a first commit |
| `is not inside a Git repository` | No repository at or above the directory | Run from a Git project, or drop `--worktree` |
| `runs '...', which has no working directory of its own` | The task is not a bash or agent task | Leave that task shared |

No task runs and no checkout is made when you see one of these.

**Resume and again** behave differently with checkouts:

- `atelier run --resume <flow_id>` continues in the **same** checkouts, so a
  failed task's partial edits are still there. Adding `--worktree` to a resume is
  refused.
- `atelier run --again <flow_id>` starts a new flow with the same tasks
  separate, in **new** checkouts cut from the repository's current `HEAD`. The old
  checkouts keep their edits.
- If a checkout a resume needs was deleted, the resume is refused, because its
  partial edits are gone. `--again` can start over in new checkouts.
- If the saved checkout record was damaged (`saved worktree record` in the
  message), both resume and again are refused. Start a new run with
  `atelier run <conduit> --worktree ...`.
