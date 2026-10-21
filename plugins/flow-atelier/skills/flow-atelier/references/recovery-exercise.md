# Recovery exercise (optional)

Practise recovering a failed run on a harmless example before you need it on real
work. A three-step shell workflow fails on purpose, you read the diagnosis, fix the
one missing file and resume the same run. A small ledger file shows which steps
did their work.

You need only the `atelier` CLI ([first run](first-run.md), step 1) and `bash`,
which macOS and most Linux systems include.
No agent, login, server or package. It takes a few minutes. Every file it writes,
including Atelier's own saved runs, stays inside one new directory.

## 1. Make the lab and open a lab shell

Run this in a terminal, from the folder where you want the lab directory:

```bash
mkdir atelier-recovery-lab && cd atelier-recovery-lab && env ATELIER_ATELIER_DIR="$PWD/.atelier" ATELIER_GLOBAL_ATELIER_DIR="$PWD/lab-global" ATELIER_NO_UPDATE_CHECK=1 HISTFILE= PS1='recovery-lab$ ' bash --noprofile --norc
```

It opens a new `bash` shell inside the new directory, with the prompt
`recovery-lab$ `. Run the rest of the exercise at that prompt, even if your usual
shell is zsh. `--noprofile --norc` stops your startup files from
changing the lab settings, and the empty `HISTFILE` keeps the lab's commands out
of your shell history file. On macOS, `bash` may first print a note that the
default shell is now zsh; you can ignore it. The lab shell has three settings that only it and the
commands you run in it see:

- `ATELIER_ATELIER_DIR` keeps the project store (conduits and saved runs) in the
  lab's `.atelier`, even if your normal shell or a `.env` points elsewhere.
- `ATELIER_GLOBAL_ATELIER_DIR` points the global store at `lab-global` inside the
  lab, so your real `~/.atelier` conduits, schedules and cache are not used.
- `ATELIER_NO_UPDATE_CHECK=1` turns off the CLI's update check, so the lab makes
  no network request.

If `atelier-recovery-lab` already exists, `mkdir` prints `File exists` and
nothing else runs: no lab shell opens. Use another name, or remove the old lab
yourself after checking what is in it. When you finish the exercise, type `exit`
to go back to your normal shell with its settings unchanged.

## 2. Save the lab workflow

Paste this into the lab shell. It writes the conduit only if you are in the lab
shell from step 1. Otherwise it prints `Stopped: ...` and writes nothing.

```bash
if [ "$ATELIER_ATELIER_DIR" = "$PWD/.atelier" ] && [ "$ATELIER_GLOBAL_ATELIER_DIR" = "$PWD/lab-global" ]; then
mkdir -p .atelier/conduits/recovery_lab
cat > .atelier/conduits/recovery_lab/conduit.yaml <<'EOF'
name: recovery_lab
description: Fail on a missing local file, then resume after you create it
tasks:
  - prepare:
      description: Record that the preparation step ran
      tool: tool:bash
      task: |
        printf 'prepare ran\n' >> ledger.txt
        printf 'prepared\n'
  - needs_input:
      description: Fail until lab-input.txt exists in this directory
      tool: tool:bash
      depends_on: [prepare]
      task: |
        if [ ! -f lab-input.txt ]; then
          printf 'missing lab-input.txt in %s\n' "$PWD" >&2
          exit 3
        fi
        printf 'needs_input ran\n' >> ledger.txt
        cat lab-input.txt
  - finish:
      description: Print the success marker
      tool: tool:bash
      depends_on: [needs_input]
      task: |
        printf 'finish ran\n' >> ledger.txt
        printf 'RECOVERY_LAB_DONE\n'
EOF
atelier check recovery_lab
else
  echo "Stopped: open the lab shell from step 1 first, then paste this again."
fi
```

Expected: `recovery_lab [project] — OK`. Each step adds one line to `ledger.txt`
only after it has done its work.

## 3. Run it and watch it fail

This run is meant to fail: `lab-input.txt` does not exist yet.

```bash
atelier run recovery_lab
```

Expected, and the command exits 1:

- `prepare` passes and prints `prepared`.
- `needs_input` fails with `exit=3` and `missing lab-input.txt in <lab path>`.
- `finish` shows `cancelled (upstream failed)`.
- The last lines are `flow failed: task 'needs_input' failed: ...`, then
  `flow_id: <date>_<id>_recovery_lab` and a resume hint.

Copy the ID from your own `flow_id:` line into a variable. Replace the example
value with yours and keep the quotes:

```bash
id='20261021_24c7409a_recovery_lab'
cat ledger.txt
```

The ledger has one line, `prepare ran`.

## 4. Read the diagnosis

```bash
atelier diagnose "$id"
```

It names `needs_input`, its `exit=3` and the stderr line about
`lab-input.txt`. Under `kept — completed and saved` it lists `prepare`, and
says a resume does not run a completed task again. `diagnose` exits 0 even
though the run failed: it reports, it does not run anything.

## 5. Fix only the cause

```bash
printf 'repaired\n' > lab-input.txt
```

Do not edit the conduit. The failure was a missing local file, not a wrong
step.

## 6. Resume the same run

```bash
atelier run --resume "$id"
cat ledger.txt
```

Expected, and the command exits 0:

- Only `needs_input` and `finish` run, each marked `resuming`. `needs_input`
  prints `repaired` and `finish` prints `RECOVERY_LAB_DONE`.
- The summary is `✓2` and the `flow_id:` line shows the same ID as before.
- The ledger now has three lines: `prepare ran`, `needs_input ran`,
  `finish ran`. `prepare` ran once.

The ledger records work that succeeded, not every attempt. The failed
`needs_input` attempt in step 3 exited before writing its line.

`atelier run --resume "$id"` on this now completed run is refused with
`can only resume failed or crashed flows, got completed`.

## 7. Optional: compare with a fresh run

`--again` is a new run with the same inputs, not a resume:

```bash
atelier run --again "$id"
cat ledger.txt
```

It prints a new `flow_id:` and runs all three steps (`✓3`). The ledger gains
three more lines, so `prepare ran` now appears twice. Use `--again` only when
repeating every step is what you want.

When you are done, type `exit` to leave the lab shell. The lab directory stays;
delete it yourself when you no longer need it.

## What this shows, and what it does not

It shows, for this run, that a step saved as completed was kept on resume, and
that resume continues the same flow ID while `--again` starts a new one.

It does not make resume exactly-once or reversible:

- Resume is at-least-once. If a run crashes after a step did its work but before
  Atelier saved that step as completed, resume runs it again. Nothing is rolled
  back.
- A cancelled task in a real run may already have started and changed things.
  Here `finish` had not started, because the steps run one after another.
- Resume reads the conduit as it is now. Editing a completed step does not make
  it run again; only unfinished steps run, under the new definition.
- Agent steps spend quota and can change files again when they rerun. This lab
  proves nothing about an agent being installed, logged in or safe to repeat.

For real failures, start at [troubleshooting](troubleshooting.md#the-flow-failed).
