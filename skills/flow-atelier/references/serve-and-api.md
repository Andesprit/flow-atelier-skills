# The server, the API, and security

```bash
atelier serve [--host 127.0.0.1] [--port 8000] [--reload-interval 30.0] \
              [--cors-origin URL]... [--log-level INFO]
```

One process hosting both the HTTP/WebSocket API and the scheduler daemon. It is
the entry point the Flow Atelier visual frontend connects to - the designer lays
a conduit out by dependency depth, and runs stream to a dashboard including HITL
gates.

`--port 0` picks an ephemeral port. `--cors-origin` is repeatable.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/conduits` | List conduits |
| `GET` | `/conduits/:name` | Read one |
| `POST` | `/conduits` | Create (201 on success, 409 on collision) |
| `PATCH` | `/conduits/:name` | Partial update |
| `DELETE` | `/conduits/:name` | Delete |
| `POST` | `/conduits/open-path` | Reveal a flow's run path in the OS file explorer |
| `POST` | `/tasks/run` | Run an ad-hoc one-task conduit |
| `GET` | `/schedules` | List active schedules |
| `POST` | `/schedules` | Create |
| `DELETE` | `/schedules/:id` | Soft-delete |
| `GET` | `/flows` | List prior flows |
| `GET` | `/flows/:id/logs` | Per-flow log entries |
| `WS` | `/ws/run-conduit` | Run flows and answer HITL gates over a socket |

`POST /tasks/run` takes `{name, description, task, tool, run_path}` and runs it
as a throwaway one-task conduit - useful for trying a single step without writing
a file.

`GET /flows/:id/logs` returns `{run_path, logs, children}`. `logs` spans the flow
**and all of its descendants**, each entry tagged with `extra["flow_id"]`;
`children` lists only direct children.

`POST /schedules` takes the same shape as a schedule file:
`{conduit_name, inputs, run_path, schedule: {...}}`. See `scheduling.md`.

## Resolution

Conduits and flows resolve exactly as on the CLI - `./.atelier` first, then
`~/.atelier` - so the conduits in the directory you started the server from are
the ones the UI shows.

**Schedules are the exception**: `serve` reads `~/.atelier/schedules/`, since one
daemon serves every project. The CLI's `atelier schedule add` writes to
`./.atelier/schedules/`. If a schedule you added on the CLI does not appear in
the UI, that is why.

## Security

The API runs shell commands on the machine hosting it. **Treat reaching it as
equivalent to a shell on that machine.**

### On loopback (the default)

`atelier serve` binds `127.0.0.1:8000` and needs no token. Two guards stop a web
page you happen to visit from driving it:

- **Origin.** CORS is restricted to localhost origins, never `*`.
- **Host.** Only `localhost`, `127.0.0.1` and `::1` are accepted as the `Host`
  header. This is what stops DNS rebinding, where an attacker's page resolves its
  own hostname to `127.0.0.1` so the browser treats the request as same-origin
  and sends no `Origin` for CORS to reject. Any other `Host` gets
  `400 Invalid host header`.

### Anywhere else

Before binding a non-loopback address, set `ATELIER_API_TOKEN`. Every REST
request then needs `Authorization: Bearer <token>`, and WebSocket connections
need `?token=<token>`. Build the UI with a matching `VITE_API_TOKEN`.

`atelier serve` **refuses to start** on a non-loopback host when the token is
unset:

```console
$ atelier serve --host 0.0.0.0
error: refusing to serve on non-loopback host '0.0.0.0' without
ATELIER_API_TOKEN. Anyone who can reach this address could run shell
commands via the API. Set ATELIER_API_TOKEN, or bind 127.0.0.1 (the default).
```

This used to be a warning that scrolled past in the same second the port opened,
so an existing `--host 0.0.0.0` setup with no token now stops rather than serves.

Binding a specific host also adds that host to the accepted `Host` values. A
wildcard bind (`--host 0.0.0.0`) cannot know which names reach it, so it accepts
any `Host` and relies on the token - which is why the token is mandatory there
rather than merely advised.

### Secrets in output

`atelier run` prints the argument identifying each tool call so the run is
readable. Credential-shaped values (`Bearer <token>`, `sk-` / `ghp_` / `xox`
prefixes, `--password` / `TOKEN=` flags) are masked as `***` on the way to the
screen.

That is a heuristic that reduces casual leakage, **not a guarantee** - it will
miss a secret that does not look like one. The recorded logs under
`.atelier/flows/<id>/` keep the **unredacted** text, so treat that directory as
sensitive and check what you are pasting before sharing a terminal transcript.

### Conduits are code

Installing a package and running it are the same trust decision as running a
shell script someone sent you. Read it first; pin `--ref`.

## Scope

flow-atelier is a local developer tool, not a hosted multi-user service. There is
no multi-tenancy, no distributed workers, no per-user authorization - the token
is all-or-nothing. If you need those, this is the wrong tool.
