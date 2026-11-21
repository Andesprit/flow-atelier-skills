# Scheduling

`atelier schedule daemon` runs conduits on a wall-clock schedule. One schedule is
one persisted YAML file under `~/.atelier/schedules/`. The daemon is a
single foreground process you can put under `systemd`, `launchd`, or any
supervisor.

## The schedule file

```yaml
conduit_name: report          # required - which conduit to run
run_path: /abs/path           # required - the working directory the run uses
inputs:                       # optional - the --input values for each fire
  date: today
  n_todo: "5"
schedule:
  mode: recurring             # recurring | once | interval
  name: weekday mornings      # optional label; usable in place of the id
  days: [1, 2, 3, 4, 5]       # ISO 8601: 1=Mon .. 7=Sun
  times: ["06:00", "12:00"]   # 24-hour "HH:mm" strings
  timezone: America/Bogota    # optional IANA name; defaults to the host zone
```

`run_path` matters: flows are always written relative to it, and conduits
resolve from `<run_path>/.atelier/conduits` before the global store.

Unknown fields are rejected, so a typo is a load error rather than a silently
ignored setting.

## The three modes

### `recurring` - days x times

```yaml
schedule:
  mode: recurring
  days: [1, 2, 3, 4, 5, 6, 7]
  times: ["06:30", "09:30", "14:00"]
  timezone: America/Bogota
```

Requires at least one `day` and one `time`. Fires at every listed time on every
listed day - the two lists are a cross product, not pairs. `days` entries must be
`1..7`; `times` must match `HH:mm` 24-hour.

### `interval` - every N minutes

```yaml
schedule:
  mode: interval
  name: every-30min
  every_minutes: 30
```

Requires `every_minutes >= 1`. Repeats forever.

### `once` - a single future run

```yaml
schedule:
  mode: once
  name: one-shot-reminder
  run_at: 2026-08-01T09:00:00
```

Requires `run_at` as an ISO 8601 datetime (a trailing `Z` is accepted). A naive
value is interpreted in the schedule's `timezone`, else the host zone.

**`run_at` must be in the future.** A past value is rejected at install time,
because it would produce a trigger that never fires - a zombie schedule
indistinguishable from one that already ran.

## Managing schedules

```bash
atelier schedule add <file.{json,yaml}>    # install into ~/.atelier/schedules/
atelier list schedules [--json]           # installed schedules + next fire times
atelier schedule migrate                  # move this project's legacy jobs
atelier schedule rm <id-or-name>          # hard delete
atelier schedule run-now <id-or-name>      # fire immediately, bypassing the daemon
atelier schedule history <id-or-name> [--json]  # recorded runs, newest first
```

`<id-or-name>` accepts the generated schedule id or the `schedule.name` you set.

## Running the daemon

```bash
atelier schedule daemon [--reload-interval 30] [--log-level INFO]
atelier list schedules [--json]
```

`schedule daemon` runs in the foreground; Ctrl+C or SIGTERM stops it.
`atelier serve` boots the same scheduler embedded alongside the HTTP server, so
run only one of them for the shared store. Additional dashboards can use
`atelier serve --no-scheduler`.

`list schedules` reads `~/.atelier/schedules/` **directly and does not contact a
running daemon**. It tells you what is installed and when it would next fire, not
whether anything is actually running. To confirm the daemon is alive, check the
process. When a scheduled run did not happen, follow
[schedule-recovery.md](schedule-recovery.md).

## Daemon behavior

- New or removed schedules are picked up on the next reload tick (default 30s).
- One-shot schedules remember they fired, in `~/.atelier/scheduler_state.json`, so
  a daemon restart never re-runs them.
- Each schedule runs **at most one instance at a time**; missed fires are
  coalesced rather than queued up.
- A schedule pins its timezone at install time, so a host timezone change cannot
  silently shift its fire times.

## Overlap is still your problem

"At most one instance per schedule" means one instance *of that schedule*. It
does not protect a conduit from:

- two **different** schedules pointing at the same conduit and working directory,
- a schedule and a manual `atelier run` overlapping,
- any state a conduit shares outside its own flow directory.

A conduit that mutates shared files needs its own lock. Set the interval wider
than a realistic run before relying on the spacing, and if you need a hard
guarantee, drive runs from cron wrapped in your own single-flight lock rather
than from the daemon - a command wrapper can take an OS advisory lock, and the
daemon invokes the conduit directly with nothing to wrap.

## Where schedules live

The CLI and API share `~/.atelier/schedules/`. Set `ATELIER_GLOBAL_ATELIER_DIR`
in your shell to change the global root. Both `schedule add` and scheduler-enabled
`serve` print the directory. New jobs resolve a relative `run_path` against the
working directory where you add them.

Stop old project daemons before upgrading. In each directory where an old daemon
ran, `atelier list schedules` reports legacy jobs in the configured project
store. Run `atelier schedule migrate` there to move them without firing any.
Scheduler-enabled `serve`, `schedule daemon`, and writable schedule commands
also migrate that project's jobs. Job IDs, run counts, fire markers and history
move with the job. Relative run paths are anchored to the current directory.
Name or ID conflicts leave the original in place and produce a warning.
