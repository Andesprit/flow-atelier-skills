# A scheduled run did not happen

One ordered path from "nothing ran" to the next justified check. Go step by step
and stop at the first branch that matches what you see. Schema, modes and overlap
rules live in [scheduling.md](scheduling.md); failed-run reading lives in
[troubleshooting.md](troubleshooting.md#a-run-failed-start-here).

Nothing here starts a scheduler, a server or a run. Do not use
`atelier schedule run-now` as a check: it runs the real conduit (it may spend
agent quota and change files), and it writes no schedule history and no once
marker, so it tells you nothing about the daemon.

## 1. Pick the store the scheduler reads

| Who fires the schedules | Store it reads |
|---|---|
| `atelier schedule daemon` (CLI) | `<its working dir>/.atelier/schedules/`, unless `ATELIER_ATELIER_DIR` is set in its environment or in a `.env` in its working dir |
| `atelier serve` | `~/.atelier/schedules/`, unless `ATELIER_GLOBAL_ATELIER_DIR` is set the same way |

A schedule added with `atelier schedule add` in a project goes to the project
store, so a server never sees it, and the other way round.

Run every command below from the scheduler's working directory, so a `.env`
there and any relative `run_path` resolve the same way they do for the
scheduler. To read the server's store, set the override for that one command
only. Do not export it, or later commands read the wrong store:

```bash
cd "/abs/path/the/daemon/runs/in"
atelier list schedules --json                                  # CLI daemon store
ATELIER_ATELIER_DIR="$HOME/.atelier" atelier list schedules --json   # serve store (default location)
```

`list` and `history` create `.atelier/` and `.atelier/schedules/` when they are
missing. That is a side effect, not proof the store was there.

## 2. Read the inventory and its warnings

Keep stderr visible, even with `--json`: invalid files are reported only there.

| You see | It supports | Still unknown | Next |
|---|---|---|---|
| `{"schedules": []}` and no warning | this store has no valid schedule | whether you read the right store | go back to step 1: working dir, `.env`, local or serve store |
| stderr `skipping unreadable schedule <file>` or `skipping invalid schedule <file>: ...` | the scheduler skips that file too (same loader) | nothing else about the daemon | fix the named file (the error says which field). Reinstalling with `schedule add` is a separate action |
| `schedule history <name>` says `schedule not found` | no **valid** schedule has that id or name | whether an invalid file has it | look for the warning above; `not found` is not proof no file exists |
| the row is there | the file is valid | whether any scheduler is running on this store | step 3 |

## 3. Establish the scheduler process separately

`list` reads files only. It never contacts a daemon, so a row with a next fire
time does not mean anything will fire.

Find one known process and check its context; a matching name alone proves
nothing. On macOS:

```bash
pgrep -fl 'atelier.*(schedule daemon|scheduler start|serve)'
lsof -a -p <PID> -d cwd -Fn          # that process's working directory
ps -o pid,lstart,etime -p <PID>      # when it started
```

On Linux, `readlink /proc/<PID>/cwd` gives the working directory. The working
directory is only part of the context: environment variables and the service
definition (launchd, systemd, a terminal) decide the store too. The daemon's own
log is the best evidence. At start it prints
`scheduler running (... schedules=<dir>)`; per schedule it logs
`registered schedule <id> ...: next fire ...`, then `RUNNING`, `DONE` or
`FAILED schedule <id>`.

- **No process or no log available:** daemon health is unknown. Find out how
  it was meant to run (service file, the terminal or job that started it, its
  log file). Starting a daemon is a separate action: from then on it fires
  the schedules in its store.
- **Several schedulers on one store:** every `atelier serve` and every
  `schedule daemon` runs its own scheduler. Two of them reading the same store
  can each fire the same job. "At most one instance per schedule" is a limit
  inside one process, not a lock across processes. Check each process's launch
  context before you start another.

## 4. Read the timing and the once state

| You see in `list` | It supports | Still unknown | Next |
|---|---|---|---|
| `kind: interval` with a `next_fire_time` | nothing about the daemon: it is the time you ran `list` plus `every_minutes` | when the daemon really fires | daemon log `registered` / `RUNNING` lines |
| `kind: once`, `next_fire_time: null`, a `last_run` | a scheduler **attempted** it once. A once job is marked fired even when it fails, and it is never retried | whether it succeeded | `last_run.status`, then step 5 |
| `kind: once`, `next_fire_time` in the past, `last_run: null` | no fire was recorded for that time | why: no scheduler on this store, a wrong timezone, a run still going or one that crashed | compare the time and `timezone` with the daemon log for that moment. To run it later, add a new schedule with a future `run_at`; that is a separate action |
| `kind: recurring` with a future time and no `last_run` | the file is valid | whether a scheduler will be up at that time | step 3 |

If `.atelier/scheduler_state.json` is missing or cannot be parsed, it is read as
empty without a warning. Then history is empty, and once jobs that already fired
show a next fire again, so a scheduler on this store may fire them again. Keep
the file as evidence and do not start another scheduler until you know which
store it belongs to. Do not delete or reset markers as a routine fix.

## 5. Read the history and diagnose the run

```bash
atelier schedule history <id-or-name> --json     # newest first
```

| You see | It supports | Still unknown | Next |
|---|---|---|---|
| `"status": "failed"` with a `flow_id` | the run started and failed | the cause | `atelier diagnose <flow_id>`, run from the row's `working_dir` (the schedule's `run_path`), because flows are saved under it. For nested runs follow the child diagnose it prints |
| `"status": "failed"`, `"flow_id": null` | it failed before any flow started | the cause; there is no flow to diagnose | the daemon log `FAILED schedule <id>` traceback; check the conduit resolves from that working dir with `atelier list conduits` |
| `"status": "succeeded"` | the run finished cleanly | whether its output is what you wanted | read the flow in `<working_dir>/.atelier/flows/` |
| `"runs": []` | no finished fire is recorded | whether one is running now or crashed (a record is written only when a fire ends), ran through `run-now` (not recorded), or the state file was lost (step 4) | step 3 for the process and log at the expected fire time |

History keeps the last 50 records per schedule.
